from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SaleLineCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)
    tax_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)


class PaymentCreate(BaseModel):
    method: str = Field(min_length=1, max_length=40)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class SaleCreate(BaseModel):
    branch_id: int | None = Field(default=None, gt=0)
    customer_id: int | None = Field(default=None, gt=0)
    items: list[SaleLineCreate] = Field(min_length=1, max_length=100)
    payments: list[PaymentCreate] = Field(min_length=1, max_length=20)

    @field_validator("items")
    @classmethod
    def unique_products(cls, items):
        ids = [item.product_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada producto debe aparecer una sola vez; combina sus cantidades")
        return items


class SaleVoid(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    reason: str = Field(min_length=3, max_length=1000)


class SaleCancellation(SaleVoid):
    refund_confirmed: Literal[True]
    restock_confirmed: Literal[True]
