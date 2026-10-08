import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.api.routes import insights
from app.services.insight_rules import revenue_drop, weekly_window, insight_key


def test_weekly_window_handles_month_and_leap_day():
    window = weekly_window(date(2024, 3, 2))
    assert window["start"] == date(2024, 2, 25)
    assert window["previous_end"] == date(2024, 2, 24)
    assert window["exclusive_end"] == date(2024, 3, 3)


@pytest.mark.parametrize("previous,current,trigger", [("100","85",True),("100","85.01",False),("0","10",False)])
def test_revenue_drop_threshold(previous,current,trigger):
    assert (revenue_drop(Decimal(previous),Decimal(current)) is not None) == trigger


def test_key_is_stable_for_rule_and_day():
    assert insight_key("stock",date(2026,10,1)) == "stock:2026-10-01"
    assert insight_key("stock",date(2026,10,1)) != insight_key("stock",date(2026,10,2))


class FixedClock:
    @staticmethod
    def now(tz):
        return datetime(2026,10,2,12,tzinfo=UTC)


def test_generation_is_repeatable_and_resolves_without_duplicate_records(monkeypatch):
    monkeypatch.setattr(insights,"datetime",FixedClock)
    monkeypatch.setattr(insights,"persist_insight_trace",lambda *args: 123)

    class Database:
        records = {}
        current = Decimal("50")
        stock = True
        result = None
        commits = 0

        def execute(self, statement, params):
            sql = str(statement)
            assert set(statement.compile().params).issubset(params)
            if "AS period" in sql:
                self.result = [{"period":"current","revenue":self.current,"sales":1},{"period":"previous","revenue":Decimal("100"),"sales":2}]
            elif "SELECT currency" in sql:
                self.result = "PEN"
            elif "COUNT(*) OVER()" in sql:
                self.result = [{"id":1,"name":"Producto","sku":"A","quantity":Decimal("2"),"total_count":1}] if self.stock else []
            elif sql.startswith("SELECT id,evidence"):
                self.result = self.records.get(params["key"])
            elif sql.startswith("INSERT INTO insights"):
                self.records[params["key"]] = {"id":len(self.records)+1,"evidence":json.loads(params["evidence"]),"status":"active"}
            elif sql.startswith("UPDATE insights SET title"):
                self.records[params["key"]].update(evidence=json.loads(params["evidence"]),status="active")
            elif sql.startswith("UPDATE insights SET status='resolved'"):
                row = self.records.get(params["key"])
                self.result = row["id"] if row and row["status"] == "active" else None
                if self.result is not None:
                    row["status"] = "resolved"
            return self

        def mappings(self): return self
        def all(self): return self.result
        def first(self): return self.result
        def scalar_one(self): return self.result
        def scalar_one_or_none(self): return self.result
        def commit(self): self.commits += 1
        def rollback(self): pytest.fail("Unexpected rollback")

    db = Database()
    user = {"id":2,"company_id":1,"role":"admin"}
    first = insights.generate_insights(db,user,date(2026,10,1))
    repeated = insights.generate_insights(db,user,date(2026,10,1))
    assert first["created"] == 2
    assert repeated["created"] == 0 and repeated["unchanged"] == 2
    db.current = Decimal("100")
    db.stock = False
    resolved = insights.generate_insights(db,user,date(2026,10,1))
    assert resolved["matched"] == 0 and resolved["resolved"] == 2
    assert len(db.records) == 2
    assert all(row["status"] == "resolved" for row in db.records.values())
    db.current = Decimal("50")
    db.stock = True
    reopened = insights.generate_insights(db,user,date(2026,10,1))
    assert reopened["updated"] == 2 and reopened["created"] == 0


def test_incomplete_day_is_rejected_before_database_access(monkeypatch):
    monkeypatch.setattr(insights,"datetime",FixedClock)
    with pytest.raises(HTTPException) as error:
        insights.generate_insights(None,{"company_id":1},date(2026,10,2))
    assert error.value.status_code == 422
