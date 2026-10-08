from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes import orders


USER = {"id": 2, "company_id": 1, "role": "seller"}


class OrderDatabase:
    def __init__(self, status="pending", price="1.50"):
        self.status = status
        self.price = Decimal(price)
        self.commits = 0
        self.rollbacks = 0
        self.writes = []
        self.result = None

    def execute(self, query, parameters):
        sql = str(query)
        if sql.startswith("SELECT * FROM orders"):
            self.result = {"id": 1, "status": self.status, "customer_id": None, "currency": "PEN"}
        elif "FROM order_details" in sql:
            self.result = [{"product_id": 3, "quantity": Decimal("2"), "unit_price": Decimal("1.50")}]
        elif "FROM products" in sql:
            self.result = {"unit_price": self.price}
        elif "FROM companies" in sql:
            self.result = "PEN"
        else:
            self.writes.append((sql, parameters))
        return self

    def mappings(self):
        return self

    def first(self):
        return self.result

    def all(self):
        return self.result

    def scalar_one(self):
        return self.result

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_order_rejects_repeated_products():
    with pytest.raises(ValidationError):
        orders.OrderCreate(items=[{"product_id": 3, "quantity": 1}, {"product_id": 3, "quantity": 2}])


def test_order_accepts_valid_pricing_and_rejects_invalid_percentages():
    payload=orders.OrderCreate(items=[{"product_id":3,"quantity":1,"discount_percent":10,"tax_percent":18}])
    assert payload.items[0].discount_percent==10
    for rate in [-1,101,"0.001"]:
        with pytest.raises(ValidationError):
            orders.OrderCreate(items=[{"product_id":3,"quantity":1,"discount_percent":rate}])


@pytest.mark.parametrize("status", ["converted", "cancelled"])
def test_only_pending_orders_can_be_converted(status):
    db = OrderDatabase(status=status)
    with pytest.raises(HTTPException) as error:
        orders.confirm_order(1, orders.OrderConfirm(payments=[{"method": "cash", "amount": 3}]), db, USER)
    assert error.value.status_code == 409
    assert db.commits == 0 and db.rollbacks == 1 and db.writes == []


def test_changed_catalog_price_blocks_conversion_before_stock_changes(monkeypatch):
    db = OrderDatabase(price="2.00")
    monkeypatch.setattr(orders, "persist_sale", lambda *args, **kwargs: pytest.fail("Must reject changed prices before creating sale"))
    with pytest.raises(HTTPException) as error:
        orders.confirm_order(1, orders.OrderConfirm(payments=[{"method": "cash", "amount": 3}]), db, USER)
    assert error.value.detail["code"] == "order_price_changed"
    assert db.commits == 0 and db.rollbacks == 1


def test_order_and_sale_share_one_commit(monkeypatch):
    db = OrderDatabase()

    def sale(payload, session, user, *, commit):
        assert commit is False
        assert session is db and db.commits == 0
        assert payload.items[0].quantity == Decimal("2")
        return {"id": 7}

    monkeypatch.setattr(orders, "persist_sale", sale)
    result = orders.confirm_order(1, orders.OrderConfirm(payments=[{"method": "cash", "amount": 3}]), db, USER)
    assert result["sale_id"] == 7
    assert db.commits == 1 and db.rollbacks == 0
    assert any("UPDATE orders" in sql and values["sale"] == 7 for sql, values in db.writes)
    assert any("audit_logs" in sql for sql, _ in db.writes)


def test_sale_failure_keeps_order_pending(monkeypatch):
    db = OrderDatabase()

    def unavailable(*args, **kwargs):
        raise HTTPException(status_code=409, detail={"code": "insufficient_stock"})

    monkeypatch.setattr(orders, "persist_sale", unavailable)
    with pytest.raises(HTTPException):
        orders.confirm_order(1, orders.OrderConfirm(payments=[{"method": "cash", "amount": 3}]), db, USER)
    assert db.commits == 0 and db.rollbacks == 1 and db.writes == []


def test_converted_order_cannot_be_cancelled():
    db = OrderDatabase(status="converted")
    with pytest.raises(HTTPException) as error:
        orders.cancel_order(1, orders.SaleVoid(reason="Cancelación"), db, USER)
    assert error.value.status_code == 409
    assert db.commits == 0 and db.writes == []
