import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.core.dependencies import DbSession, require_roles
from app.services.insight_trace import persist_insight_trace
from app.services.insight_rules import weekly_window, revenue_drop, insight_key

router = APIRouter(prefix="/insights", tags=["Insights"])
ROLES = ("admin", "manager", "analyst")


@router.get("")
def list_insights(db: DbSession, user: dict = Depends(require_roles(*ROLES)),
                  limit: int = Query(default=26, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    rows = db.execute(text("""SELECT i.id,i.analysis_id,a.dataset_id,i.rule_code,i.title,i.message,i.evidence,i.severity,i.status,i.created_at,i.evaluated_at,i.resolved_at
                              FROM insights i LEFT JOIN statistical_analyses a ON a.company_id=i.company_id AND a.id=i.analysis_id WHERE i.company_id=:company
                              ORDER BY i.evaluated_at DESC,i.id DESC LIMIT :limit OFFSET :offset"""),
                      {"company": user["company_id"], "limit": limit, "offset": offset}).mappings().all()
    return [dict(row) for row in rows]


@router.post("/generate")
def generate_insights(db: DbSession, user: dict = Depends(require_roles(*ROLES)), end: date | None = None):
    now = datetime.now(UTC)
    today = now.astimezone(ZoneInfo("America/Lima")).date()
    end = end or today - timedelta(days=1)
    if end >= today:
        raise HTTPException(status_code=422, detail={"code": "incomplete_period", "message": "Elige una fecha hasta ayer para comparar semanas completas"})
    window = weekly_window(end)
    company = user["company_id"]
    counters = {"created": 0, "updated": 0, "unchanged": 0, "resolved": 0}
    try:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": f"salesia-insights:{company}"})
        weekly = db.execute(text("""SELECT CASE WHEN sold_at >= (CAST(:start AS timestamp) AT TIME ZONE 'America/Lima')
                                                THEN 'current' ELSE 'previous' END AS period,
                                           SUM(total) AS revenue,COUNT(*) AS sales
                                      FROM sales WHERE company_id=:company AND status='confirmed'
                                        AND sold_at >= (CAST(:previous_start AS timestamp) AT TIME ZONE 'America/Lima')
                                        AND sold_at < (CAST(:exclusive_end AS timestamp) AT TIME ZONE 'America/Lima')
                                     GROUP BY 1"""), {"company": company, **window}).mappings().all()
        totals = {row["period"]: row for row in weekly}
        previous = Decimal(totals.get("previous", {}).get("revenue", 0))
        current = Decimal(totals.get("current", {}).get("revenue", 0))
        currency = db.execute(text("SELECT currency FROM companies WHERE id=:company"), {"company": company}).scalar_one()
        drop = revenue_drop(previous, current)
        candidates = {}
        keys = {
            "sales_week_over_week_drop": insight_key("sales_week_over_week_drop", end),
            "inventory_low_stock": insight_key("inventory_low_stock", today),
        }
        if drop:
            evidence = {**drop, "currency": currency, "period_days": 7, "timezone": "America/Lima",
                        "start": str(window["start"]), "end": str(end),
                        "previous_start": str(window["previous_start"]), "previous_end": str(window["previous_end"]),
                        "current_sales": totals.get("current", {}).get("sales", 0),
                        "previous_sales": totals.get("previous", {}).get("sales", 0)}
            candidates["sales_week_over_week_drop"] = ("Los ingresos semanales bajaron",
                f"Los ingresos confirmados cayeron {abs(Decimal(drop['change_percent'])):.2f}% frente a los siete días anteriores.", evidence)
        stock = db.execute(text("""SELECT p.id,p.name,p.sku,i.quantity,COUNT(*) OVER() AS total_count
                                     FROM inventory i JOIN products p ON p.company_id=i.company_id AND p.id=i.product_id
                                    WHERE i.company_id=:company AND p.is_active=TRUE AND i.quantity<=5
                                    ORDER BY i.quantity,p.id LIMIT 50"""), {"company": company}).mappings().all()
        if stock:
            evidence = {"inventory_scope":"general", "threshold_units": 5, "snapshot_day": str(today), "total_count": stock[0]["total_count"],
                        "products": [{"id": row["id"], "name": row["name"], "sku": row["sku"], "quantity": str(row["quantity"])} for row in stock]}
            candidates["inventory_low_stock"] = ("Productos con stock bajo",
                f"{stock[0]['total_count']} productos activos tienen cinco unidades o menos.", evidence)
        for code, key in keys.items():
            params = {"company": company, "key": key, "now": now}
            if code not in candidates:
                resolved = db.execute(text("""UPDATE insights SET status='resolved',resolved_at=:now,evaluated_at=:now
                                               WHERE company_id=:company AND dedupe_key=:key AND status='active' RETURNING id"""), params).scalar_one_or_none()
                if resolved is not None:
                    counters["resolved"] += 1
                continue
            title, message, evidence = candidates[code]
            existing = db.execute(text("SELECT id,evidence,status,analysis_id FROM insights WHERE company_id=:company AND dedupe_key=:key"), params).mappings().first()
            analysis_id=existing.get("analysis_id") if existing else None
            if not existing or existing["evidence"]!=evidence or analysis_id is None:
                analysis_id=persist_insight_trace(db,user,code,evidence,now)
            params["analysis_id"]=analysis_id
            params.update({"code": code, "title": title, "message": message, "evidence": json.dumps(evidence)})
            if existing:
                counters["unchanged" if existing["evidence"] == evidence and existing["status"] == "active" else "updated"] += 1
                db.execute(text("""UPDATE insights SET title=:title,message=:message,analysis_id=:analysis_id,evidence=CAST(:evidence AS jsonb),
                                      status='active',resolved_at=NULL,evaluated_at=:now
                                    WHERE company_id=:company AND dedupe_key=:key"""), params)
            else:
                db.execute(text("""INSERT INTO insights(company_id,analysis_id,rule_code,title,message,evidence,severity,dedupe_key,status,evaluated_at)
                                   VALUES (:company,:analysis_id,:code,:title,:message,CAST(:evidence AS jsonb),'warning',:key,'active',:now)"""), params)
                counters["created"] += 1
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                           VALUES (:company,:user,'insights.evaluated','company',:id,CAST(:details AS jsonb))"""),
                   {"company": company, "user": user["id"], "id": str(company),
                    "details": json.dumps({**counters, "sales_end": str(end), "inventory_day": str(today)})})
        db.commit()
        return {**counters, "matched": len(candidates), "generated_at": now.isoformat(),
                "sales_period": {key: str(value) for key, value in window.items()}, "inventory_day": str(today)}
    except Exception:
        db.rollback()
        raise


@router.get("/{insight_id}/trace")
def insight_trace(insight_id:int,db:DbSession,user:dict=Depends(require_roles(*ROLES))):
    row=db.execute(text("""SELECT i.id,i.analysis_id,a.dataset_id,a.analysis_type,a.parameters,a.result,a.created_at,
        d.name AS dataset_name,d.source,d.filters FROM insights i
        LEFT JOIN statistical_analyses a ON a.company_id=i.company_id AND a.id=i.analysis_id
        LEFT JOIN datasets d ON d.company_id=a.company_id AND d.id=a.dataset_id
        WHERE i.company_id=:company AND i.id=:id"""),{"company":user["company_id"],"id":insight_id}).mappings().first()
    if row is None: raise HTTPException(404,detail="El hallazgo no existe en esta empresa")
    if row["analysis_id"] is None: return {"available":False,"observations":[]}
    observations=db.execute(text("""SELECT o.source_ref,o.numeric_value,o.observed_at,v.name,v.unit
        FROM observations o JOIN dataset_variables v ON v.dataset_id=o.dataset_id AND v.company_id=o.company_id AND v.id=o.variable_id
        WHERE o.company_id=:company AND o.dataset_id=:dataset ORDER BY o.id LIMIT 100"""),
        {"company":user["company_id"],"dataset":row["dataset_id"]}).mappings().all()
    return {"available":True,**dict(row),"observations":[dict(r) for r in observations]}
