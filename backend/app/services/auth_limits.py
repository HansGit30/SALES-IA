"""Persistent fixed windows. Keys are HMAC digests, never raw account/IP data."""
import hashlib
import hmac
import math

from fastapi import HTTPException
from sqlalchemy import text

from app.core.config import settings


def consume_attempts(db, buckets: list[tuple[str, int]]):
    retry_after = 0
    try:
        # Bound cleanup work per request; expired buckets also reset on reuse.
        db.execute(text("""DELETE FROM auth_rate_limits WHERE bucket_key IN (
            SELECT bucket_key FROM auth_rate_limits WHERE expires_at <= now()
            ORDER BY expires_at LIMIT 100
        )"""))
        # Stable order prevents opposite lock ordering across requests.
        for value, limit in sorted(buckets):
            key = hmac.new(settings.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()
            row = db.execute(text("""
                INSERT INTO auth_rate_limits(bucket_key,attempts,expires_at)
                VALUES (:key,1,now()+make_interval(secs => :window))
                ON CONFLICT (bucket_key) DO UPDATE SET
                    attempts=CASE WHEN auth_rate_limits.expires_at<=now() THEN 1
                                  ELSE LEAST(auth_rate_limits.attempts+1,:cap) END,
                    expires_at=CASE WHEN auth_rate_limits.expires_at<=now()
                                    THEN now()+make_interval(secs => :window)
                                    ELSE auth_rate_limits.expires_at END
                RETURNING attempts,EXTRACT(EPOCH FROM (expires_at-now())) AS remaining
            """), {"key": key, "window": settings.auth_window_seconds, "cap": limit+1}).mappings().one()
            if row["attempts"] > limit:
                retry_after = max(retry_after, max(1, math.ceil(row["remaining"])))
        # Persist attempts even when credentials fail or the request is rejected.
        db.commit()
    except Exception:
        db.rollback()
        raise
    if retry_after:
        raise HTTPException(status_code=429,
                            detail={"code": "auth_rate_limited", "message": f"Demasiados intentos. Inténtalo de nuevo en {retry_after} segundos."},
                            headers={"Retry-After": str(retry_after)})
