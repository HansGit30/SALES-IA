from datetime import date
from decimal import Decimal

import pytest

from app.api.routes.analytics import summary, sales_series


@pytest.mark.parametrize("function", [summary, sales_series])
@pytest.mark.parametrize("filters", [{}, {"employee_id": 17, "product_id": 22, "category_id": 3}])
def test_dashboard_queries_keep_company_seller_and_local_day_scope(function, filters):
    class Database:
        def execute(self, statement, parameters):
            sql = str(statement)
            if "FROM sales" in sql:
                assert "America/Lima" in sql
                assert "status='confirmed'" in sql
                assert parameters["company_id"] == 4
                assert parameters["seller_id"] == 8
                assert parameters["start"] == date(2026, 9, 1)
                assert parameters["end"] == date(2026, 9, 30)
                for key in ("employee_id", "product_id", "category_id"):
                    assert parameters[key] == filters.get(key)
                assert "EXISTS" in sql
                assert "d.company_id=s.company_id AND d.sale_id=s.id" in sql
                assert set(statement.compile().params).issubset(parameters)
            return self

        def mappings(self):
            return self

        def one(self):
            return {"transaction_count": 0, "revenue": Decimal("0"), "average_ticket": Decimal("0"), "median_ticket": Decimal("0")}

        def all(self):
            return []

        def scalar_one(self):
            return "PEN"

    result = function(Database(), {"id":8,"company_id":4,"role":"seller"}, date(2026,9,1), date(2026,9,30), **filters)
    if function is summary:
        assert result["currency"] == "PEN"
        assert result["transaction_count"] == 0
    else:
        assert result == []
