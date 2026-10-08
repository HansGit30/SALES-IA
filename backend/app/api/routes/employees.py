from app.services.audit import record_audit
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import DbSession, require_roles
from app.services.branch_stock import check_branch

router = APIRouter(prefix="/employees", tags=["Vendedores"])

class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    full_name: str = Field(min_length=2, max_length=160)
    branch_id: int | None = Field(default=None, gt=0)
    is_active: bool


@router.put("/{record_id}")
def update_employee(record_id: int, payload: EmployeeUpdate, db: DbSession, user: dict = Depends(require_roles("admin"))):
    from json import dumps

    try:
        previous = db.execute(text("SELECT full_name,is_active,branch_id FROM employees WHERE company_id=:company_id AND id=:id FOR UPDATE"), {"company_id": user["company_id"], "id": record_id}).mappings().first()
        if previous is None:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "El registro no existe en esta empresa"})
        if payload.branch_id != previous["branch_id"]:
            check_branch(db,user["company_id"],payload.branch_id)
        row = db.execute(text("UPDATE employees SET branch_id=:branch_id,full_name=:full_name,is_active=:is_active WHERE company_id=:company_id AND id=:id RETURNING *"), {**payload.model_dump(), "company_id": user["company_id"], "id": record_id}).mappings().one()
        changes = {key: {"before": previous[key], "after": row[key]} for key in payload.model_dump() if previous[key] != row[key]}
        if changes:
            db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                               VALUES (:company_id,:user_id,'employee.updated','employee',:id,CAST(:details AS jsonb))"""), {"company_id": user["company_id"], "user_id": user["id"], "id": str(record_id), "details": dumps(changes)})
        db.commit()
        return dict(row)
    except Exception:
        db.rollback()
        raise


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    full_name: str = Field(min_length=2, max_length=160)
    user_id: int | None = Field(default=None, gt=0)
    branch_id: int | None = Field(default=None, gt=0)


@router.get("")
def list_employees(db: DbSession, user: dict = Depends(require_roles("admin", "manager"))):
    rows = db.execute(text("""SELECT e.id,e.full_name,e.user_id,e.is_active,e.branch_id,b.name AS branch_name,u.email FROM employees e
                              LEFT JOIN branches b ON b.company_id=e.company_id AND b.id=e.branch_id
                              LEFT JOIN users u ON u.company_id=e.company_id AND u.id=e.user_id
                             WHERE e.company_id=:company_id ORDER BY e.full_name"""), {"company_id": user["company_id"]}).mappings().all()
    return [dict(row) for row in rows]


@router.post("", status_code=201)
def create_employee(payload: EmployeeCreate, db: DbSession, user: dict = Depends(require_roles("admin"))):
    check_branch(db,user["company_id"],payload.branch_id)
    if payload.user_id is not None:
        account = db.execute(text("SELECT id,full_name FROM users WHERE id=:user_id AND company_id=:company_id AND is_active=TRUE"), {"user_id": payload.user_id, "company_id": user["company_id"]}).mappings().first()
        if account is None:
            raise HTTPException(status_code=422, detail={"code": "invalid_user", "message": "La cuenta no pertenece a esta empresa o está inactiva"})
        if account["full_name"] != payload.full_name:
            raise HTTPException(status_code=422, detail={"code": "name_mismatch", "message": "El nombre debe coincidir con el usuario vinculado"})
    try:
        row = db.execute(text("INSERT INTO employees(company_id,user_id,full_name,branch_id) VALUES (:company_id,:user_id,:name,:branch_id) RETURNING id,full_name,user_id,is_active,branch_id"), {"company_id": user["company_id"], "user_id": payload.user_id, "name": payload.full_name.strip(), "branch_id":payload.branch_id}).mappings().one()
        record_audit(db,user,"employee.created","employee",row["id"])
        db.commit()
        return dict(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "employee_conflict", "message": "La cuenta ya tiene un perfil de vendedor"}) from exc
