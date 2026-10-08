from app.services.pricing import load_rules,line_rates
import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text

from app.core.dependencies import DbSession, require_roles
from app.schemas.sales import PaymentCreate, SaleCreate, SaleVoid, SaleLineCreate
from app.api.routes.sales import money, persist_sale
from app.services.branch_stock import check_branch

router = APIRouter(prefix="/orders", tags=["Pedidos"])


class OrderLine(SaleLineCreate):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)


class OrderCreate(BaseModel):
    branch_id: int | None = Field(default=None, gt=0)
    model_config = ConfigDict(extra="forbid")
    customer_id: int | None = Field(default=None, gt=0)
    items: list[OrderLine] = Field(min_length=1, max_length=100)

    @field_validator("items")
    @classmethod
    def unique_products(cls, items):
        if len({item.product_id for item in items}) != len(items):
            raise ValueError("Cada producto debe aparecer una sola vez")
        return items


class OrderConfirm(BaseModel):
    payments: list[PaymentCreate] = Field(min_length=1, max_length=20)


def audit(db, user, order_id, action, details):
    db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                       VALUES (:company,:user,:action,'order',:id,CAST(:details AS jsonb))"""),
               {"company": user["company_id"], "user": user["id"], "action": action,
                "id": str(order_id), "details": json.dumps(details)})


def owned_order(db, user, order_id, *, lock=False):
    query = """SELECT * FROM orders WHERE company_id=:company AND id=:id
               AND (CAST(:owner AS bigint) IS NULL OR created_by=:owner)"""
    if lock:
        query += " FOR UPDATE"
    row = db.execute(text(query), {"company": user["company_id"], "id": order_id,
                     "owner": user["id"] if user["role"] == "seller" else None}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "order_not_found", "message": "No se encontró el pedido"})
    return row


def pending(row):
    if row["status"] != "pending":
        raise HTTPException(status_code=409, detail={"code": "order_not_pending", "message": "El pedido ya fue convertido o cancelado"})


@router.get("")
def list_orders(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "seller")),
                limit: int = Query(default=26, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    rows = db.execute(text("""SELECT o.*,c.name AS customer_name,u.full_name AS author_name FROM orders o
                              LEFT JOIN customers c ON c.company_id=o.company_id AND c.id=o.customer_id
                              JOIN users u ON u.company_id=o.company_id AND u.id=o.created_by
                              WHERE o.company_id=:company AND (CAST(:owner AS bigint) IS NULL OR o.created_by=:owner)
                              ORDER BY o.created_at DESC,o.id DESC LIMIT :limit OFFSET :offset"""),
                      {"company": user["company_id"], "owner": user["id"] if user["role"] == "seller" else None,
                       "limit": limit, "offset": offset}).mappings().all()
    return [dict(row) for row in rows]


@router.get("/{order_id}")
def get_order(order_id: int, db: DbSession, user: dict = Depends(require_roles("admin", "manager", "seller"))):
    row = owned_order(db, user, order_id)
    lines = db.execute(text("""SELECT product_id,product_name_snapshot AS name,sku_snapshot AS sku,quantity,unit_price,line_total
                               FROM order_details WHERE company_id=:company AND order_id=:id ORDER BY id"""),
                       {"company": user["company_id"], "id": order_id}).mappings().all()
    return {**dict(row), "items": [dict(item) for item in lines]}


@router.post("", status_code=201)
def create_order(payload: OrderCreate, db: DbSession, user: dict = Depends(require_roles("admin", "seller"))):
    try:
        company = user["company_id"]
        check_branch(db,company,payload.branch_id)
        if payload.customer_id is not None:
            customer = db.execute(text("SELECT 1 FROM customers WHERE company_id=:company AND id=:id AND is_active=TRUE"),
                                  {"company": company, "id": payload.customer_id}).first()
            if not customer:
                raise HTTPException(status_code=422, detail={"code": "invalid_customer", "message": "El cliente no existe o está inactivo"})
        currency = db.execute(text("SELECT currency FROM companies WHERE id=:company"), {"company": company}).scalar_one()
        rules=load_rules(db,company)
        lines = []
        for item in sorted(payload.items, key=lambda line: line.product_id):
            product = db.execute(text("SELECT id,name,sku,unit_price FROM products WHERE company_id=:company AND id=:id AND is_active=TRUE FOR SHARE"),
                                 {"company": company, "id": item.product_id}).mappings().first()
            if not product:
                raise HTTPException(status_code=422, detail={"code": "product_unavailable", "message": "Un producto no está disponible"})
            discount,tax=line_rates(item,rules)
            gross=money(product["unit_price"]*item.quantity)
            taxable=gross-money(gross*discount/100)
            lines.append({**dict(product),"quantity":item.quantity,"discount_percent":discount,"tax_percent":tax,"line_total":taxable+money(taxable*tax/100)})
        total = sum((line["line_total"] for line in lines), Decimal("0"))
        if not Decimal("0") < total <= Decimal("999999999999.99"):
            raise HTTPException(status_code=422, detail={"code": "invalid_order_total", "message": "El total del pedido está fuera del rango permitido"})
        row = db.execute(text("""INSERT INTO orders(company_id,branch_id,customer_id,created_by,currency,total)
                                 VALUES (:company,:branch,:customer,:user,:currency,:total) RETURNING *"""),
                         {"company": company, "branch":payload.branch_id, "customer": payload.customer_id, "user": user["id"],
                          "currency": currency, "total": total}).mappings().one()
        for line in lines:
            db.execute(text("""INSERT INTO order_details(company_id,order_id,product_id,product_name_snapshot,sku_snapshot,quantity,unit_price,line_total,discount_percent,tax_percent)
                               VALUES (:company,:order,:id,:name,:sku,:quantity,:unit_price,:line_total,:discount_percent,:tax_percent)"""),
                       {**line, "company": company, "order": row["id"]})
        audit(db, user, row["id"], "order.created", {"total": str(total), "items": len(lines)})
        db.commit()
        return dict(row)
    except Exception:
        db.rollback()
        raise


@router.post("/{order_id}/confirm")
def confirm_order(order_id: int, payload: OrderConfirm, db: DbSession, user: dict = Depends(require_roles("admin", "seller"))):
    try:
        order = owned_order(db, user, order_id, lock=True)
        pending(order)
        currency = db.execute(text("SELECT currency FROM companies WHERE id=:company"), {"company": user["company_id"]}).scalar_one()
        if currency != order["currency"]:
            raise HTTPException(status_code=409, detail={"code": "order_currency_changed", "message": "La moneda de la empresa cambió. Crea un pedido nuevo."})
        lines = db.execute(text("SELECT product_id,quantity,unit_price,discount_percent,tax_percent FROM order_details WHERE company_id=:company AND order_id=:id ORDER BY product_id"),
                           {"company": user["company_id"], "id": order_id}).mappings().all()
        for line in lines:
            product = db.execute(text("SELECT unit_price FROM products WHERE company_id=:company AND id=:id AND is_active=TRUE FOR SHARE"),
                                 {"company": user["company_id"], "id": line["product_id"]}).mappings().first()
            if product is None or product["unit_price"] != line["unit_price"]:
                raise HTTPException(status_code=409, detail={"code": "order_price_changed", "message": "Cambió el precio o la disponibilidad de un artículo. Cancela este pedido y crea uno con el catálogo actualizado."})
        sale = persist_sale(SaleCreate(customer_id=order["customer_id"],branch_id=order.get("branch_id"),
                            items=[{"product_id": line["product_id"], "quantity": line["quantity"],"discount_percent":line.get("discount_percent",0),"tax_percent":line.get("tax_percent",0)} for line in lines],
                            payments=payload.payments), db, user, commit=False)
        db.execute(text("UPDATE orders SET status='converted',sale_id=:sale,updated_at=now() WHERE company_id=:company AND id=:id"),
                   {"company": user["company_id"], "id": order_id, "sale": sale["id"]})
        audit(db, user, order_id, "order.converted", {"sale_id": sale["id"]})
        db.commit()
        return {"id": order_id, "status": "converted", "sale_id": sale["id"]}
    except Exception:
        db.rollback()
        raise


@router.post("/{order_id}/cancel")
def cancel_order(order_id: int, payload: SaleVoid, db: DbSession, user: dict = Depends(require_roles("admin", "seller"))):
    try:
        row = owned_order(db, user, order_id, lock=True)
        pending(row)
        db.execute(text("UPDATE orders SET status='cancelled',cancel_reason=:reason,updated_at=now() WHERE company_id=:company AND id=:id"),
                   {"company": user["company_id"], "id": order_id, "reason": payload.reason})
        audit(db, user, order_id, "order.cancelled", {"reason": payload.reason})
        db.commit()
        return {"id": order_id, "status": "cancelled"}
    except Exception:
        db.rollback()
        raise
