import statistics as calculations
import math
import json
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, FiniteFloat
from app.core.dependencies import DbSession, require_roles
from sqlalchemy import text
from app.services.audit import record_audit

router = APIRouter(prefix="/statistics", tags=["Estadística"], dependencies=[Depends(require_roles("admin", "manager", "analyst"))])


class ValuesRequest(BaseModel):
    values: list[FiniteFloat] = Field(min_length=1, max_length=100000)


def mean(payload: ValuesRequest):
    return {"count": len(payload.values), "mean": calculations.mean(payload.values)}


def median(payload: ValuesRequest):
    values = sorted(payload.values)
    middle = len(values) // 2
    value = values[middle] if len(values) % 2 else calculations.mean([values[middle - 1], values[middle]])
    return {"count": len(values), "median": value}


def compare(payload: ValuesRequest):
    average = calculations.mean(payload.values)
    ordered = sorted(payload.values)
    middle = len(ordered) // 2
    center = ordered[middle] if len(ordered) % 2 else calculations.mean([ordered[middle - 1], ordered[middle]])
    if not math.isfinite(average - center):
        raise HTTPException(status_code=422, detail="La diferencia excede el rango numérico; cambia la unidad de los datos")
    return {"count": len(ordered), "mean": average, "median": center, "difference": average - center}


def save_calculation(payload,db,user,operation,result):
    if len(payload.values)>10000 or any(abs(value)>=1e12 for value in payload.values):
        raise HTTPException(422,detail="Para guardar el análisis usa hasta 10 000 valores de magnitud menor a un billón.")
    try:
        params={"company":user["company_id"],"user":user["id"],"name":"Cálculo manual: "+operation}
        dataset=db.execute(text("INSERT INTO datasets(company_id,name,source,created_by) VALUES (:company,:name,'manual',:user) RETURNING id"),params).scalar_one()
        variable=db.execute(text("INSERT INTO dataset_variables(company_id,dataset_id,name,data_type) VALUES (:company,:dataset,'Valores ingresados','quantitative_continuous') RETURNING id"),{**params,"dataset":dataset}).scalar_one()
        db.execute(text("INSERT INTO observations(company_id,dataset_id,variable_id,numeric_value,source_ref) VALUES (:company,:dataset,:variable,:value,:ref)"),[{"company":user["company_id"],"dataset":dataset,"variable":variable,"value":Decimal(str(value)),"ref":str(index)} for index,value in enumerate(payload.values)])
        analysis=db.execute(text("""INSERT INTO statistical_analyses(company_id,dataset_id,analysis_type,parameters,result,created_by)
            VALUES (:company,:dataset,'descriptive_manual',CAST(:parameters AS jsonb),CAST(:result AS jsonb),:user) RETURNING id"""),{**params,"dataset":dataset,"parameters":json.dumps({"operation":operation}),"result":json.dumps(result)}).scalar_one()
        record_audit(db,user,"analytics.manual_created","statistical_analysis",analysis,{"dataset_id":dataset,"operation":operation})
        db.commit()
        return {**result,"analysis_id":analysis,"dataset_id":dataset}
    except Exception:
        db.rollback()
        raise

@router.post("/mean")
def saved_mean(payload:ValuesRequest,db:DbSession,user:dict=Depends(require_roles("admin","manager","analyst"))):
    return save_calculation(payload,db,user,"mean",mean(payload))

@router.post("/median")
def saved_median(payload:ValuesRequest,db:DbSession,user:dict=Depends(require_roles("admin","manager","analyst"))):
    return save_calculation(payload,db,user,"median",median(payload))

@router.post("/compare")
def saved_compare(payload:ValuesRequest,db:DbSession,user:dict=Depends(require_roles("admin","manager","analyst"))):
    return save_calculation(payload,db,user,"compare",compare(payload))
