from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.api.routes.sales import list_sales, void_sale
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.sales import SaleVoid, SaleCancellation


def test_seller_cannot_void_another_sellers_sale():
    class Database:
        calls = 0
        rolled_back = False

        def execute(self, *args, **kwargs):
            self.calls += 1
            assert self.calls == 1, "Must reject before reading details or changing stock"
            return self

        def mappings(self):
            return self

        def first(self):
            return {"id": 10, "status": "confirmed", "created_by": 99}

        def rollback(self):
            self.rolled_back = True

        def commit(self):
            pytest.fail("Unauthorized cancellation must not commit")

    db = Database()
    with pytest.raises(HTTPException) as error:
        void_sale(10, SaleCancellation(reason="Anulación solicitada", refund_confirmed=True, restock_confirmed=True), db, {"id": 2, "company_id": 1, "role": "seller"})
    assert error.value.status_code == 404
    assert db.rolled_back


def test_sales_reject_reversed_dates_before_querying_database():
    with pytest.raises(HTTPException) as error:
        list_sales(None, {"role": "manager"}, date(2026, 10, 2), date(2026, 10, 1))
    assert error.value.status_code == 422
    assert error.value.detail["code"] == "invalid_date_range"


def test_cancellation_requires_a_real_reason():
    with pytest.raises(ValidationError):
        SaleVoid(reason="   ")


@pytest.mark.parametrize("confirmation", [
    {},
    {"refund_confirmed": True},
    {"refund_confirmed": False, "restock_confirmed": True},
    {"refund_confirmed": True, "restock_confirmed": False},
])
def test_cancellation_requires_refund_and_physical_restock_confirmation(confirmation):
    with pytest.raises(ValidationError):
        SaleCancellation(reason="Devolución completa", **confirmation)


@pytest.mark.parametrize("endpoint", ["/sales/1", "/inventory", "/inventory/movements", "/orders", "/orders/1"])
def test_analyst_cannot_read_operational_details(endpoint):
    class NoDatabase:
        def execute(self, *args, **kwargs):
            pytest.fail("Unauthorized reads must not query data")

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "company_id": 1, "role": "analyst"}
    app.dependency_overrides[get_db] = lambda: NoDatabase()
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1" + endpoint).status_code == 403
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
