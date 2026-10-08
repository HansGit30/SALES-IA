from fastapi import HTTPException
from sqlalchemy import text

def check_branch(db,company_id,branch_id):
    if branch_id is not None and db.execute(text("SELECT id FROM branches WHERE company_id=:c AND id=:b AND is_active=TRUE FOR SHARE"),
            {"c":company_id,"b":branch_id}).first() is None:
        raise HTTPException(422,detail="La sucursal no existe o está inactiva")

def stock_target(branch_id):
    return ("inventory","") if branch_id is None else ("branch_inventory"," AND branch_id=:branch_id")
