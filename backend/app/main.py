from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import logging

from app.database import engine, Base, SessionLocal
from app import models
from app.routers import auth, suppliers, audit

load_dotenv()
logger = logging.getLogger("mdm.startup")

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)


def run_seed_if_empty():
    """Ejecuta el seed de datos iniciales si la BD está vacía."""
    db = SessionLocal()
    try:
        user_count = db.query(models.User).count()
        if user_count == 0:
            logger.info("Base de datos vacía — ejecutando seed inicial...")
            from app.auth import get_password_hash

            users_data = [
                {"username": "admin",   "full_name": "Administrador MDM",          "email": "admin@holcim.com",    "password": "admin123",  "role": models.RoleEnum.admin},
                {"username": "editor1", "full_name": "María García (Datos Maestros)", "email": "mgarcia@holcim.com", "password": "editor123", "role": models.RoleEnum.editor},
                {"username": "viewer1", "full_name": "Carlos Restrepo (Compras)",  "email": "crestrepo@holcim.com","password": "viewer123", "role": models.RoleEnum.viewer},
                {"username": "viewer2", "full_name": "Ana López (Finanzas)",       "email": "alopez@holcim.com",   "password": "viewer123", "role": models.RoleEnum.viewer},
            ]
            created_users = {}
            for u in users_data:
                user = models.User(
                    username=u["username"], full_name=u["full_name"],
                    email=u["email"], role=u["role"],
                    hashed_password=get_password_hash(u["password"])
                )
                db.add(user)
                db.flush()
                created_users[u["username"]] = user

            admin_id = created_users["admin"].id

            suppliers_data = [
                {"business_name": "Cementos Argos S.A.",              "nit": "890903793-8",  "country": "Colombia", "city": "Medellín",        "category": models.SupplierCategory.goods,    "status": models.SupplierStatus.active,   "contact_name": "Juan Pérez",     "contact_email": "jperez@argos.com"},
                {"business_name": "Holcim Trading México S.A. de C.V.", "nit": "HTM900101ABC","country": "México",   "city": "Ciudad de México","category": models.SupplierCategory.goods,    "status": models.SupplierStatus.active,   "contact_name": "Luis Hernández", "contact_email": "lhernandez@holcim.mx"},
                {"business_name": "Transportes Rápidos del Valle Ltda.", "nit": "804012345-1","country": "Colombia", "city": "Cali",            "category": models.SupplierCategory.logistics,"status": models.SupplierStatus.active,   "contact_name": "Patricia Sánchez","contact_email": "psanchez@transvalle.co"},
                {"business_name": "Materiales INNOVA S.A.S",           "nit": "900456789-2", "country": "Colombia", "city": "Bogotá",          "category": models.SupplierCategory.goods,    "status": models.SupplierStatus.pending,  "contact_name": "Diego Morales",  "contact_email": "dmorales@innova.co"},
                {"business_name": "Consultores Tech S.A.S.",           "nit": "901234567-3", "country": "Colombia", "city": "Bogotá",          "category": models.SupplierCategory.services, "status": models.SupplierStatus.active,   "contact_name": "Sofía Castro",   "contact_email": "scastro@tech.co"},
                {"business_name": "Mantenimiento Industrial del Norte", "nit": "800987654-5", "country": "Colombia", "city": "Barranquilla",    "category": models.SupplierCategory.services, "status": models.SupplierStatus.inactive, "contact_name": "Roberto Gómez",  "contact_email": "rgomez@minorte.co"},
                {"business_name": "Agregados y Áridos del Pacífico",   "nit": "805432100-7", "country": "Colombia", "city": "Buenaventura",    "category": models.SupplierCategory.goods,    "status": models.SupplierStatus.active,   "contact_name": "Claudia Vargas", "contact_email": "cvargas@aapac.co"},
                {"business_name": "Servicios Ambientales Colombia S.A.","nit": "830000111-9", "country": "Colombia", "city": "Bogotá",          "category": models.SupplierCategory.services, "status": models.SupplierStatus.active,   "contact_name": "Felipe Rojas",   "contact_email": "frojas@sacol.com"},
                {"business_name": "Supply Chain Global Ltda.",         "nit": "SCG202400001","country": "Brasil",   "city": "São Paulo",       "category": models.SupplierCategory.mixed,    "status": models.SupplierStatus.pending,  "contact_name": "Ana Ferreira",   "contact_email": "aferreira@scglobal.com.br"},
                {"business_name": "Lubricantes y Repuestos Andinos S.A.","nit": "900111222-4","country": "Colombia","city": "Manizales",       "category": models.SupplierCategory.goods,    "status": models.SupplierStatus.active,   "contact_name": "Tomás Ríos",     "contact_email": "trios@lubandinos.co"},
            ]
            for s in suppliers_data:
                supplier = models.Supplier(**s, created_by=admin_id)
                db.add(supplier)
                db.flush()
                db.add(models.AuditLog(
                    user_id=admin_id, supplier_id=supplier.id,
                    action="CREATE", entity="Supplier",
                    description=f"Importado en seed inicial: '{supplier.business_name}'",
                    new_value=supplier.business_name
                ))

            db.commit()
            logger.info("✅ Seed completado: 4 usuarios y 10 proveedores creados.")
    except Exception as e:
        logger.error(f"Error en seed: {e}")
        db.rollback()
    finally:
        db.close()


run_seed_if_empty()

app = FastAPI(
    title=os.getenv("APP_NAME", "Holcim MDM - Datos Maestros"),
    description="Sistema de Gestión de Datos Maestros - Prototipo",
    version="1.0.0",
)

# CORS para desarrollo local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers de la API
app.include_router(auth.router)
app.include_router(suppliers.router)
app.include_router(audit.router)

# Servir el frontend como archivos estáticos
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str = ""):
        # No servir rutas de API como frontend
        if full_path.startswith("api/") or full_path == "docs" or full_path == "openapi.json":
            return {"detail": "Not Found"}
        index_file = os.path.join(static_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend no encontrado. Ejecuta el build del frontend."}


@app.get("/api/health", tags=["Sistema"])
def health_check():
    return {"status": "ok", "app": os.getenv("APP_NAME")}
