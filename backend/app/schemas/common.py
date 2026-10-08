from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    company_id: int = Field(gt=0)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class CustomerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=180)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    is_active: bool


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    sku: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    category_id: int | None = Field(default=None, gt=0)


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    description: str | None = None
    unit_price: Decimal
    is_active: bool


class CustomerUpdate(CustomerCreate):
    is_active: bool


class ProductUpdate(ProductCreate):
    is_active: bool
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=200)
    role: str = Field(pattern="^(admin|manager|seller|analyst|warehouse)$")
