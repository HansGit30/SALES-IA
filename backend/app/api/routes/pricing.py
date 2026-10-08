from decimal import Decimal
from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from sqlalchemy import text
from app.core.dependencies import DbSession,get_current_user,require_roles
from app.services.audit import record_audit
router=APIRouter(prefix="/pricing",tags=["Reglas comerciales"])
class PricingRules(BaseModel):
    default_tax_percent:Decimal=Field(ge=0,le=100,max_digits=5,decimal_places=2)
    default_discount_percent:Decimal=Field(ge=0,le=100,max_digits=5,decimal_places=2)
    allow_pricing_override:bool

@router.get("")
def get_rules(db:DbSession,user:dict=Depends(get_current_user)):
    return dict(db.execute(text("SELECT default_tax_percent,default_discount_percent,allow_pricing_override FROM companies WHERE id=:id"),{"id":user["company_id"]}).mappings().one())

@router.put("")
def save_rules(payload:PricingRules,db:DbSession,user:dict=Depends(require_roles("admin"))):
    try:
        before=db.execute(text("SELECT default_tax_percent,default_discount_percent,allow_pricing_override FROM companies WHERE id=:id FOR UPDATE"),{"id":user["company_id"]}).mappings().one()
        db.execute(text("UPDATE companies SET default_tax_percent=:default_tax_percent,default_discount_percent=:default_discount_percent,allow_pricing_override=:allow_pricing_override WHERE id=:id"),{**payload.model_dump(),"id":user["company_id"]})
        record_audit(db,user,"pricing.updated","company",user["company_id"],{"before":dict(before),"after":payload.model_dump()})
        db.commit()
        return payload
    except Exception:
        db.rollback()
        raise
