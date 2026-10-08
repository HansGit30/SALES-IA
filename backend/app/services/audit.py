import json
from sqlalchemy import text


def record_audit(db,user,action,entity,entity_id,details=None):
    db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
        VALUES (:company,:user,:action,:entity,:id,CAST(:details AS jsonb))"""),
        {"company":user["company_id"],"user":user["id"],"action":action,"entity":entity,"id":str(entity_id),"details":json.dumps(details or {},default=str)})
