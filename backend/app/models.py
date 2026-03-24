from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.viewer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    audit_logs = relationship("AuditLog", back_populates="user")


class SupplierStatus(str, enum.Enum):
    active = "Activo"
    inactive = "Inactivo"
    pending = "Pendiente"


class SupplierCategory(str, enum.Enum):
    goods = "Bienes"
    services = "Servicios"
    mixed = "Mixto"
    logistics = "Logística"


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(200), nullable=False, index=True)
    nit = Column(String(20), unique=True, nullable=False, index=True)
    country = Column(String(50), nullable=False, default="Colombia")
    city = Column(String(100))
    category = Column(Enum(SupplierCategory), nullable=False)
    status = Column(Enum(SupplierStatus), default=SupplierStatus.pending, nullable=False)
    contact_name = Column(String(100))
    contact_email = Column(String(100))
    contact_phone = Column(String(20))
    address = Column(String(250))
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    audit_logs = relationship("AuditLog", back_populates="supplier")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    action = Column(String(20), nullable=False)  # CREATE, UPDATE, DELETE
    entity = Column(String(50), nullable=False)  # 'Supplier'
    field_changed = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    description = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")
    supplier = relationship("Supplier", back_populates="audit_logs")
