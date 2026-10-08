from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from pydantic import BaseModel, Field
from app.core.config import settings
from app.services.auth_limits import consume_attempts
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import DbSession, require_roles
from app.core.security import hash_password, verify_password
from app.schemas.common import UserCreate

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("")
def list_users(db: DbSession, user: dict = Depends(require_roles("admin")), limit: int = Query(default=100, ge=1, le=500)):
    rows = db.execute(text("""SELECT u.id,u.email,u.full_name,u.is_active,u.must_change_password,r.code AS role,u.created_at
                              FROM users u JOIN roles r ON r.id=u.role_id
                             WHERE u.company_id=:company_id ORDER BY u.full_name LIMIT :limit"""), {"company_id": user["company_id"], "limit": limit}).mappings().all()
    return [dict(row) for row in rows]


@router.post("", status_code=201)
def create_user(payload: UserCreate, db: DbSession, actor: dict = Depends(require_roles("admin"))):
    try:
        role_id = db.execute(text("SELECT id FROM roles WHERE code=:role"), {"role": payload.role}).scalar_one_or_none()
        if role_id is None:
            raise HTTPException(status_code=422, detail={"code": "unknown_role", "message": "El rol indicado no está configurado"})
        user = db.execute(text("""INSERT INTO users(company_id,role_id,email,full_name,password_hash,must_change_password)
                                  VALUES (:company_id,:role_id,:email,:full_name,:password_hash,TRUE)
                                  RETURNING id,email,full_name,is_active,created_at"""), {"company_id": actor["company_id"], "role_id": role_id, "email": payload.email.lower(), "full_name": payload.full_name.strip(), "password_hash": hash_password(payload.password)}).mappings().one()
        if payload.role in {"admin", "seller", "warehouse"}:
            db.execute(text("INSERT INTO employees(company_id,user_id,full_name) VALUES (:company_id,:user_id,:name)"), {"company_id": actor["company_id"], "user_id": user["id"], "name": payload.full_name.strip()})
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                          VALUES (:company_id,:actor,'user.created','user',:created,CAST(:details AS jsonb))"""), {"company_id": actor["company_id"], "actor": actor["id"], "created": str(user["id"]), "details": '{"role":"' + payload.role + '"}'})
        db.commit()
        return {**dict(user), "role": payload.role}
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "email_in_use", "message": "Ya existe un usuario con ese correo en esta empresa"}) from exc
    except Exception:
        db.rollback()
        raise


class UserPasswordReset(BaseModel):
    admin_password: str = Field(min_length=1, max_length=200)
    temporary_password: str = Field(min_length=12, max_length=200)


@router.post("/{user_id}/reset-password", status_code=204)
def reset_password(user_id: int, payload: UserPasswordReset, db: DbSession, actor: dict = Depends(require_roles("admin"))):
    if user_id == actor["id"]:
        raise HTTPException(status_code=422, detail="Usa Mi seguridad para cambiar tu propia contraseña")
    consume_attempts(db, [(f"admin-reset:{actor['company_id']}:{actor['id']}", settings.auth_account_attempts)])
    try:
        # Consistent lock ordering for two administrators recovering each other.
        rows = db.execute(text("""SELECT id,password_hash,session_version,is_active FROM users
            WHERE company_id=:company AND id IN (:actor,:target) ORDER BY id FOR UPDATE"""),
            {"company": actor["company_id"], "actor": actor["id"], "target": user_id}).mappings().all()
        accounts = {row["id"]: row for row in rows}
        administrator = accounts.get(actor["id"])
        target = accounts.get(user_id)
        if administrator is None or not administrator["is_active"] or administrator["session_version"] != actor["session_version"]:
            raise HTTPException(status_code=401, detail="La sesión ha expirado")
        if not verify_password(payload.admin_password, administrator["password_hash"]):
            raise HTTPException(status_code=400, detail="Tu contraseña de administrador no es correcta")
        if target is None or not target["is_active"]:
            raise HTTPException(status_code=404, detail="No se encontró un usuario activo en esta empresa")
        if verify_password(payload.temporary_password, target["password_hash"]):
            raise HTTPException(status_code=422, detail="La contraseña temporal debe ser diferente de la anterior")
        db.execute(text("""UPDATE users SET password_hash=:password,must_change_password=TRUE,
            session_version=session_version+1 WHERE company_id=:company AND id=:id"""),
            {"password": hash_password(payload.temporary_password), "company": actor["company_id"], "id": user_id})
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
            VALUES (:company,:actor,'user.password_reset','user',:target,CAST('{}' AS jsonb))"""),
            {"company": actor["company_id"], "actor": actor["id"], "target": str(user_id)})
        db.commit()
    except Exception:
        db.rollback()
        raise


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=2,max_length=160)
    role: str = Field(pattern="^(admin|manager|seller|analyst|warehouse)$")
    is_active: bool


