"""Persist the exact rule inputs alongside the analysis that produced an insight."""
import json
from sqlalchemy import text


def persist_insight_trace(db,user,code,evidence,now):
    params={"company":user["company_id"],"user":user["id"],"code":code,"evidence":json.dumps(evidence),"now":now}
    dataset=db.execute(text("""INSERT INTO datasets(company_id,name,source,filters,created_by)
        VALUES (:company,:code,'insight_snapshot',CAST(:evidence AS jsonb),:user) RETURNING id"""),params).scalar_one()
    params["dataset"]=dataset
    variable=db.execute(text("""INSERT INTO dataset_variables(company_id,dataset_id,name,data_type,unit)
        VALUES (:company,:dataset,:code,'quantitative_continuous',:unit) RETURNING id"""),
        {**params,"unit":evidence.get("currency","units")}).scalar_one()
    if code=="sales_week_over_week_drop":
        values=[("previous_week",evidence["previous_7_days_revenue"]),("current_week",evidence["current_7_days_revenue"])]
    else:
        values=[("product:"+str(row["id"]),row["quantity"]) for row in evidence.get("products",[])]
    for source,value in values:
        db.execute(text("""INSERT INTO observations(company_id,dataset_id,variable_id,numeric_value,observed_at,source_ref)
            VALUES (:company,:dataset,:variable,:value,:now,:source)"""),{**params,"variable":variable,"value":value,"source":source})
    return db.execute(text("""INSERT INTO statistical_analyses(company_id,dataset_id,analysis_type,parameters,result,created_by)
        VALUES (:company,:dataset,'rule_evaluation',CAST(:parameters AS jsonb),CAST(:evidence AS jsonb),:user) RETURNING id"""),
        {**params,"parameters":json.dumps({"rule_code":code,"observation_count":len(values),"snapshot_limit":50 if code=="inventory_low_stock" else None})}).scalar_one()
