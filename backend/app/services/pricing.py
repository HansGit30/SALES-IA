from sqlalchemy import text
from fastapi import HTTPException

def load_rules(db,company):
    return db.execute(text("SELECT default_discount_percent,default_tax_percent,allow_pricing_override FROM companies WHERE id=:company FOR SHARE"),{"company":company}).mappings().one()

def line_rates(item,rules):
    discount=item.discount_percent if "discount_percent" in item.model_fields_set else rules["default_discount_percent"]
    tax=item.tax_percent if "tax_percent" in item.model_fields_set else rules["default_tax_percent"]
    if not rules["allow_pricing_override"] and (discount!=rules["default_discount_percent"] or tax!=rules["default_tax_percent"]):
        raise HTTPException(409,detail="Las reglas comerciales cambiaron o no permiten porcentajes personalizados. Actualiza el formulario o crea un pedido nuevo.")
    return discount,tax
