import json
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text

from app.core.dependencies import DbSession, get_current_user, require_roles

router = APIRouter(prefix="/analytics", tags=["Analytics"])

DASHBOARD_FILTER = """
    AND (CAST(:branch_id AS bigint) IS NULL OR s.branch_id=:branch_id)
    AND (CAST(:employee_id AS bigint) IS NULL OR s.seller_id=:employee_id)
    AND ((CAST(:product_id AS bigint) IS NULL AND CAST(:category_id AS bigint) IS NULL) OR EXISTS (
        SELECT 1 FROM sale_details d
        JOIN products p ON p.company_id=d.company_id AND p.id=d.product_id
        WHERE d.company_id=s.company_id AND d.sale_id=s.id
          AND (CAST(:product_id AS bigint) IS NULL OR d.product_id=:product_id)
          AND (CAST(:category_id AS bigint) IS NULL OR p.category_id=:category_id)
    ))
"""


@router.get("/filter-options")
def filter_options(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "analyst", "seller"))):
    parameters = {"company_id": user["company_id"], "user_id": user["id"] if user["role"] == "seller" else None}
    employees = db.execute(text("SELECT id,full_name AS name,is_active FROM employees WHERE company_id=:company_id AND (CAST(:user_id AS bigint) IS NULL OR user_id=:user_id) ORDER BY full_name,id"), parameters).mappings().all()
    products = db.execute(text("SELECT id,name,sku,category_id,is_active FROM products WHERE company_id=:company_id ORDER BY name,id"), parameters).mappings().all()
    categories = db.execute(text("SELECT id,name,is_active FROM categories WHERE company_id=:company_id ORDER BY name,id"), parameters).mappings().all()
    return {"employees": [dict(row) for row in employees], "products": [dict(row) for row in products], "categories": [dict(row) for row in categories]}


class SalesAnalysisRequest(BaseModel):
    metric: str = Field(pattern="^(sales_total|units_per_sale)$")
    start: date | None = None
    end: date | None = None

    @model_validator(mode="after")
    def validate_range(self):
        if self.start and self.end and self.end < self.start:
            raise ValueError("La fecha final debe ser igual o posterior a la inicial")
        return self


def median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / Decimal("2")


@router.get("/summary")
def summary(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "analyst", "seller")), start: date | None = None, end: date | None = None, employee_id: Annotated[int | None, Query(gt=0)] = None, product_id: Annotated[int | None, Query(gt=0)] = None, category_id: Annotated[int | None, Query(gt=0)] = None, branch_id: Annotated[int | None, Query(gt=0)] = None):
    if start and end and end < start:
        raise HTTPException(status_code=422, detail={"code": "invalid_date_range", "message": "La fecha final debe ser igual o posterior a la inicial"})
    result = db.execute(
        text(f"""SELECT COUNT(*) AS transaction_count,COUNT(DISTINCT customer_id) AS customer_count, COALESCE(SUM(total),0) AS revenue,
                      COALESCE(AVG(total),0) AS average_ticket,
                      COALESCE(percentile_cont(0.5) WITHIN GROUP (ORDER BY total),0) AS median_ticket
                 FROM sales s WHERE company_id=:company_id AND status='confirmed' AND (CAST(:seller_id AS bigint) IS NULL OR created_by=:seller_id) {DASHBOARD_FILTER}
                   AND (CAST(:start AS date) IS NULL OR sold_at >= (CAST(:start AS timestamp) AT TIME ZONE 'America/Lima'))
                   AND (CAST(:end AS date) IS NULL OR sold_at < ((CAST(:end AS date) + INTERVAL '1 day') AT TIME ZONE 'America/Lima'))"""),
        {"company_id": user["company_id"], "seller_id": user["id"] if user["role"] == "seller" else None, "start": start, "end": end, "employee_id": employee_id, "product_id": product_id, "category_id": category_id,"branch_id":branch_id},
    ).mappings().one()
    currency = db.execute(text("SELECT currency FROM companies WHERE id=:company_id"), {"company_id": user["company_id"]}).scalar_one()
    return {"currency": currency, **{key: str(value) if key in {"revenue", "average_ticket", "median_ticket"} else value for key, value in result.items()}}


