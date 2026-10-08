import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text

from app.core.dependencies import DbSession, require_roles
from app.services.reporting import summarize, csv_content

router = APIRouter(prefix="/reports", tags=["Reportes"])
ROLES = ("admin", "manager", "analyst")


class SalesReportRequest(BaseModel):
    start: date | None = None
    end: date | None = None
    report_type: Literal["sales","statistical","products","customers","sellers"] = "sales"

    branch_id: int | None = Field(default=None,gt=0)
    customer_id: int | None = Field(default=None, gt=0)
    employee_id: int | None = Field(default=None, gt=0)
    product_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_range(self):
        if self.start and self.end and self.end < self.start:
            raise ValueError("La fecha final debe ser igual o posterior a la inicial")
        return self


def sales_data(db, company_id, start, end, customer_id=None, employee_id=None, product_id=None, branch_id=None):
    rows = db.execute(text("""SELECT s.id,s.customer_id,s.seller_id,s.sold_at,s.status,s.currency,s.subtotal,s.discount_total,s.tax_total,s.total,
                                   c.name AS customer_name,e.full_name AS seller_name
                              FROM sales s LEFT JOIN customers c ON c.company_id=s.company_id AND c.id=s.customer_id
                              JOIN employees e ON e.company_id=s.company_id AND e.id=s.seller_id
                             WHERE s.company_id=:company_id AND (CAST(:branch_id AS bigint) IS NULL OR s.branch_id=:branch_id) AND s.status IN ('confirmed','voided')
                               AND (CAST(:start AS date) IS NULL OR s.sold_at >= (CAST(:start AS timestamp) AT TIME ZONE 'America/Lima'))
                               AND (CAST(:end AS date) IS NULL OR s.sold_at < ((CAST(:end AS date)+INTERVAL '1 day') AT TIME ZONE 'America/Lima'))
                               AND (CAST(:customer_id AS bigint) IS NULL OR s.customer_id=:customer_id)
                               AND (CAST(:employee_id AS bigint) IS NULL OR s.seller_id=:employee_id)
                               AND (CAST(:product_id AS bigint) IS NULL OR EXISTS (
                                   SELECT 1 FROM sale_details d WHERE d.company_id=s.company_id
                                   AND d.sale_id=s.id AND d.product_id=:product_id))
                             ORDER BY s.sold_at,s.id LIMIT 10001"""), {"company_id":company_id,"start":start,"end":end,"customer_id":customer_id,"employee_id":employee_id,"product_id":product_id,"branch_id":branch_id}).mappings().all()
    if len(rows)>10000:
        raise HTTPException(status_code=422,detail={"code":"report_too_large","message":"El reporte supera 10 000 ventas. Selecciona un periodo más corto."})
    return rows


def build_snapshot(rows, payload, filters=None):
    return {"report_type":payload.report_type,"generated_at":datetime.now(UTC).isoformat(),
            "parameters":{"start":str(payload.start) if payload.start else None,"end":str(payload.end) if payload.end else None,
                          "timezone":"America/Lima","exclude_voided_from_totals":True,"filters":filters or {}},
            "summary":summarize(rows),
            "rows":[{"id":row["id"],"sold_at":row["sold_at"].astimezone(ZoneInfo("America/Lima")).isoformat(),
                     "status":row["status"],"customer":row["customer_name"],"seller":row["seller_name"],
                     **{key:str(row[key]) for key in ("subtotal","discount_total","tax_total","total","currency")}} for row in rows]}


def grouped_report(db,company_id,rows,payload):
    confirmed=[r for r in rows if r["status"]=="confirmed"]
    groups={}
    if payload.report_type=="products":
        ids=[r["id"] for r in confirmed]
        if not ids: return []
        lines=db.execute(text("""SELECT d.product_id AS entity_id,d.product_name_snapshot AS name,
            s.currency,d.quantity,d.line_total AS amount,s.id AS sale_id
            FROM sale_details d JOIN sales s ON s.company_id=d.company_id AND s.id=d.sale_id
            WHERE d.company_id=:company AND d.sale_id=ANY(:ids)
            AND (CAST(:product AS bigint) IS NULL OR d.product_id=:product)"""),
            {"company":company_id,"ids":ids,"product":payload.product_id}).mappings().all()
    else:
        customer=payload.report_type=="customers"
        lines=[{"entity_id":r["customer_id" if customer else "seller_id"],"name":r["customer_name" if customer else "seller_name"] or "Cliente general",
                "currency":r["currency"],"quantity":0,"amount":r["total"],"sale_id":r["id"]} for r in confirmed]
    for row in lines:
        key=(row["entity_id"],row["currency"])
        group=groups.setdefault(key,{"entity_id":row["entity_id"],"name":row["name"],"currency":row["currency"],"revenue":Decimal(0),"units":Decimal(0),"ids":set()})
        group["revenue"]+=Decimal(str(row["amount"]))
        group["units"]+=Decimal(str(row["quantity"]))
        group["ids"].add(row["sale_id"])
    return [{"entity_id":g["entity_id"],"name":g["name"],"currency":g["currency"],"revenue":str(g["revenue"]),
             "units":str(g["units"]),"sales_count":len(g["ids"]),"average":str(g["revenue"]/len(g["ids"]))}
            for g in sorted(groups.values(),key=lambda g:(g["currency"],-g["revenue"],g["name"]))]


