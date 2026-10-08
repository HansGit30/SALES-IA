import json
import math
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text

from app.core.dependencies import DbSession, require_roles

router = APIRouter(prefix="/probability", tags=["Probabilidad"])


class BayesRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)
    event_a: str = Field(min_length=1, max_length=160)
    event_b: str = Field(min_length=1, max_length=160)
    p_a: float = Field(ge=0, le=1)
    p_b_given_a: float = Field(ge=0, le=1)
    p_b: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def consistent_events(self):
        joint = self.p_a * self.p_b_given_a
        if joint > self.p_b + 1e-12 or self.p_b - joint > 1 - self.p_a + 1e-12:
            raise ValueError("P(A), P(B|A) y P(B) no describen eventos compatibles")
        return self


class Outcome(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    value: float = Field(gt=-1e12, lt=1e12)
    probability: float = Field(ge=0, le=1)


class RandomVariableRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=120)
    outcomes: list[Outcome] = Field(min_length=1, max_length=1000)
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def probabilities_sum_to_one(self):
        if len({x.value for x in self.outcomes}) != len(self.outcomes):
            raise ValueError("Cada valor debe aparecer una sola vez; combina sus probabilidades")
        if not math.isclose(math.fsum(x.probability for x in self.outcomes), 1.0, rel_tol=0, abs_tol=1e-8):
            raise ValueError("Las probabilidades de todos los resultados deben sumar 1")
        expectation = math.fsum(x.value * x.probability for x in self.outcomes)
        variance = math.fsum((x.value - expectation) ** 2 * x.probability for x in self.outcomes)
        if not math.isfinite(variance) or variance >= 1e14:
            raise ValueError("La varianza excede la capacidad de almacenamiento; utiliza una unidad de menor escala")
        return self