@router.get("/sales-series")
def sales_series(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "analyst", "seller")), start: date | None = None, end: date | None = None, employee_id: Annotated[int | None, Query(gt=0)] = None, product_id: Annotated[int | None, Query(gt=0)] = None, category_id: Annotated[int | None, Query(gt=0)] = None, branch_id: Annotated[int | None, Query(gt=0)] = None):
    if start and end and end < start:
        raise HTTPException(status_code=422, detail={"code": "invalid_date_range", "message": "La fecha final debe ser igual o posterior a la inicial"})
    rows = db.execute(
        text(f"""SELECT (sold_at AT TIME ZONE 'America/Lima')::date AS day, COUNT(*) AS transactions, SUM(total) AS revenue
                 FROM sales s WHERE company_id=:company_id AND status='confirmed' AND (CAST(:seller_id AS bigint) IS NULL OR created_by=:seller_id) {DASHBOARD_FILTER}
                   AND (CAST(:start AS date) IS NULL OR sold_at >= (CAST(:start AS timestamp) AT TIME ZONE 'America/Lima'))
                   AND (CAST(:end AS date) IS NULL OR sold_at < ((CAST(:end AS date) + INTERVAL '1 day') AT TIME ZONE 'America/Lima'))
                GROUP BY 1 ORDER BY 1"""),
        {"company_id": user["company_id"], "seller_id": user["id"] if user["role"] == "seller" else None, "start": start, "end": end, "employee_id": employee_id, "product_id": product_id, "category_id": category_id,"branch_id":branch_id},
    ).mappings().all()
    return [{"day": row["day"].isoformat(), "transactions": row["transactions"], "revenue": str(row["revenue"])} for row in rows]


