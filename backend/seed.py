"""
Script para poblar la base de datos con datos de prueba.
Ejecutar una sola vez después de levantar el servidor por primera vez.
Uso: python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app import models
from app.auth import get_password_hash

Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    try:
        # ── Crear usuarios de prueba ──────────────────────────────────────────
        users_data = [
            {"username": "admin", "full_name": "Administrador MDM", "email": "admin@holcim.com",
             "password": "admin123", "role": models.RoleEnum.admin},
            {"username": "editor1", "full_name": "María García (Datos Maestros)", "email": "mgarcia@holcim.com",
             "password": "editor123", "role": models.RoleEnum.editor},
            {"username": "viewer1", "full_name": "Carlos Restrepo (Compras)", "email": "crestrepo@holcim.com",
             "password": "viewer123", "role": models.RoleEnum.viewer},
            {"username": "viewer2", "full_name": "Ana López (Finanzas)", "email": "alopez@holcim.com",
             "password": "viewer123", "role": models.RoleEnum.viewer},
        ]

        created_users = {}
        for u in users_data:
            existing = db.query(models.User).filter(models.User.username == u["username"]).first()
            if not existing:
                user = models.User(
                    username=u["username"],
                    full_name=u["full_name"],
                    email=u["email"],
                    role=u["role"],
                    hashed_password=get_password_hash(u["password"])
                )
                db.add(user)
                db.flush()
                created_users[u["username"]] = user
                print(f"  ✅ Usuario creado: {u['username']} [{u['role']}]")
            else:
                created_users[u["username"]] = existing
                print(f"  ⏭️  Usuario ya existe: {u['username']}")

        db.commit()
        admin_id = created_users["admin"].id

        # ── Crear proveedores de prueba ───────────────────────────────────────
        suppliers_data = [
            {"business_name": "Cementos Argos S.A.", "nit": "890903793-8",
             "country": "Colombia", "city": "Medellín", "category": models.SupplierCategory.goods,
             "status": models.SupplierStatus.active, "contact_name": "Juan Pérez",
             "contact_email": "jperez@argos.com", "contact_phone": "3001234567",
             "address": "Cra 43A # 1-50, Medellín"},
            {"business_name": "Holcim Trading México S.A. de C.V.", "nit": "HTM900101ABC",
             "country": "México", "city": "Ciudad de México", "category": models.SupplierCategory.goods,
             "status": models.SupplierStatus.active, "contact_name": "Luis Hernández",
             "contact_email": "lhernandez@holcim.mx"},
            {"business_name": "Transportes Rápidos del Valle Ltda.", "nit": "804012345-1",
             "country": "Colombia", "city": "Cali", "category": models.SupplierCategory.logistics,
             "status": models.SupplierStatus.active, "contact_name": "Patricia Sánchez",
             "contact_email": "psanchez@transvalle.co", "contact_phone": "3156789012"},
            {"business_name": "Materiales de Construcción INNOVA S.A.S", "nit": "900456789-2",
             "country": "Colombia", "city": "Bogotá", "category": models.SupplierCategory.goods,
             "status": models.SupplierStatus.pending, "contact_name": "Diego Morales",
             "contact_email": "dmorales@innova.co"},
            {"business_name": "Consultores Tech S.A.S.", "nit": "901234567-3",
             "country": "Colombia", "city": "Bogotá", "category": models.SupplierCategory.services,
             "status": models.SupplierStatus.active, "contact_name": "Sofía Castro",
             "contact_email": "scastro@consultorestech.co", "contact_phone": "3009876543"},
            {"business_name": "Mantenimiento Industrial del Norte", "nit": "800987654-5",
             "country": "Colombia", "city": "Barranquilla", "category": models.SupplierCategory.services,
             "status": models.SupplierStatus.inactive, "contact_name": "Roberto Gómez",
             "contact_email": "rgomez@minorte.co"},
            {"business_name": "Agregados y Áridos del Pacífico", "nit": "805432100-7",
             "country": "Colombia", "city": "Buenaventura", "category": models.SupplierCategory.goods,
             "status": models.SupplierStatus.active, "contact_name": "Claudia Vargas",
             "contact_email": "cvargas@aapac.co"},
            {"business_name": "Servicios Ambientales Colombia S.A.", "nit": "830000111-9",
             "country": "Colombia", "city": "Bogotá", "category": models.SupplierCategory.services,
             "status": models.SupplierStatus.active, "contact_name": "Felipe Rojas",
             "contact_email": "frojas@sacol.com"},
            {"business_name": "Supply Chain Global Ltda.", "nit": "SCG202400001",
             "country": "Brasil", "city": "São Paulo", "category": models.SupplierCategory.mixed,
             "status": models.SupplierStatus.pending, "contact_name": "Ana Ferreira",
             "contact_email": "aferreira@scglobal.com.br"},
            {"business_name": "Lubricantes y Repuestos Andinos S.A.", "nit": "900111222-4",
             "country": "Colombia", "city": "Manizales", "category": models.SupplierCategory.goods,
             "status": models.SupplierStatus.active, "contact_name": "Tomás Ríos",
             "contact_email": "trios@lubandinos.co", "contact_phone": "3044567890"},
        ]

        created_count = 0
        for s in suppliers_data:
            existing = db.query(models.Supplier).filter(models.Supplier.nit == s["nit"]).first()
            if not existing:
                supplier = models.Supplier(**s, created_by=admin_id)
                db.add(supplier)
                created_count += 1
                print(f"  ✅ Proveedor: {s['business_name']}")
            else:
                print(f"  ⏭️  Ya existe: {s['business_name']}")

        db.commit()

        # ── Crear algunos audit logs de prueba ───────────────────────────────
        count = db.query(models.AuditLog).count()
        if count == 0:
            supplier_1 = db.query(models.Supplier).first()
            if supplier_1:
                logs = [
                    models.AuditLog(user_id=admin_id, supplier_id=supplier_1.id,
                                    action="CREATE", entity="Supplier",
                                    description=f"Proveedor '{supplier_1.business_name}' creado en migración inicial",
                                    new_value=supplier_1.business_name),
                    models.AuditLog(user_id=admin_id, supplier_id=supplier_1.id,
                                    action="UPDATE", entity="Supplier",
                                    field_changed="status", old_value="Pendiente", new_value="Activo",
                                    description="Estado actualizado a Activo tras validación"),
                ]
                db.add_all(logs)
                db.commit()
                print("  ✅ Audit logs de ejemplo creados")

        print("\n🎉 Seed completado exitosamente!")
        print("\n📋 Usuarios creados:")
        print("   admin / admin123     → Rol: Administrador")
        print("   editor1 / editor123  → Rol: Editor")
        print("   viewer1 / viewer123  → Rol: Solo lectura")
        print("   viewer2 / viewer123  → Rol: Solo lectura")
        print(f"\n📦 Proveedores creados: {created_count}")

    except Exception as e:
        print(f"❌ Error en seed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Iniciando seed de la base de datos...")
    seed()
