import csv
import io
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.api.routes.reports import SalesReportRequest, build_snapshot, get_report
from app.services.reporting import summarize, csv_content, safe_cell


def row(total="20.00", status="confirmed", currency="PEN"):
    return {"id":1,"sold_at":datetime(2026,10,2,2,tzinfo=UTC),"status":status,"currency":currency,
            "subtotal":Decimal(total),"discount_total":Decimal("0"),"tax_total":Decimal("0"),
            "total":Decimal(total),"customer_name":"=1+1","seller_name":"Ana, Pérez"}


def test_report_excludes_voided_and_separates_currencies():
    result=summarize([row("10"),row("30"),row("999","voided"),row("5",currency="USD")])
    assert result["sales_count"]==3 and result["voided_count"]==1
    pen=next(group for group in result["by_currency"] if group["currency"]=="PEN")
    assert Decimal(pen["revenue"])==40
    assert Decimal(pen["average_ticket"])==20
    assert Decimal(pen["median_ticket"])==20


def test_empty_report_does_not_invent_a_currency():
    assert summarize([])=={"sales_count":0,"voided_count":0,"by_currency":[]}


@pytest.mark.parametrize("value", ["=1+1","+SUM(A1)","-1+1","@SUM(A1)","  =A1","\t=1+1"])
def test_csv_neutralizes_formula_like_text(value):
    assert safe_cell(value).startswith("'")


def test_saved_content_does_not_change_with_source_and_csv_preserves_text():
    source=row()
    snapshot=build_snapshot([source],SalesReportRequest())
    source["total"]=Decimal("999")
    assert snapshot["rows"][0]["total"]=="20.00"
    assert snapshot["rows"][0]["sold_at"].startswith("2026-10-01T21:00:00")
    output=csv_content(snapshot)
    assert output.startswith("\ufeff")
    rows=list(csv.reader(io.StringIO(output.lstrip("\ufeff"))))
    assert rows[1][3]=="'=1+1"
    assert rows[1][4]=="Ana, Pérez"
    assert rows[1][8]=="20.00"


def test_statistical_csv_exports_aggregates():
    snapshot=build_snapshot([row()],SalesReportRequest(report_type="statistical"))
    rows=list(csv.reader(io.StringIO(csv_content(snapshot).lstrip("\ufeff"))))
    assert rows[0][0]=="moneda" and rows[1][0]=="PEN"
    assert rows[1][1]=="1"


def test_retrieval_reads_saved_snapshot_and_company_scope_only():
    snapshot=build_snapshot([row()],SalesReportRequest())
    class Database:
        def execute(self,query,params):
            assert "FROM reports" in str(query) and "company_id=:company" in str(query)
            assert params=={"company":7,"id":12}
            return self
        def mappings(self):return self
        def first(self):return {"snapshot":snapshot}
    assert get_report(12,Database(),{"company_id":7})["summary"]==snapshot["summary"]


@pytest.mark.parametrize("endpoint", ["/reports","/reports/sales.csv","/reports/1","/reports/1/download"])
def test_seller_cannot_access_company_reports(endpoint):
    class NoDatabase:
        def execute(self,*args,**kwargs):pytest.fail("Unauthorized report read")
    previous=app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user]=lambda:{"id":1,"company_id":1,"role":"seller"}
    app.dependency_overrides[get_db]=lambda:NoDatabase()
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1"+endpoint).status_code==403
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