@router.post("/analyses", status_code=201)
def analyze_sales(payload: SalesAnalysisRequest, db: DbSession, user: dict = Depends(require_roles("admin", "manager", "analyst"))):
    company_id = user["company_id"]
    params = {"metric": payload.metric, "start": payload.start.isoformat() if payload.start else None, "end": payload.end.isoformat() if payload.end else None, "status": "confirmed"}
    if payload.metric == "sales_total":
        observations = db.execute(text("""SELECT id::text AS source_ref,total AS value,sold_at AS observed_at FROM sales
                                          WHERE company_id=:company_id AND status='confirmed' AND (CAST(:seller_id AS bigint) IS NULL OR created_by=:seller_id)
                                            AND (CAST(:start AS date) IS NULL OR sold_at >= (CAST(:start AS timestamp) AT TIME ZONE 'America/Lima'))
                                            AND (CAST(:end AS date) IS NULL OR sold_at < ((CAST(:end AS date)+INTERVAL '1 day') AT TIME ZONE 'America/Lima'))
                                          ORDER BY sold_at,id"""), {"company_id": company_id, "seller_id": None, "start": payload.start, "end": payload.end}).mappings().all()
        variable_name, data_type, unit = "Monto total por venta", "quantitative_continuous", "currency"
    else:
        observations = db.execute(text("""SELECT s.id::text AS source_ref,SUM(d.quantity) AS value,s.sold_at AS observed_at
                                          FROM sales s JOIN sale_details d ON d.company_id=s.company_id AND d.sale_id=s.id
                                         WHERE s.company_id=:company_id AND s.status='confirmed' AND (CAST(:seller_id AS bigint) IS NULL OR s.created_by=:seller_id)
                                           AND (CAST(:start AS date) IS NULL OR s.sold_at >= (CAST(:start AS timestamp) AT TIME ZONE 'America/Lima'))
                                           AND (CAST(:end AS date) IS NULL OR s.sold_at < ((CAST(:end AS date)+INTERVAL '1 day') AT TIME ZONE 'America/Lima'))
                                         GROUP BY s.id,s.sold_at ORDER BY s.sold_at,s.id"""), {"company_id": company_id, "seller_id": None, "start": payload.start, "end": payload.end}).mappings().all()
        variable_name, data_type, unit = "Unidades por venta", "quantitative_discrete", "units"
    values = [Decimal(row["value"]) for row in observations]
    if payload.metric == "units_per_sale" and any(value != value.to_integral_value() for value in values):
        data_type = "quantitative_continuous"
    if not values:
        raise HTTPException(status_code=422, detail={"code": "empty_dataset", "message": "No hay ventas confirmadas en el periodo indicado"})
    average = sum(values, Decimal("0")) / Decimal(len(values))
    center = median(values)
    result = {"count": len(values), "mean": str(average), "median": str(center), "minimum": str(min(values)), "maximum": str(max(values)), "metric": payload.metric}
    try:
        dataset_id = db.execute(text("""INSERT INTO datasets(company_id,name,source,filters,created_by)
                                        VALUES (:company_id,:name,'sales',CAST(:filters AS jsonb),:user_id) RETURNING id"""), {"company_id": company_id, "name": f"Análisis de ventas {payload.metric}", "filters": json.dumps(params), "user_id": user["id"]}).scalar_one()
        variable_id = db.execute(text("""INSERT INTO dataset_variables(company_id,dataset_id,name,data_type,unit)
                                         VALUES (:company_id,:dataset_id,:name,:data_type,:unit) RETURNING id"""), {"company_id": company_id, "dataset_id": dataset_id, "name": variable_name, "data_type": data_type, "unit": unit}).scalar_one()
        for row in observations:
            db.execute(text("""INSERT INTO observations(company_id,dataset_id,variable_id,numeric_value,observed_at,source_ref)
                              VALUES (:company_id,:dataset_id,:variable_id,:value,:observed_at,:source_ref)"""), {"company_id": company_id, "dataset_id": dataset_id, "variable_id": variable_id, "value": row["value"], "observed_at": row["observed_at"], "source_ref": row["source_ref"]})
        analysis_id = db.execute(text("""INSERT INTO statistical_analyses(company_id,dataset_id,analysis_type,parameters,result,created_by)
                                         VALUES (:company_id,:dataset_id,'descriptive',CAST(:parameters AS jsonb),CAST(:result AS jsonb),:user_id) RETURNING id"""), {"company_id": company_id, "dataset_id": dataset_id, "parameters": json.dumps(params), "result": json.dumps(result), "user_id": user["id"]}).scalar_one()
        for metric, value in [("count", Decimal(len(values))), ("mean", average), ("median", center), ("minimum", min(values)), ("maximum", max(values))]:
            db.execute(text("""INSERT INTO statistical_results(company_id,analysis_id,variable_id,metric,numeric_value,details)
                              VALUES (:company_id,:analysis_id,:variable_id,:metric,:value,CAST(:details AS jsonb))"""), {"company_id": company_id, "analysis_id": analysis_id, "variable_id": variable_id, "metric": metric, "value": value, "details": "{}"})
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                          VALUES (:company_id,:user_id,'analytics.analysis_created','statistical_analysis',:analysis_id,CAST(:details AS jsonb))"""), {"company_id": company_id, "user_id": user["id"], "analysis_id": str(analysis_id), "details": json.dumps(params)})
        db.commit()
        return {"id": analysis_id, "dataset_id": dataset_id, "created_at": "now", "parameters": params, "result": result}
    except Exception:
        db.rollback()
        raise


@router.get("/analyses")
def analysis_history(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "analyst")), limit: int = Query(default=50, ge=1, le=200)):
    rows = db.execute(text("""SELECT id,dataset_id,analysis_type,parameters,result,created_at FROM statistical_analyses
                              WHERE company_id=:company_id AND analysis_type<>'rule_evaluation' ORDER BY created_at DESC,id DESC LIMIT :limit"""), {"company_id": user["company_id"], "limit": limit}).mappings().all()
    return [dict(row) for row in rows]



@router.get("/breakdown")
def sales_breakdown(db: DbSession, user: dict = Depends(require_roles("admin", "manager", "analyst", "seller")), start: date | None = None, end: date | None = None, employee_id: Annotated[int | None, Query(gt=0)] = None, product_id: Annotated[int | None, Query(gt=0)] = None, category_id: Annotated[int | None, Query(gt=0)] = None, branch_id: Annotated[int | None, Query(gt=0)] = None):
    if start and end and end < start:
        raise HTTPException(422, detail="La fecha final debe ser igual o posterior a la inicial")
    params={"company_id":user["company_id"],"owner":user["id"] if user["role"]=="seller" else None,
            "start":start,"end":end,"employee_id":employee_id,"product_id":product_id,"category_id":category_id,"branch_id":branch_id}
    source=f"""WITH selected AS (SELECT s.* FROM sales s WHERE s.company_id=:company_id AND s.status='confirmed'
        AND (CAST(:owner AS bigint) IS NULL OR s.created_by=:owner) {DASHBOARD_FILTER}
        AND (CAST(:start AS date) IS NULL OR s.sold_at >= (CAST(:start AS timestamp) AT TIME ZONE 'America/Lima'))
        AND (CAST(:end AS date) IS NULL OR s.sold_at < ((CAST(:end AS date)+INTERVAL '1 day') AT TIME ZONE 'America/Lima')))
    """
    products=db.execute(text(source+"""SELECT d.product_id AS id,MAX(d.product_name_snapshot) AS name,s.currency,
        SUM(d.quantity) AS units,SUM(d.line_total) AS revenue,
        COALESCE(100*SUM(d.line_total)/NULLIF(SUM(SUM(d.line_total)) OVER(PARTITION BY s.currency),0),0) AS share_percent,COUNT(DISTINCT s.id) AS transactions
        FROM selected s JOIN sale_details d ON d.company_id=s.company_id AND d.sale_id=s.id
        JOIN products p ON p.company_id=d.company_id AND p.id=d.product_id
        WHERE (CAST(:product_id AS bigint) IS NULL OR d.product_id=:product_id)
        AND (CAST(:category_id AS bigint) IS NULL OR p.category_id=:category_id)
        GROUP BY d.product_id,s.currency ORDER BY revenue DESC,d.product_id LIMIT 20"""),params).mappings().all()
    sellers=db.execute(text(source+"""SELECT e.id,e.full_name AS name,s.currency,COUNT(*) AS transactions,SUM(s.total) AS revenue,AVG(s.total) AS average_ticket
        FROM selected s JOIN employees e ON e.company_id=s.company_id AND e.id=s.seller_id
        GROUP BY e.id,e.full_name,s.currency ORDER BY revenue DESC,e.id LIMIT 20"""),params).mappings().all()
    customers=db.execute(text(source+"""SELECT c.id,COALESCE(c.name,'Cliente general') AS name,s.currency,
        COUNT(*) AS transactions,SUM(s.total) AS revenue,AVG(s.total) AS average_ticket,
        COUNT(DISTINCT (s.sold_at AT TIME ZONE 'America/Lima')::date) AS purchase_days,
        MAX(s.sold_at) AS last_purchase
        FROM selected s LEFT JOIN customers c ON c.company_id=s.company_id AND c.id=s.customer_id
        GROUP BY c.id,c.name,s.currency ORDER BY revenue DESC,c.id NULLS LAST LIMIT 20"""),params).mappings().all()
    frequencies=db.execute(text(source+"""SELECT currency,
        CASE WHEN total<100 THEN 0 WHEN total<500 THEN 1 WHEN total<1000 THEN 2 WHEN total<5000 THEN 3 ELSE 4 END AS band,
        COUNT(*) AS frequency FROM selected GROUP BY currency,band ORDER BY currency,band"""),params).mappings().all()
    return {"customers":[dict(r) for r in customers],"products":[dict(r) for r in products],"sellers":[dict(r) for r in sellers],"frequencies":[dict(r) for r in frequencies],"ranking_limit":20}


@router.get("/datasets")
def list_datasets(db:DbSession,user:dict=Depends(require_roles("manager","analyst")),offset:int=Query(default=0,ge=0)):
    return [dict(row) for row in db.execute(text("""SELECT d.id,d.name,d.source,d.created_at,
        (SELECT COUNT(*) FROM dataset_variables v WHERE v.company_id=d.company_id AND v.dataset_id=d.id) AS variable_count,
        (SELECT COUNT(*) FROM observations o WHERE o.company_id=d.company_id AND o.dataset_id=d.id) AS observation_count
        FROM datasets d WHERE d.company_id=:company ORDER BY d.created_at DESC,d.id DESC LIMIT 26 OFFSET :offset"""),
        {"company":user["company_id"],"offset":offset}).mappings()]

@router.get("/datasets/{dataset_id}")
def dataset_detail(dataset_id:int,db:DbSession,user:dict=Depends(require_roles("manager","analyst")),offset:int=Query(default=0,ge=0)):
    params={"company":user["company_id"],"id":dataset_id,"offset":offset}
    dataset=db.execute(text("SELECT id,name,source,filters,created_at FROM datasets WHERE company_id=:company AND id=:id"),params).mappings().first()
    if dataset is None: raise HTTPException(404,detail="El conjunto de datos no existe en esta empresa")
    variables=db.execute(text("SELECT id,name,data_type,unit FROM dataset_variables WHERE company_id=:company AND dataset_id=:id ORDER BY id"),params).mappings().all()
    observations=db.execute(text("SELECT id,variable_id,numeric_value,text_value,source_ref,observed_at FROM observations WHERE company_id=:company AND dataset_id=:id ORDER BY id LIMIT 51 OFFSET :offset"),params).mappings().all()
    analyses=db.execute(text("SELECT id,analysis_type,parameters,result FROM statistical_analyses WHERE company_id=:company AND dataset_id=:id ORDER BY id DESC"),params).mappings().all()
    return {"dataset":dict(dataset),"variables":[dict(row) for row in variables],"observations":[dict(row) for row in observations],"analyses":[dict(row) for row in analyses]}
