from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models import RoleEnum, SupplierStatus, SupplierCategory


# ─── Auth Schemas ────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    username: str
    full_name: str
    email: str
    role: RoleEnum


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Supplier Schemas ─────────────────────────────────────────────────────────

class SupplierBase(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=200)
    nit: str = Field(..., min_length=5, max_length=20)
    country: str = Field(default="Colombia", max_length=50)
    city: Optional[str] = Field(None, max_length=100)
    category: SupplierCategory
    status: SupplierStatus = SupplierStatus.pending
    contact_name: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=250)
    notes: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    business_name: Optional[str] = Field(None, min_length=2, max_length=200)
    country: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=100)
    category: Optional[SupplierCategory] = None
    status: Optional[SupplierStatus] = None
    contact_name: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=250)
    notes: Optional[str] = None


class SupplierOut(SupplierBase):
    id: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SupplierListResponse(BaseModel):
    total: int
    items: list[SupplierOut]


# ─── AuditLog Schemas ─────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    action: str
    entity: str
    field_changed: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    description: Optional[str]
    timestamp: datetime
    user_id: int
    supplier_id: Optional[int]
    username: Optional[str] = None
    supplier_name: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    total: int
    items: list[AuditLogOut]
