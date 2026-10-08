from decimal import Decimal
from pathlib import Path
import re

import pytest

from app.api.routes.sales import money
from app.api.routes.analytics import median
from app.api.routes.probability import BayesRequest, RandomVariableRequest
from app.api.routes.inventory import Adjustment
from pydantic import ValidationError


def test_money_rounding_uses_half_up():
    assert money(Decimal("1.005")) == Decimal("1.01")
    assert money(Decimal("1.004")) == Decimal("1.00")


@pytest.mark.parametrize("quantity", [0, "0.000", "-0.000"])
def test_inventory_rejects_zero_movements(quantity):
    with pytest.raises(ValidationError):
        Adjustment(product_id=1, quantity_delta=quantity, reason="Ajuste manual")


def test_median_odd_and_even_samples():
    assert median([Decimal("1"), Decimal("9"), Decimal("4")]) == Decimal("4")
    assert median([Decimal("1"), Decimal("9")]) == Decimal("5")


def test_bayes_requires_positive_evidence_probability():
    with pytest.raises(ValidationError):
        BayesRequest(event_a="A", event_b="B", p_a=0.2, p_b_given_a=0.5, p_b=0)


def test_discrete_probabilities_must_sum_to_one():
    with pytest.raises(ValidationError):
        RandomVariableRequest(name="X", outcomes=[{"value": 0, "probability": 0.2}, {"value": 1, "probability": 0.3}])


def test_schema_contains_company_scoped_composite_foreign_keys():
    schema = (Path(__file__).parents[2] / "database" / "schema.sql").read_text(encoding="utf-8-sig")
    assert "FOREIGN KEY (company_id, sale_id) REFERENCES sales(company_id, id)" in schema
    assert "NUMERIC(14,2)" in schema


def test_schema_meets_required_minimum_of_twenty_business_tables():
    schema = (Path(__file__).parents[2] / "database" / "schema.sql").read_text(encoding="utf-8-sig")
    tables = set(re.findall(r"^CREATE TABLE\s+(\w+)", schema, flags=re.MULTILINE | re.IGNORECASE))
    assert len(tables - {"alembic_version"}) >= 20
