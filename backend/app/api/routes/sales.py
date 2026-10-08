from app.services.pricing import load_rules,line_rates
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import DbSession, get_current_user, require_roles
from app.services.branch_stock import check_branch, stock_target
from app.schemas.sales import SaleCreate, SaleCancellation

router = APIRouter(prefix="/sales", tags=["Ventas"])
CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@router.post("", status_code=201)
def create_sale(payload: SaleCreate, db: DbSession, user: dict = Depends(require_roles("admin", "seller"))):
    return persist_sale(payload, db, user)


def persist_sale(payload: SaleCreate, db, user: dict, *, commit: bool = True):
    company_id = user["company_id"]
    check_branch(db,company_id,payload.branch_id)
    stock_table,stock_filter=stock_target(payload.branch_id)
    employee = db.execute(text("SELECT id FROM employees WHERE company_id=:company_id AND user_id=:user_id AND is_active=TRUE"), {"company_id": company_id, "user_id": user["id"]}).scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=409, detail={"code": "seller_profile_missing", "message": "El usuario no tiene un perfil de vendedor activo"})
    if payload.customer_id is not None:
        found = db.execute(text("SELECT 1 FROM customers WHERE company_id=:company_id AND id=:id AND is_active=TRUE"), {"company_id": company_id, "id": payload.customer_id}).first()
        if not found:
            raise HTTPException(status_code=422, detail={"code": "invalid_customer", "message": "El cliente no existe o está inactivo"})

    rules=load_rules(db,company_id)
    subtotal = Decimal("0")
    discount_total = Decimal("0")
    tax_total = Decimal("0")
    lines = []
    try:
        for item in sorted(payload.items, key=lambda line: line.product_id):
            product = db.execute(
                text(f"""SELECT p.id,p.sku,p.name,p.unit_price,i.quantity FROM products p
                         JOIN {stock_table} i ON i.company_id=p.company_id AND i.product_id=p.id
                        WHERE p.company_id=:company_id AND p.id=:product_id AND p.is_active=TRUE {stock_filter} FOR UPDATE OF i"""),
                {"company_id": company_id, "product_id": item.product_id, "branch_id": payload.branch_id},
            ).mappings().first()
            if product is None:
                raise HTTPException(status_code=422, detail={"code": "product_unavailable", "message": f"El producto {item.product_id} no existe o no tiene inventario inicializado"})
            if Decimal(product["quantity"]) < item.quantity:
                raise HTTPException(status_code=409, detail={"code": "insufficient_stock", "message": f"Stock insuficiente para {product['name']}", "available": str(product["quantity"])})
            unit_price = Decimal(product["unit_price"])
            gross = money(unit_price * item.quantity)
            discount_percent,tax_percent=line_rates(item,rules)
            discount = money(gross * discount_percent / Decimal("100"))
            taxable = gross - discount
            tax = money(taxable * tax_percent / Decimal("100"))
            line_total = taxable + tax
            if line_total < 0:
                raise HTTPException(status_code=422, detail={"code": "invalid_line_total", "message": "El total de una línea no puede ser negativo"})
            subtotal += gross
            discount_total += discount
            tax_total += tax
            lines.append({"product": product, "quantity": item.quantity, "unit_price": unit_price, "discount": discount, "tax": tax, "line_total": line_total})

        subtotal, discount_total, tax_total = money(subtotal), money(discount_total), money(tax_total)
        total = money(subtotal - discount_total + tax_total)
        if total <= 0:
            raise HTTPException(status_code=422, detail={"code": "invalid_sale_total", "message": "El total de la venta debe ser mayor que cero"})
        payment_total = money(sum((payment.amount for payment in payload.payments), Decimal("0")))
        if payment_total != total:
            raise HTTPException(status_code=422, detail={"code": "payment_total_mismatch", "message": "La suma de pagos debe coincidir con el total de la venta", "sale_total": str(total), "payment_total": str(payment_total)})

        sale = db.execute(
            text("""INSERT INTO sales(company_id,branch_id,customer_id,seller_id,created_by,currency,subtotal,discount_total,tax_total,total)
                 SELECT :company_id,:branch_id,:customer_id,:seller_id,:created_by,currency,:subtotal,:discount_total,:tax_total,:total
                   FROM companies WHERE id=:company_id
                 RETURNING id,company_id,customer_id,seller_id,status,currency,subtotal,discount_total,tax_total,total,sold_at"""),
            {"company_id": company_id, "branch_id": payload.branch_id, "customer_id": payload.customer_id, "seller_id": employee, "created_by": user["id"], "subtotal": subtotal, "discount_total": discount_total, "tax_total": tax_total, "total": total},
        ).mappings().one()
        for line in lines:
            product = line["product"]
            db.execute(
                text("""INSERT INTO sale_details(company_id,sale_id,product_id,product_name_snapshot,sku_snapshot,quantity,unit_price,discount,tax,line_total)
                     VALUES (:company_id,:sale_id,:product_id,:name,:sku,:quantity,:unit_price,:discount,:tax,:line_total)"""),
                {"company_id": company_id, "sale_id": sale["id"], "product_id": product["id"], "name": product["name"], "sku": product["sku"], "quantity": line["quantity"], "unit_price": line["unit_price"], "discount": line["discount"], "tax": line["tax"], "line_total": line["line_total"]},
            )
            db.execute(text(f"UPDATE {stock_table} SET quantity=quantity-:quantity,updated_at=now() WHERE company_id=:company_id AND product_id=:product_id {stock_filter}"), {"quantity": line["quantity"], "company_id": company_id, "product_id": product["id"], "branch_id":payload.branch_id})
            db.execute(text("""INSERT INTO inventory_movements(company_id,branch_id,product_id,sale_id,movement_type,quantity_delta,created_by)
                              VALUES (:company_id,:branch_id,:product_id,:sale_id,'sale',:delta,:created_by)"""), {"company_id": company_id, "branch_id":payload.branch_id, "product_id": product["id"], "sale_id": sale["id"], "delta": -line["quantity"], "created_by": user["id"]})
        for payment in payload.payments:
            db.execute(text("INSERT INTO payments(company_id,sale_id,method,amount,status,paid_at) VALUES (:company_id,:sale_id,:method,:amount,'completed',now())"), {"company_id": company_id, "sale_id": sale["id"], "method": payment.method, "amount": money(payment.amount)})
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                          VALUES (:company_id,:user_id,'sale.confirmed','sale',:sale_id,CAST(:details AS jsonb))"""), {"company_id": company_id, "user_id": user["id"], "sale_id": str(sale["id"]), "details": '{"source":"api"}'})
        if commit:
            db.commit()
        return {**dict(sale), "items": [{"product_id": line["product"]["id"], "name": line["product"]["name"], "sku": line["product"]["sku"], "quantity": str(line["quantity"]), "unit_price": str(line["unit_price"]), "line_total": str(line["line_total"])} for line in lines], "payments": [{"method": p.method, "amount": str(money(p.amount))} for p in payload.payments]}
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "sale_conflict", "message": "No se pudo confirmar la venta por un conflicto de integridad"}) from exc
    except Exception:
        db.rollback()
        raise


@router.get("")
def list_sales(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "seller")), start: date | None = None, end: date | None = None, status_filter: str | None = Query(default=None, alias="status", pattern="^(draft|confirmed|voided)$"), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    if user["role"] not in {"admin", "manager", "seller"}:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "No tienes permiso para consultar ventas"})
    if start and end and end < start:
        raise HTTPException(status_code=422, detail={"code": "invalid_date_range", "message": "La fecha final debe ser igual o posterior a la inicial"})
    rows = db.execute(text("""SELECT s.id,s.status,s.currency,s.total,s.sold_at,s.voided_at,s.created_by,c.name AS customer_name,e.full_name AS seller_name
                              FROM sales s LEFT JOIN customers c ON c.company_id=s.company_id AND c.id=s.customer_id
                              JOIN employees e ON e.company_id=s.company_id AND e.id=s.seller_id
                             WHERE s.company_id=:company_id AND (CAST(:start AS date) IS NULL OR s.sold_at>=CAST(:start AS date))
                               AND (CAST(:end AS date) IS NULL OR s.sold_at<CAST(:end AS date)+INTERVAL '1 day')
                               AND (CAST(:status AS text) IS NULL OR s.status=:status)
                               AND (CAST(:seller_id AS bigint) IS NULL OR s.created_by=:seller_id)
                             ORDER BY s.sold_at DESC,s.id DESC LIMIT :limit OFFSET :offset"""), {"company_id": user["company_id"], "start": start, "end": end, "status": status_filter, "seller_id": user["id"] if user["role"] == "seller" else None, "limit": limit, "offset": offset}).mappings().all()
    return [dict(row) for row in rows]


@router.get("/{sale_id}")
def get_sale(sale_id: int, db: DbSession, user: dict = Depends(require_roles("admin", "manager", "seller"))):
    sale = db.execute(text("""SELECT s.*, co.name AS company_name, c.name AS customer_name, e.full_name AS seller_name FROM sales s JOIN companies co ON co.id=s.company_id
                              LEFT JOIN customers c ON c.company_id=s.company_id AND c.id=s.customer_id
                              JOIN employees e ON e.company_id=s.company_id AND e.id=s.seller_id
                             WHERE s.id=:sale_id AND s.company_id=:company_id AND (CAST(:seller_id AS bigint) IS NULL OR s.created_by=:seller_id)"""), {"sale_id": sale_id, "company_id": user["company_id"], "seller_id": user["id"] if user["role"] == "seller" else None}).mappings().first()
    if sale is None:
        raise HTTPException(status_code=404, detail={"code": "sale_not_found", "message": "No se encontró la venta"})
    items = db.execute(text("SELECT product_id,product_name_snapshot AS name,sku_snapshot AS sku,quantity,unit_price,discount,tax,line_total FROM sale_details WHERE company_id=:company_id AND sale_id=:sale_id ORDER BY id"), {"company_id": user["company_id"], "sale_id": sale_id}).mappings().all()
    payments = db.execute(text("SELECT method,amount,status,paid_at FROM payments WHERE company_id=:company_id AND sale_id=:sale_id ORDER BY id"), {"company_id": user["company_id"], "sale_id": sale_id}).mappings().all()
    return {**dict(sale), "items": [dict(row) for row in items], "payments": [dict(row) for row in payments]}


@router.get("/{sale_id}/pdf")
def download_sale_pdf(sale_id:int,db:DbSession,user:dict=Depends(require_roles("admin","manager","seller"))):
    from fastapi.responses import Response
    from app.services.pdf_documents import sale_pdf
    return Response(sale_pdf(get_sale(sale_id,db,user)),media_type="application/pdf",
                    headers={"Content-Disposition":f"attachment; filename=salesia-venta-{sale_id}.pdf","Cache-Control":"no-store"})


@router.post("/{sale_id}/void")
def void_sale(sale_id: int, payload: SaleCancellation, db: DbSession, user: dict = Depends(require_roles("admin", "seller"))):
    company_id = user["company_id"]
    try:
        sale = db.execute(text("SELECT id,status,created_by,branch_id FROM sales WHERE id=:sale_id AND company_id=:company_id FOR UPDATE"), {"sale_id": sale_id, "company_id": company_id}).mappings().first()
        if sale is None:
            raise HTTPException(status_code=404, detail={"code": "sale_not_found", "message": "No se encontró la venta"})
        if user["role"] == "seller" and sale["created_by"] != user["id"]:
            raise HTTPException(status_code=404, detail={"code": "sale_not_found", "message": "No se encontró la venta"})
        if sale["status"] != "confirmed":
            raise HTTPException(status_code=409, detail={"code": "sale_not_confirmed", "message": "Solo se puede anular una venta confirmada"})
        lines = db.execute(text("SELECT product_id,quantity FROM sale_details WHERE company_id=:company_id AND sale_id=:sale_id ORDER BY product_id"), {"company_id": company_id, "sale_id": sale_id}).mappings().all()
        stock_table,stock_filter=stock_target(sale.get("branch_id"))
        for line in lines:
            db.execute(text(f"UPDATE {stock_table} SET quantity=quantity+:quantity,updated_at=now() WHERE company_id=:company_id AND product_id=:product_id {stock_filter}"), {"quantity": line["quantity"], "company_id": company_id, "product_id": line["product_id"], "branch_id":sale.get("branch_id")})
            db.execute(text("""INSERT INTO inventory_movements(company_id,branch_id,product_id,sale_id,movement_type,quantity_delta,reason,created_by)
                              VALUES (:company_id,:branch_id,:product_id,:sale_id,'sale_void',:delta,:reason,:created_by)"""), {"company_id": company_id, "branch_id":sale.get("branch_id"), "product_id": line["product_id"], "sale_id": sale_id, "delta": line["quantity"], "reason": payload.reason, "created_by": user["id"]})
        db.execute(text("UPDATE payments SET status='refunded' WHERE company_id=:company_id AND sale_id=:sale_id AND status='completed'"), {"company_id": company_id, "sale_id": sale_id})
        result = db.execute(text("UPDATE sales SET status='voided',void_reason=:reason,voided_at=now() WHERE id=:sale_id AND company_id=:company_id AND status='confirmed' RETURNING id,status,void_reason,voided_at"), {"reason": payload.reason.strip(), "sale_id": sale_id, "company_id": company_id}).mappings().one()
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                          VALUES (:company_id,:user_id,'sale.voided','sale',:sale_id,CAST(:details AS jsonb))"""), {"company_id": company_id, "user_id": user["id"], "sale_id": str(sale_id), "details": json.dumps({"reason": payload.reason.strip(), "refund_confirmed": payload.refund_confirmed, "restock_confirmed": payload.restock_confirmed})})
        db.commit()
        return dict(result)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise






