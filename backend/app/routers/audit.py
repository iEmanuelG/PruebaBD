from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Log"])


@router.get("", response_model=schemas.AuditLogListResponse)
def list_audit_logs(
    action: Optional[str] = Query(None, description="CREATE, UPDATE o DELETE"),
    supplier_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.AuditLog)

    if action:
        query = query.filter(models.AuditLog.action == action.upper())
    if supplier_id:
        query = query.filter(models.AuditLog.supplier_id == supplier_id)

    total = query.count()
    logs = query.order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

    # Enriquecer con datos de usuario y proveedor
    result = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "action": log.action,
            "entity": log.entity,
            "field_changed": log.field_changed,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "description": log.description,
            "timestamp": log.timestamp,
            "user_id": log.user_id,
            "supplier_id": log.supplier_id,
            "username": log.user.full_name if log.user else None,
            "supplier_name": log.supplier.business_name if log.supplier else None,
        }
        result.append(schemas.AuditLogOut(**log_dict))

    return {"total": total, "items": result}