@router.put("/{user_id}")
def update_user(user_id:int,payload:UserUpdate,db:DbSession,actor:dict=Depends(require_roles("admin"))):
    from app.services.audit import record_audit
    try:
        db.execute(text("SELECT id FROM companies WHERE id=:c FOR UPDATE"),{"c":actor["company_id"]})
        current_actor=db.execute(text("""SELECT u.is_active,u.session_version,r.code AS role
            FROM users u JOIN roles r ON r.id=u.role_id WHERE u.company_id=:c AND u.id=:id"""),
            {"c":actor["company_id"],"id":actor["id"]}).mappings().first()
        if not current_actor or not current_actor["is_active"] or current_actor["role"]!="admin" or current_actor["session_version"]!=actor["session_version"]:
            raise HTTPException(401,detail="La sesión ha expirado")
        previous=db.execute(text("""SELECT u.id,u.full_name,u.is_active,r.code AS role FROM users u JOIN roles r ON r.id=u.role_id
            WHERE u.company_id=:c AND u.id=:id FOR UPDATE OF u"""),{"c":actor["company_id"],"id":user_id}).mappings().first()
        if previous is None: raise HTTPException(404,detail="El usuario no existe en esta empresa")
        if user_id==actor["id"] and (not payload.is_active or payload.role!="admin"):
            raise HTTPException(409,detail="No puedes quitar tu propio acceso de administrador")
        if previous["role"]=="admin" and previous["is_active"] and (payload.role!="admin" or not payload.is_active):
            remaining=db.execute(text("""SELECT COUNT(*) FROM users u JOIN roles r ON r.id=u.role_id
                WHERE u.company_id=:c AND u.id<>:id AND u.is_active AND r.code='admin'"""),{"c":actor["company_id"],"id":user_id}).scalar_one()
            if remaining==0: raise HTTPException(409,detail="Debe quedar al menos un administrador activo")
        role=db.execute(text("SELECT id FROM roles WHERE code=:role"),{"role":payload.role}).scalar_one()
        values={"c":actor["company_id"],"id":user_id,"name":payload.full_name.strip(),"active":payload.is_active,"role":role}
        if len(values["name"])<2: raise HTTPException(422,detail="Escribe un nombre válido")
        changed=previous["role"]!=payload.role or previous["is_active"]!=payload.is_active
        db.execute(text("""UPDATE users SET full_name=:name,is_active=:active,role_id=:role,session_version=session_version+:revoke
            WHERE company_id=:c AND id=:id"""),{**values,"revoke":1 if changed else 0})
        db.execute(text("UPDATE employees SET full_name=:name,is_active=:active WHERE company_id=:c AND user_id=:id"),values)
        if payload.role in {"admin","seller","warehouse"}:
            db.execute(text("""INSERT INTO employees(company_id,user_id,full_name,is_active) VALUES (:c,:id,:name,:active)
                ON CONFLICT (company_id,user_id) DO NOTHING"""),values)
        record_audit(db,actor,"user.updated","user",user_id,{"before":dict(previous),"after":payload.model_dump(),"sessions_revoked":changed})
        db.commit()
        return {"id":user_id,**payload.model_dump()}
    except Exception:
        db.rollback()
        raise
