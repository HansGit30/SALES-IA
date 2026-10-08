from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.dependencies import DbSession, get_current_user
from app.core.security import create_access_token, verify_password, hash_password
from app.schemas.common import LoginRequest
from app.core.config import settings
from app.services.auth_limits import consume_attempts

DUMMY_PASSWORD_HASH = hash_password("salesia-account-timing-placeholder")

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login")
def login(payload: LoginRequest, db: DbSession, request: Request):
    consume_attempts(db, [
        (f"login:account:{payload.company_id}:{str(payload.email).lower()}", settings.auth_account_attempts),
        (f"login:ip:{request.client.host if request.client else 'unknown'}", settings.auth_ip_attempts),
    ])
    user = db.execute(
        text("""SELECT u.id, u.company_id, u.email, u.full_name, u.password_hash, u.session_version, u.must_change_password, r.code AS role
                  FROM users u JOIN roles r ON r.id = u.role_id
                 WHERE lower(u.email) = lower(:email) AND u.company_id = :company_id AND u.is_active = TRUE"""),
        {"email": payload.email, "company_id": payload.company_id},
    ).mappings().first()
    valid_password = verify_password(payload.password, user["password_hash"] if user else DUMMY_PASSWORD_HASH)
    if user is None or not valid_password:
        if user is not None:
            record_session_event(db, user, "auth.login_failed")
            db.commit()
        raise HTTPException(status_code=401, detail={"code": "invalid_credentials", "message": "Correo, empresa o contraseña incorrectos"}, headers={"WWW-Authenticate": "Bearer"})
    record_session_event(db, user, "auth.login_succeeded")
    db.commit()
    token = create_access_token(subject=str(user["id"]), company_id=user["company_id"], role=user["role"], session_version=user["session_version"])
    return {"access_token": token, "token_type": "bearer", "user": {"id": user["id"], "company_id": user["company_id"], "email": user["email"], "full_name": user["full_name"], "role": user["role"], "must_change_password": user["must_change_password"]}}


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


@router.post("/password", status_code=204)
def change_password(payload: PasswordChange, db: DbSession, user: dict = Depends(get_current_user)):
    consume_attempts(db, [(f"password:{user['company_id']}:{user['id']}", settings.auth_account_attempts)])
    try:
        row = db.execute(text("SELECT password_hash,session_version FROM users WHERE company_id=:company AND id=:id FOR UPDATE"),
                         {"company": user["company_id"], "id": user["id"]}).mappings().one()
        if row["session_version"] != user["session_version"]:
            raise HTTPException(status_code=401, detail="La sesión ha expirado")
        if not verify_password(payload.current_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
        if payload.current_password == payload.new_password:
            raise HTTPException(status_code=422, detail="La nueva contraseña debe ser diferente")
        db.execute(text("UPDATE users SET password_hash=:password,must_change_password=FALSE,session_version=session_version+1 WHERE company_id=:company AND id=:id"),
                   {"password": hash_password(payload.new_password), "company": user["company_id"], "id": user["id"]})
        record_session_event(db, user, "auth.password_changed")
        db.commit()
    except Exception:
        db.rollback()
        raise


def record_session_event(db, user, action):
    db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                       VALUES (:company,:id,:action,'user',:entity,CAST('{}' AS jsonb))"""),
               {"company": user["company_id"], "id": user["id"], "action": action, "entity": str(user["id"])})


@router.post("/logout-all", status_code=204)
def logout_all(db: DbSession, user: dict = Depends(get_current_user)):
    try:
        db.execute(text("UPDATE users SET session_version=session_version+1 WHERE company_id=:company AND id=:id"),
                   {"company": user["company_id"], "id": user["id"]})
        record_session_event(db, user, "auth.sessions_revoked")
        db.commit()
    except Exception:
        db.rollback()
        raise
