import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes.statistics import ValuesRequest, mean
from app.api.routes.probability import BayesRequest, RandomVariableRequest
from app.api.routes.analytics import SalesAnalysisRequest, analyze_sales


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_observations_are_rejected(value):
    with pytest.raises(ValidationError):
        ValuesRequest(values=[value])


def test_mean_avoids_intermediate_overflow():
    assert mean(ValuesRequest(values=[1e308, 1e308]))["mean"] == 1e308


@pytest.mark.parametrize("probabilities", [
    {"p_a": 0.8, "p_b_given_a": 0.9, "p_b": 0.2},
    {"p_a": 0.9, "p_b_given_a": 0.1, "p_b": 0.8},
])
def test_bayes_requires_a_possible_joint_distribution(probabilities):
    with pytest.raises(ValidationError):
        BayesRequest(event_a="Compra", event_b="Contacto", **probabilities)


def test_discrete_outcomes_must_be_unique():
    with pytest.raises(ValidationError):
        RandomVariableRequest(name="X", outcomes=[{"value": 1, "probability": 0.5}, {"value": 1, "probability": 0.5}])


def test_constant_random_variable_is_valid():
    result = RandomVariableRequest(name="X", outcomes=[{"value": 5, "probability": 1}])
    assert len(result.outcomes) == 1


@pytest.mark.parametrize("metric", ["sales_total", "units_per_sale"])
def test_sales_analysis_supplies_every_sql_parameter(metric):
    class EmptyDatabase:
        def execute(self, query, parameters):
            assert set(query.compile().params).issubset(parameters)
            assert parameters["company_id"] == 7
            return self

        def mappings(self):
            return self

        def all(self):
            return []

    with pytest.raises(HTTPException) as error:
        analyze_sales(SalesAnalysisRequest(metric=metric), EmptyDatabase(), {"id": 1, "company_id": 7, "role": "analyst"})
    assert error.value.detail["code"] == "empty_dataset"
