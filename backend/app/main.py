from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError, TimeoutError as PoolTimeout
from sqlalchemy import text
from alembic.script import ScriptDirectory
from pathlib import Path
import logging
from uuid import uuid4

from app.api.router import api_router
from app.core.config import settings
from app.db.session import engine

app = FastAPI(title=settings.app_name, version="0.1.0", description="API empresarial de ventas, inventario y analítica")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Operación"])
def health():
    return {"status": "ok", "service": "salesia-api"}


@app.get("/ready", tags=["Operación"])
def readiness():
    try:
        expected = set(ScriptDirectory(str(Path(__file__).resolve().parents[1] / "alembic")).get_heads())
        with engine.connect() as connection:
            connection.execute(text("SET LOCAL statement_timeout = '3000ms'"))
            actual = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
        if actual != expected:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
    except Exception:
        logging.getLogger(__name__).warning("Readiness check failed")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ready"}

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, exc):
    return JSONResponse(status_code=409, content={"detail": {"code": "integrity_conflict", "message": "La operación entra en conflicto con datos existentes o relacionados"}})


@app.exception_handler(PoolTimeout)
@app.exception_handler(OperationalError)
async def database_unavailable_handler(request, exc):
    reference=uuid4().hex[:12]
    original=getattr(exc,"orig",exc)
    logging.getLogger(__name__).error("Database unavailable ref=%s method=%s route=%s error=%s sqlstate=%s disconnected=%s",
        reference,request.method,getattr(request.scope.get("route"),"path","unknown"),type(original).__name__,
        getattr(original,"sqlstate",None),getattr(exc,"connection_invalidated",False))
    return JSONResponse(status_code=503,headers={"Retry-After":"1"},content={"detail":{
        "code":"database_unavailable","reference":reference,
        "message":f"La base de datos no respondió a tiempo. Reintenta en unos segundos. Referencia: {reference}"}})


@app.exception_handler(ProgrammingError)
async def database_schema_handler(request, exc):
    logging.getLogger(__name__).error("Database query error class=%s sqlstate=%s",type(exc.orig).__name__,getattr(exc.orig,"sqlstate",None))
    return JSONResponse(status_code=503, content={"detail": {
        "code": "database_not_ready",
        "message": "La base de datos no está preparada para esta operación. Revisa las migraciones y los registros del backend."
    }})
