import asyncio
import json
from types import SimpleNamespace
from sqlalchemy.exc import OperationalError, TimeoutError
from app.main import database_unavailable_handler


def test_operational_errors_have_safe_correlatable_reference(caplog):
    original=RuntimeError("secret password should never appear")
    error=OperationalError("SELECT secret",{"password":"sensitive"},original)
    request=SimpleNamespace(method="POST",scope={"route":SimpleNamespace(path="/sales")})
    response=asyncio.run(database_unavailable_handler(request,error))
    body=json.loads(response.body)
    assert response.status_code==503 and response.headers["retry-after"]=="1"
    assert len(body["detail"]["reference"])==12
    assert "secret" not in caplog.text and "sensitive" not in caplog.text
    assert body["detail"]["reference"] in caplog.text


def test_pool_exhaustion_returns_a_controlled_503():
    request=SimpleNamespace(method="GET",scope={})
    response=asyncio.run(database_unavailable_handler(request,TimeoutError("pool busy")))
    assert response.status_code==503