@router.get("")
def list_reports(db: DbSession, user:dict=Depends(require_roles(*ROLES)), limit:int=Query(default=26,ge=1,le=200), offset:int=Query(default=0,ge=0)):
    rows=db.execute(text("""SELECT id,report_type,parameters,created_at,(snapshot IS NOT NULL) AS available
                            FROM reports WHERE company_id=:company ORDER BY created_at DESC,id DESC LIMIT :limit OFFSET :offset"""),
                    {"company":user["company_id"],"limit":limit,"offset":offset}).mappings().all()
    return [dict(row) for row in rows]


FILTER_TABLES = {"branch_id": ("branches", "name"),"customer_id": ("customers", "name"), "employee_id": ("employees", "full_name"), "product_id": ("products", "name")}


@router.get("/filter-options")
def filter_options(db: DbSession, user: dict = Depends(require_roles(*ROLES))):
    return {key: [dict(row) for row in db.execute(text(
        f"SELECT id,{column} AS name FROM {table} WHERE company_id=:company ORDER BY {column},id"
    ), {"company": user["company_id"]}).mappings().all()] for key, (table, column) in FILTER_TABLES.items()}


def resolve_filters(db, company_id, payload):
    filters = {}
    for key, (table, column) in FILTER_TABLES.items():
        selected = getattr(payload, key)
        if selected is None:
            continue
        row = db.execute(text(f"SELECT id,{column} AS name FROM {table} WHERE company_id=:company AND id=:id"),
                         {"company": company_id, "id": selected}).mappings().first()
        if row is None:
            raise HTTPException(status_code=422, detail="El filtro seleccionado no está disponible en esta empresa.")
        filters[key] = dict(row)
    return filters


@router.post("/sales",status_code=201)
def create_sales_report(payload:SalesReportRequest,db:DbSession,user:dict=Depends(require_roles(*ROLES))):
    try:
        filters=resolve_filters(db,user["company_id"],payload)
        rows=sales_data(db,user["company_id"],payload.start,payload.end,payload.customer_id,payload.employee_id,payload.product_id,payload.branch_id)
        snapshot=build_snapshot(rows,payload,filters)
        if payload.report_type in {"products","customers","sellers"}:
            snapshot["groups"]=grouped_report(db,user["company_id"],rows,payload)
        report_id=db.execute(text("""INSERT INTO reports(company_id,report_type,parameters,snapshot,created_by)
                                     VALUES (:company,:type,CAST(:parameters AS jsonb),CAST(:snapshot AS jsonb),:user) RETURNING id"""),
                             {"company":user["company_id"],"type":payload.report_type,"parameters":json.dumps(snapshot["parameters"]),
                              "snapshot":json.dumps(snapshot),"user":user["id"]}).scalar_one()
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                           VALUES (:company,:user,'report.created','report',:id,CAST(:details AS jsonb))"""),
                   {"company":user["company_id"],"user":user["id"],"id":str(report_id),
                    "details":json.dumps({"report_type":payload.report_type,**snapshot["parameters"],"rows":len(snapshot["rows"])})})
        db.commit()
        return {"id":report_id,**snapshot}
    except Exception:
        db.rollback()
        raise


@router.get("/sales.csv")
def export_sales_csv(db:DbSession,user:dict=Depends(require_roles(*ROLES)),start:date|None=None,end:date|None=None):
    if start and end and end<start:
        raise HTTPException(status_code=422,detail={"code":"invalid_date_range","message":"La fecha final debe ser igual o posterior a la inicial"})
    snapshot=build_snapshot(sales_data(db,user["company_id"],start,end),SalesReportRequest(start=start,end=end))
    return Response(csv_content(snapshot),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":"attachment; filename=salesia-ventas.csv"})


def saved_report(db,user,report_id):
    row=db.execute(text("SELECT snapshot FROM reports WHERE company_id=:company AND id=:id"),{"company":user["company_id"],"id":report_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404,detail={"code":"report_not_found","message":"No se encontró el reporte"})
    if row["snapshot"] is None:
        raise HTTPException(status_code=409,detail={"code":"legacy_report","message":"Este reporte antiguo no conserva su contenido. Genera uno nuevo con las fechas indicadas."})
    return row["snapshot"]


@router.get("/{report_id}/download")
def download_report(report_id:int,db:DbSession,user:dict=Depends(require_roles(*ROLES))):
    snapshot=saved_report(db,user,report_id)
    return Response(csv_content(snapshot),media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":f"attachment; filename=salesia-reporte-{report_id}.csv"})


@router.get("/{report_id}")
def get_report(report_id:int,db:DbSession,user:dict=Depends(require_roles(*ROLES))):
    return {"id":report_id,**saved_report(db,user,report_id)}


@router.get("/{report_id}/pdf")
def download_report_pdf(report_id:int,db:DbSession,user:dict=Depends(require_roles(*ROLES))):
    from app.services.pdf_documents import report_pdf
    return Response(report_pdf({"id":report_id,**saved_report(db,user,report_id)}),media_type="application/pdf",
                    headers={"Content-Disposition":f"attachment; filename=salesia-reporte-{report_id}.pdf","Cache-Control":"no-store"})
