import json
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy import text
from app.core.dependencies import DbSession, require_roles

router = APIRouter(prefix="/branches", tags=["Sucursales"])


class BranchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    address: str = Field(min_length=3, max_length=300)
    city: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    manager_name: str | None = Field(default=None, max_length=160)
    manager_email: EmailStr | None = None
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, decimal_places=6)
    is_active: bool = True

    @model_validator(mode="after")
    def coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Indica ambas coordenadas o deja ambas vacías")
        return self


@router.get("")
def list_branches(db: DbSession, user: dict = Depends(require_roles("manager","seller","analyst","warehouse"))):
    return [dict(row) for row in db.execute(text("SELECT * FROM branches WHERE company_id=:company ORDER BY name,id"),
                                           {"company": user["company_id"]}).mappings().all()]


@router.get("/{branch_id}/summary")
def branch_summary(branch_id:int,db:DbSession,user:dict=Depends(require_roles("manager","analyst","warehouse","seller"))):
    params={"company":user["company_id"],"branch":branch_id}
    if db.execute(text("SELECT id FROM branches WHERE company_id=:company AND id=:branch"),params).scalar_one_or_none() is None:
        raise HTTPException(404,detail="La sucursal no existe en esta empresa")
    stock=db.execute(text("SELECT COALESCE(SUM(quantity),0) AS units,COUNT(*) FILTER (WHERE quantity>0) AS products FROM branch_inventory WHERE company_id=:company AND branch_id=:branch"),params).mappings().one()
    staff=db.execute(text("SELECT COUNT(*) FROM employees WHERE company_id=:company AND branch_id=:branch AND is_active=TRUE"),params).scalar_one()
    sales=[]
    if user["role"] in {"admin","manager","analyst"}:
        sales=[dict(r) for r in db.execute(text("SELECT currency,COUNT(*) AS transactions,COALESCE(SUM(total),0) AS revenue FROM sales WHERE company_id=:company AND branch_id=:branch AND status='confirmed' GROUP BY currency ORDER BY currency"),params).mappings()]
    return {"staff":staff,"units":stock["units"],"products":stock["products"],"sales":sales,"sales_visible":user["role"] in {"admin","manager","analyst"}}


def save_branch(db, user, payload, branch_id=None):
    values = {**payload.model_dump(), "company": user["company_id"]}
    values["code"] = values["code"].upper()
    try:
        before = None
        if branch_id is not None:
            before = db.execute(text("SELECT * FROM branches WHERE company_id=:company AND id=:id FOR UPDATE"),
                                {"company":user["company_id"],"id":branch_id}).mappings().first()
            if before is None:
                raise HTTPException(404, detail="La sucursal no existe en esta empresa")
            row = db.execute(text("""UPDATE branches SET code=:code,name=:name,address=:address,city=:city,
                phone=:phone,manager_name=:manager_name,manager_email=:manager_email,latitude=:latitude,longitude=:longitude,is_active=:is_active
                WHERE company_id=:company AND id=:id RETURNING *"""),{**values,"id":branch_id}).mappings().one()
        else:
            row = db.execute(text("""INSERT INTO branches(company_id,code,name,address,city,phone,manager_name,manager_email,latitude,longitude,is_active)
                VALUES (:company,:code,:name,:address,:city,:phone,:manager_name,:manager_email,:latitude,:longitude,:is_active) RETURNING *"""),values).mappings().one()
        changes={key:{"before":before[key] if before else None,"after":row[key]} for key in type(payload).model_fields if before is None or before[key]!=row[key]}
        db.execute(text("""INSERT INTO audit_logs(company_id,user_id,action,entity_type,entity_id,details)
            VALUES (:company,:user,:action,'branch',:id,CAST(:details AS jsonb))"""),
            {"company":user["company_id"],"user":user["id"],"action":"branch.updated" if before else "branch.created",
             "id":str(row["id"]),"details":json.dumps(changes,default=str)})
        db.commit()
        return dict(row)
    except Exception:
        db.rollback()
        raise


@router.post("",status_code=201)
def create_branch(payload:BranchInput,db:DbSession,user:dict=Depends(require_roles("admin"))):
    return save_branch(db,user,payload)


@router.put("/{branch_id}")
def update_branch(branch_id:int,payload:BranchInput,db:DbSession,user:dict=Depends(require_roles("admin"))):
    return save_branch(db,user,payload,branch_id)
