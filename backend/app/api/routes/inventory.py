from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from app.core.dependencies import DbSession, get_current_user, require_roles

from app.services.branch_stock import check_branch, stock_target

router = APIRouter(prefix="/inventory", tags=["Inventario"])


class Adjustment(BaseModel):
    branch_id: int | None = Field(default=None,gt=0)
    product_id: int = Field(gt=0)
    quantity_delta: Decimal = Field(max_digits=14, decimal_places=3)
    reason: str = Field(min_length=3, max_length=1000)

    @field_validator("quantity_delta")
    @classmethod
    def reject_zero_adjustment(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("El ajuste debe ser distinto de cero")
        return value


@router.get("")
def list_inventory(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "warehouse")), q: str | None = Query(default=None, max_length=100), low_stock_only: bool = False, branch_id: int | None = Query(default=None,gt=0)):
    table, _ = stock_target(branch_id)
    branch_join = " AND i.branch_id=:branch_id" if branch_id else ""
    rows = db.execute(text(f"""SELECT p.id AS product_id,p.sku,p.name,COALESCE(i.quantity,0) AS quantity,i.updated_at
        FROM products p LEFT JOIN {table} i ON i.company_id=p.company_id AND i.product_id=p.id {branch_join}
        WHERE p.company_id=:company_id AND p.is_active=TRUE
        AND (CAST(:q AS text) IS NULL OR p.name ILIKE :pattern OR p.sku ILIKE :pattern)
        AND (NOT :low_stock_only OR COALESCE(i.quantity,0)<=5) ORDER BY p.name,p.id"""),
        {"company_id":user["company_id"],"branch_id":branch_id,"q":q,"pattern":f"%{q}%" if q else None,"low_stock_only":low_stock_only}).mappings().all()
    return [dict(row) for row in rows]


@router.get("/movements")
def list_movements(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "warehouse")), product_id: int | None = Query(default=None, gt=0), limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0), branch_id: int | None = Query(default=None,gt=0)):
    rows = db.execute(text("""SELECT m.id,m.product_id,p.name AS product_name,m.sale_id,m.movement_type,m.quantity_delta,m.reason,m.created_at,u.full_name AS created_by
                              FROM inventory_movements m JOIN products p ON p.company_id=m.company_id AND p.id=m.product_id
                              JOIN users u ON u.company_id=m.company_id AND u.id=m.created_by
                             WHERE m.company_id=:company_id AND m.branch_id IS NOT DISTINCT FROM CAST(:branch_id AS bigint) AND (CAST(:product_id AS bigint) IS NULL OR m.product_id=:product_id)
                             ORDER BY m.created_at DESC,m.id DESC LIMIT :limit OFFSET :offset"""), {"company_id": user["company_id"], "product_id": product_id, "limit": limit, "offset": offset,"branch_id":branch_id}).mappings().all()
    return [dict(row) for row in rows]


@router.post("/adjustments", status_code=201)
def adjust_inventory(payload: Adjustment, db: DbSession, user: dict = Depends(require_roles("admin", "warehouse"))):
    company_id = user["company_id"]
    try:
        check_branch(db,company_id,payload.branch_id)
        table, clause=stock_target(payload.branch_id)
        if payload.branch_id is not None:
            found=db.execute(text("SELECT id FROM products WHERE company_id=:c AND id=:p"),{"c":company_id,"p":payload.product_id}).first()
            if not found: raise HTTPException(404,detail="El producto no existe")
            db.execute(text("INSERT INTO branch_inventory(company_id,branch_id,product_id) VALUES (:c,:b,:p) ON CONFLICT DO NOTHING"),{"c":company_id,"b":payload.branch_id,"p":payload.product_id})
        row = db.execute(text(f"""UPDATE {table} SET quantity=quantity+:delta,updated_at=now()
                                  WHERE company_id=:company_id AND product_id=:product_id AND quantity+:delta>=0 {clause}
                                  RETURNING quantity"""), {"company_id": company_id,"branch_id":payload.branch_id, "product_id": payload.product_id, "delta": payload.quantity_delta,"branch_id":payload.branch_id}).mappings().first()
        if row is None:
            exists = db.execute(text("SELECT 1 FROM inventory WHERE company_id=:company_id AND product_id=:product_id"), {"company_id": company_id, "product_id": payload.product_id}).first()
            if not exists:
                raise HTTPException(status_code=404, detail={"code": "inventory_not_found", "message": "No se encontró el inventario del producto"})
            raise HTTPException(status_code=409, detail={"code": "negative_stock", "message": "El ajuste dejaría el stock por debajo de cero"})
        movement = db.execute(text("""INSERT INTO inventory_movements(company_id,branch_id,product_id,movement_type,quantity_delta,reason,created_by)
                                     VALUES (:company_id,:branch_id,:product_id,'adjustment',:delta,:reason,:user_id)
                                     RETURNING id,product_id,quantity_delta,reason,created_at"""), {"company_id": company_id,"branch_id":payload.branch_id, "product_id": payload.product_id, "delta": payload.quantity_delta, "reason": payload.reason, "user_id": user["id"]}).mappings().one()
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                          VALUES (:company_id,:user_id,'inventory.adjusted','product',:product_id,CAST(:details AS jsonb))"""), {"company_id": company_id, "user_id": user["id"], "product_id": str(payload.product_id), "details": '{"source":"manual adjustment"}'})
        db.commit()
        return {**dict(movement), "stock_after": str(row["quantity"])}
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
