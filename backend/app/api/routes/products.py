from app.services.audit import record_audit
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.core.dependencies import DbSession, get_current_user, require_roles
from app.schemas.common import ProductCreate, ProductUpdate

router = APIRouter(prefix="/products", tags=["Productos"])

@router.put("/{record_id}")
def update_product(record_id: int, payload: ProductUpdate, db: DbSession, user: dict = Depends(require_roles("admin"))):
    from json import dumps

    try:
        previous = db.execute(text("SELECT * FROM products WHERE company_id=:company_id AND id=:id FOR UPDATE"), {"company_id": user["company_id"], "id": record_id}).mappings().first()
        if previous is None:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "El registro no existe en esta empresa"})
        if payload.category_id is not None:
            category = db.execute(text("SELECT 1 FROM categories WHERE company_id=:company_id AND id=:id AND (is_active=TRUE OR id=:previous_id)"), {"company_id": user["company_id"], "id": payload.category_id, "previous_id": previous["category_id"]}).first()
            if category is None:
                raise HTTPException(status_code=422, detail={"code": "invalid_category", "message": "La categoría no existe o está inactiva"})
        values = payload.model_dump()
        row = db.execute(text("UPDATE products SET sku=:sku,name=:name,description=:description,unit_price=:unit_price,category_id=:category_id,is_active=:is_active WHERE company_id=:company_id AND id=:id RETURNING *"), {**values, "company_id": user["company_id"], "id": record_id}).mappings().one()
        changes = {key: {"before": previous[key], "after": row[key]} for key in values if previous[key] != row[key]}
        if changes:
            db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                               VALUES (:company_id,:user_id,'product.updated','product',:id,CAST(:details AS jsonb))"""), {"company_id": user["company_id"], "user_id": user["id"], "id": str(record_id), "details": dumps(changes, default=str)})
        db.commit()
        return dict(row)
    except Exception:
        db.rollback()
        raise


@router.get("")
def list_products(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "seller", "warehouse")), q: str | None = Query(default=None, max_length=100), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), branch_id: int | None = Query(default=None,gt=0)):
    if user["role"] not in {"admin", "manager", "seller", "warehouse"}:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "No tienes permiso para consultar productos"})
    rows = db.execute(text("""SELECT p.id,p.sku,p.name,p.description,p.unit_price,p.is_active,c.id AS category_id,c.name AS category_name,CASE WHEN CAST(:branch_id AS bigint) IS NULL THEN COALESCE(i.quantity,0) ELSE COALESCE(bi.quantity,0) END AS stock
                              FROM products p LEFT JOIN categories c ON c.company_id=p.company_id AND c.id=p.category_id
                              LEFT JOIN inventory i ON i.company_id=p.company_id AND i.product_id=p.id
                             LEFT JOIN branch_inventory bi ON bi.company_id=p.company_id AND bi.product_id=p.id AND bi.branch_id=:branch_id
                             WHERE p.company_id=:company_id AND (CAST(:q AS text) IS NULL OR p.name ILIKE :pattern OR p.sku ILIKE :pattern)
                             ORDER BY p.name LIMIT :limit OFFSET :offset"""), {"company_id": user["company_id"], "q": q or None, "pattern": f"%{q}%" if q else None, "limit": limit, "offset": offset,"branch_id":branch_id}).mappings().all()
    return [dict(row) for row in rows]


@router.post("", status_code=201)
def create_product(payload: ProductCreate, db: DbSession, user: dict = Depends(require_roles("admin"))):
    if payload.category_id is not None:
        category = db.execute(text("SELECT 1 FROM categories WHERE company_id=:company_id AND id=:category_id AND is_active=TRUE"), {"company_id": user["company_id"], "category_id": payload.category_id}).first()
        if not category:
            raise HTTPException(status_code=422, detail={"code": "invalid_category", "message": "La categoría no existe o está inactiva"})
    try:
        row = db.execute(text("""INSERT INTO products(company_id,sku,name,description,unit_price,category_id)
                                 VALUES (:company_id,:sku,:name,:description,:unit_price,:category_id)
                                 RETURNING id,sku,name,description,unit_price,category_id,is_active"""), {"company_id": user["company_id"], "sku": payload.sku.strip(), "name": payload.name.strip(), "description": payload.description, "unit_price": payload.unit_price, "category_id": payload.category_id}).mappings().one()
        db.execute(text("INSERT INTO inventory(company_id,product_id,quantity) VALUES (:company_id,:product_id,0)"), {"company_id": user["company_id"], "product_id": row["id"]})
        record_audit(db,user,"product.created","product",row["id"])
        db.commit()
        return dict(row)
    except Exception:
        db.rollback()
        raise