@router.post("/bayes")
def bayes(payload: BayesRequest, db: DbSession, user: dict = Depends(require_roles("admin", "manager", "analyst"))):
    result = payload.p_b_given_a * payload.p_a / payload.p_b
    if result > 1 + 1e-12:
        raise HTTPException(status_code=422, detail={"code": "inconsistent_probabilities", "message": "Las probabilidades ingresadas producen P(A|B) mayor que 1"})
    result = min(result, 1.0)
    params = payload.model_dump()
    output = {**params, "p_a_given_b": result, "interpretation": f"Si se observa B, la probabilidad de A es {result:.4f} ({result*100:.2f}%)."}
    try:
        dataset_id = db.execute(text("""INSERT INTO datasets(company_id,name,source,filters,created_by)
                                        VALUES (:company_id,'Análisis Bayes','manual',CAST(:filters AS jsonb),:user_id) RETURNING id"""), {"company_id": user["company_id"], "filters": json.dumps(params), "user_id": user["id"]}).scalar_one()
        analysis_id = db.execute(text("""INSERT INTO statistical_analyses(company_id,dataset_id,analysis_type,parameters,result,created_by)
                                         VALUES (:company_id,:dataset_id,'bayes',CAST(:parameters AS jsonb),CAST(:result AS jsonb),:user_id) RETURNING id"""), {"company_id": user["company_id"], "dataset_id": dataset_id, "parameters": json.dumps(params), "result": json.dumps(output), "user_id": user["id"]}).scalar_one()
        db.execute(text("""INSERT INTO bayes_analyses(company_id,analysis_id,event_a,event_b,p_a,p_b_given_a,p_b,p_a_given_b)
                          VALUES (:company_id,:analysis_id,:event_a,:event_b,:p_a,:p_b_given_a,:p_b,:p_a_given_b)"""), {"company_id": user["company_id"], "analysis_id": analysis_id, "event_a": payload.event_a, "event_b": payload.event_b, "p_a": payload.p_a, "p_b_given_a": payload.p_b_given_a, "p_b": payload.p_b, "p_a_given_b": result})
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
                          VALUES (:company_id,:user_id,'analytics.bayes_created','statistical_analysis',:analysis_id,CAST(:details AS jsonb))"""), {"company_id": user["company_id"], "user_id": user["id"], "analysis_id": str(analysis_id), "details": json.dumps(params)})
        db.commit()
        return {"analysis_id": analysis_id, **output}
    except Exception:
        db.rollback()
        raise


@router.post("/random-variables/analyze", status_code=201)
def analyze_random_variable(payload: RandomVariableRequest, db: DbSession, user: dict = Depends(require_roles("admin", "manager", "analyst"))):
    mean = math.fsum(item.value * item.probability for item in payload.outcomes)
    variance = math.fsum(((item.value - mean) ** 2) * item.probability for item in payload.outcomes)
    std_dev = math.sqrt(variance)
    params = {"distribution": "discrete", "outcomes": [item.model_dump() for item in payload.outcomes]}
    output = {"mean": mean, "variance": variance, "standard_deviation": std_dev, "outcome_count": len(payload.outcomes), "probability_sum": sum(item.probability for item in payload.outcomes)}
    try:
        variable_id = db.execute(text("""INSERT INTO random_variables(company_id,name,distribution,parameters,description,created_by)
                                          VALUES (:company_id,:name,'discrete',CAST(:parameters AS jsonb),:description,:user_id) RETURNING id"""), {"company_id": user["company_id"], "name": payload.name, "parameters": json.dumps(params), "description": payload.description, "user_id": user["id"]}).scalar_one()
        dataset_id = db.execute(text("""INSERT INTO datasets(company_id,name,source,filters,created_by)
                                        VALUES (:company_id,:name,'manual',CAST(:filters AS jsonb),:user_id) RETURNING id"""), {"company_id": user["company_id"], "name": f"Variable aleatoria: {payload.name}", "filters": json.dumps({"random_variable_id": variable_id}), "user_id": user["id"]}).scalar_one()
        dataset_var_id = db.execute(text("""INSERT INTO dataset_variables(company_id,dataset_id,name,data_type)
                                            VALUES (:company_id,:dataset_id,:name,'quantitative_discrete') RETURNING id"""), {"company_id": user["company_id"], "dataset_id": dataset_id, "name": payload.name}).scalar_one()
        for index, outcome in enumerate(payload.outcomes):
            db.execute(text("""INSERT INTO observations(company_id,dataset_id,variable_id,numeric_value,source_ref)
                              VALUES (:company_id,:dataset_id,:variable_id,:value,:source_ref)"""), {"company_id": user["company_id"], "dataset_id": dataset_id, "variable_id": dataset_var_id, "value": Decimal(str(outcome.value)), "source_ref": str(index)})
        analysis_id = db.execute(text("""INSERT INTO statistical_analyses(company_id,dataset_id,analysis_type,parameters,result,created_by)
                                         VALUES (:company_id,:dataset_id,'random_variable',CAST(:parameters AS jsonb),CAST(:result AS jsonb),:user_id) RETURNING id"""), {"company_id": user["company_id"], "dataset_id": dataset_id, "parameters": json.dumps(params), "result": json.dumps(output), "user_id": user["id"]}).scalar_one()
        for metric, value in [("expectation", mean), ("variance", variance), ("standard_deviation", std_dev)]:
            db.execute(text("""INSERT INTO statistical_results(company_id,analysis_id,variable_id,metric,numeric_value,details)
                              VALUES (:company_id,:analysis_id,:variable_id,:metric,:value,CAST(:details AS jsonb))"""), {"company_id": user["company_id"], "analysis_id": analysis_id, "variable_id": dataset_var_id, "metric": metric, "value": Decimal(str(value)), "details": "{}"})
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
            VALUES (:company,:user,'analytics.random_variable_created','statistical_analysis',:id,CAST(:details AS jsonb))"""),
            {"company":user["company_id"],"user":user["id"],"id":str(analysis_id),"details":json.dumps({"dataset_id":dataset_id,"random_variable_id":variable_id})})
        db.commit()
        return {"random_variable_id": variable_id, "analysis_id": analysis_id, "name": payload.name, **output}
    except Exception:
        db.rollback()
        raise

