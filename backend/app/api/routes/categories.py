from app.services.audit import record_audit
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.core.dependencies import DbSession, require_roles

router = APIRouter(prefix="/categories", tags=["Categorías"])

class CategoryUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    is_active: bool


@router.put("/{record_id}")
def update_category(record_id: int, payload: CategoryUpdate, db: DbSession, user: dict = Depends(require_roles("admin"))):
    from json import dumps

    try:
        previous = db.execute(text("SELECT name,is_active FROM categories WHERE company_id=:company_id AND id=:id FOR UPDATE"), {"company_id": user["company_id"], "id": record_id}).mappings().first()
        if previous is None:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "El registro no existe en esta empresa"})
        row = db.execute(text("UPDATE categories SET name=:name,is_active=:is_active WHERE company_id=:company_id AND id=:id RETURNING *"), {**payload.model_dump(), "company_id": user["company_id"], "id": record_id}).mappings().one()
        changes = {key: {"before": previous[key], "after": row[key]} for key in payload.model_dump() if previous[key] != row[key]}
        if changes:
            db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                               VALUES (:company_id,:user_id,'category.updated','category',:id,CAST(:details AS jsonb))"""), {"company_id": user["company_id"], "user_id": user["id"], "id": str(record_id), "details": dumps(changes)})
        db.commit()
        return dict(row)
    except Exception:
        db.rollback()
        raise


class CategoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)


@router.get("")
def list_categories(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "seller", "warehouse"))):
    rows = db.execute(text("SELECT id,name,is_active FROM categories WHERE company_id=:company_id ORDER BY name"), {"company_id": user["company_id"]}).mappings().all()
    return [dict(row) for row in rows]


@router.post("", status_code=201)
def create_category(payload: CategoryCreate, db: DbSession, user: dict = Depends(require_roles("admin"))):
    row = db.execute(text("INSERT INTO categories(company_id,name) VALUES (:company_id,:name) RETURNING id,name,is_active"), {"company_id": user["company_id"], "name": payload.name.strip()}).mappings().one()
    record_audit(db,user,"category.created","category",row["id"])
    db.commit()
    return dict(row)
