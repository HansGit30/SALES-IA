from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.core.dependencies import DbSession, require_roles

router = APIRouter(prefix="/audit", tags=["Auditoría"])


@router.get("")
def list_audit_logs(db: DbSession, user: dict = Depends(require_roles("admin")), limit: int = Query(default=26, ge=1, le=100), offset: int = Query(default=0, ge=0),
                    action: str | None = Query(default=None, max_length=100), start: date | None = None, end: date | None = None):
    if start and end and end < start:
        raise HTTPException(status_code=422, detail="La fecha final debe ser igual o posterior a la inicial")
    rows = db.execute(text("""SELECT a.id,a.action,a.entity_type,a.entity_id,a.details,a.created_at,u.email AS actor_email
                              FROM audit_logs a LEFT JOIN users u ON u.company_id=a.company_id AND u.id=a.user_id
                             WHERE a.company_id=:company_id
                               AND (CAST(:action AS text) IS NULL OR a.action=:action)
                               AND (CAST(:start AS date) IS NULL OR a.created_at >= (CAST(:start AS timestamp) AT TIME ZONE 'America/Lima'))
                               AND (CAST(:end AS date) IS NULL OR a.created_at < ((CAST(:end AS date)+INTERVAL '1 day') AT TIME ZONE 'America/Lima'))
                             ORDER BY a.created_at DESC,a.id DESC LIMIT :limit OFFSET :offset"""), {"company_id": user["company_id"], "limit": limit,"offset": offset,"action": action or None,"start": start,"end": end}).mappings().all()
    return [dict(row) for row in rows]


@router.get("/actions")
def audit_actions(db: DbSession, user: dict = Depends(require_roles("admin"))):
    return list(db.execute(text("SELECT DISTINCT action FROM audit_logs WHERE company_id=:company ORDER BY action"),
                           {"company": user["company_id"]}).scalars().all())
