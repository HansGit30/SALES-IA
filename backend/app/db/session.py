from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

connect_args={"connect_timeout":settings.database_connect_timeout,"keepalives":1,"keepalives_idle":30,"keepalives_interval":10,"keepalives_count":3}
# Transaction poolers do not preserve per-connection prepared statements.
if make_url(settings.database_url).port == 6543:
    connect_args["prepare_threshold"]=None
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5,
                       pool_timeout=settings.database_pool_timeout, pool_recycle=settings.database_pool_recycle,
                       pool_use_lifo=True, hide_parameters=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
