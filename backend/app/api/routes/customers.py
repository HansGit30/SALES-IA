from app.services.audit import record_audit
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.core.dependencies import DbSession, get_current_user, require_roles
from app.schemas.common import CustomerCreate, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["Clientes"])


@router.get("/{customer_id}/history")
def customer_history(customer_id:int,db:DbSession,user:dict=Depends(require_roles("admin","manager","seller")),
                     offset:int=Query(default=0,ge=0),limit:int=Query(default=26,ge=1,le=100)):
    customer=db.execute(text("SELECT id,name,email,phone,is_active FROM customers WHERE company_id=:company AND id=:id"),
                        {"company":user["company_id"],"id":customer_id}).mappings().first()
    if customer is None:
        raise HTTPException(404,detail="El cliente no existe en esta empresa")
    params={"company":user["company_id"],"id":customer_id,"owner":user["id"] if user["role"]=="seller" else None,"limit":limit,"offset":offset}
    totals=db.execute(text("""SELECT currency,COUNT(*) AS sales_count,SUM(total) AS revenue,MAX(sold_at) AS last_sale
        FROM sales WHERE company_id=:company AND customer_id=:id AND status='confirmed'
        AND (CAST(:owner AS bigint) IS NULL OR created_by=:owner) GROUP BY currency"""),params).mappings().all()
    rows=db.execute(text("""SELECT s.id,s.sold_at,s.total,s.currency,s.status,b.name AS branch_name
        FROM sales s LEFT JOIN branches b ON b.company_id=s.company_id AND b.id=s.branch_id
        WHERE s.company_id=:company AND s.customer_id=:id AND (CAST(:owner AS bigint) IS NULL OR s.created_by=:owner)
        ORDER BY s.sold_at DESC,s.id DESC LIMIT :limit OFFSET :offset"""),params).mappings().all()
    return {"customer":dict(customer),"totals":[dict(r) for r in totals],"sales":[dict(r) for r in rows],
            "scope":"own_sales" if user["role"]=="seller" else "company"}

@router.put("/{record_id}")
def update_customer(record_id: int, payload: CustomerUpdate, db: DbSession, user: dict = Depends(require_roles("admin", "seller"))):
    from json import dumps

    try:
        previous = db.execute(text("SELECT * FROM customers WHERE company_id=:company_id AND id=:id FOR UPDATE"), {"company_id": user["company_id"], "id": record_id}).mappings().first()
        if previous is None:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "El registro no existe en esta empresa"})
        values = payload.model_dump()
        row = db.execute(text("UPDATE customers SET name=:name,email=:email,phone=:phone,is_active=:is_active WHERE company_id=:company_id AND id=:id RETURNING *"), {**values, "company_id": user["company_id"], "id": record_id}).mappings().one()
        changes = {key: {"before": previous[key], "after": row[key]} for key in values if previous[key] != row[key]}
        if changes:
            db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                               VALUES (:company_id,:user_id,'customer.updated','customer',:id,CAST(:details AS jsonb))"""), {"company_id": user["company_id"], "user_id": user["id"], "id": str(record_id), "details": dumps(changes, default=str)})
        db.commit()
        return dict(row)
    except Exception:
        db.rollback()
        raise


@router.get("")
def list_customers(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "seller")), q: str | None = Query(default=None, max_length=100), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    if user["role"] not in {"admin", "manager", "seller"}:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "No tienes permiso para consultar clientes"})
    rows = db.execute(text("""SELECT id,name,email,phone,is_active,created_at FROM customers
                             WHERE company_id=:company_id AND (CAST(:q AS text) IS NULL OR name ILIKE :pattern OR email ILIKE :pattern)
                             ORDER BY name LIMIT :limit OFFSET :offset"""), {"company_id": user["company_id"], "q": q or None, "pattern": f"%{q}%" if q else None, "limit": limit, "offset": offset}).mappings().all()
    return [dict(row) for row in rows]


@router.post("", status_code=201)
def create_customer(payload: CustomerCreate, db: DbSession, user: dict = Depends(require_roles("admin", "seller"))):
    row = db.execute(text("""INSERT INTO customers(company_id,name,email,phone) VALUES (:company_id,:name,:email,:phone)
                             RETURNING id,name,email,phone,is_active,created_at"""), {"company_id": user["company_id"], "name": payload.name.strip(), "email": payload.email, "phone": payload.phone}).mappings().one()
    record_audit(db,user,"customer.created","customer",row["id"])
    db.commit()
    return dict(row)
