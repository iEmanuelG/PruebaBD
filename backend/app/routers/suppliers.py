import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/suppliers", tags=["Proveedores"])


def _log_action(
    db: Session,
    user_id: int,
    supplier_id: int,
    action: str,
    description: str,
    field_changed: str = None,
    old_value: str = None,
    new_value: str = None,
):
    log = models.AuditLog(
        user_id=user_id,
        supplier_id=supplier_id,
        action=action,
        entity="Supplier",
        field_changed=field_changed,
        old_value=old_value,
        new_value=new_value,
        description=description,
    )
    db.add(log)


@router.get("", response_model=schemas.SupplierListResponse)
def list_suppliers(
    search: Optional[str] = Query(None, description="Buscar por nombre o NIT"),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.Supplier)

    if search:
        query = query.filter(
            models.Supplier.business_name.ilike(f"%{search}%") |
            models.Supplier.nit.ilike(f"%{search}%")
        )
    if status:
        query = query.filter(models.Supplier.status == status)
    if category:
        query = query.filter(models.Supplier.category == category)

    total = query.count()
    items = query.order_by(models.Supplier.business_name).offset(skip).limit(limit).all()

    return {"total": total, "items": items}


@router.get("/{supplier_id}", response_model=schemas.SupplierOut)
def get_supplier(
    supplier_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return supplier


@router.post("", response_model=schemas.SupplierOut, status_code=201)
def create_supplier(
    supplier_data: schemas.SupplierCreate,
    current_user: models.User = Depends(require_role(models.RoleEnum.admin, models.RoleEnum.editor)),
    db: Session = Depends(get_db),
):
    existing = db.query(models.Supplier).filter(models.Supplier.nit == supplier_data.nit).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un proveedor con NIT {supplier_data.nit}")

    supplier = models.Supplier(**supplier_data.model_dump(), created_by=current_user.id)
    db.add(supplier)
    db.flush()  # para obtener el id antes del commit

    _log_action(
        db, current_user.id, supplier.id,
        action="CREATE",
        description=f"Proveedor '{supplier.business_name}' (NIT: {supplier.nit}) creado por {current_user.full_name}",
        new_value=supplier.business_name,
    )

    db.commit()
    db.refresh(supplier)
    return supplier


@router.put("/{supplier_id}", response_model=schemas.SupplierOut)
def update_supplier(
    supplier_id: int,
    supplier_data: schemas.SupplierUpdate,
    current_user: models.User = Depends(require_role(models.RoleEnum.admin, models.RoleEnum.editor)),
    db: Session = Depends(get_db),
):
    supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    update_dict = supplier_data.model_dump(exclude_unset=True)
    for field, new_val in update_dict.items():
        old_val = getattr(supplier, field)
        if str(old_val) != str(new_val):
            _log_action(
                db, current_user.id, supplier.id,
                action="UPDATE",
                description=f"Campo '{field}' modificado en proveedor '{supplier.business_name}'",
                field_changed=field,
                old_value=str(old_val) if old_val is not None else None,
                new_value=str(new_val) if new_val is not None else None,
            )
        setattr(supplier, field, new_val)

    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: int,
    current_user: models.User = Depends(require_role(models.RoleEnum.admin)),
    db: Session = Depends(get_db),
):
    supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    _log_action(
        db, current_user.id, supplier.id,
        action="DELETE",
        description=f"Proveedor '{supplier.business_name}' (NIT: {supplier.nit}) eliminado por {current_user.full_name}",
        old_value=supplier.business_name,
    )

    db.delete(supplier)
    db.commit()


@router.post("/import-csv", status_code=201)
def import_suppliers_csv(
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_role(models.RoleEnum.admin, models.RoleEnum.editor)),
    db: Session = Depends(get_db),
):
    """Importar proveedores desde un archivo CSV."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV")

    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    created, skipped, errors = 0, 0, []
    for i, row in enumerate(reader, start=2):
        try:
            nit = row.get("nit", "").strip()
            if not nit:
                errors.append(f"Fila {i}: NIT vacío")
                continue

            existing = db.query(models.Supplier).filter(models.Supplier.nit == nit).first()
            if existing:
                skipped += 1
                continue

            category_str = row.get("category", "Bienes").strip()
            status_str = row.get("status", "Pendiente").strip()

            supplier = models.Supplier(
                business_name=row.get("business_name", "").strip(),
                nit=nit,
                country=row.get("country", "Colombia").strip(),
                city=row.get("city", "").strip() or None,
                category=category_str,
                status=status_str,
                contact_name=row.get("contact_name", "").strip() or None,
                contact_email=row.get("contact_email", "").strip() or None,
                contact_phone=row.get("contact_phone", "").strip() or None,
                address=row.get("address", "").strip() or None,
                created_by=current_user.id,
            )
            db.add(supplier)
            db.flush()
            _log_action(db, current_user.id, supplier.id, "CREATE",
                        f"Importado vía CSV: '{supplier.business_name}'", new_value=supplier.business_name)
            created += 1
        except Exception as e:
            errors.append(f"Fila {i}: {str(e)}")

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}
