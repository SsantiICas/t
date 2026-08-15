from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from sqlalchemy import inspect, text
from database import Base, SessionLocal, engine
from routes import auth_routes
import models

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def migrar_columnas_faltantes():
    """Agrega columnas nuevas a bases de datos ya existentes (SQLite no soporta
    migraciones automáticas de esquema al usar create_all)."""
    inspector = inspect(engine)
    if "usuarios" not in inspector.get_table_names():
        return

    columnas = {col["name"] for col in inspector.get_columns("usuarios")}
    with engine.begin() as conexion:
        if "rol" not in columnas:
            conexion.execute(text("ALTER TABLE usuarios ADD COLUMN rol VARCHAR DEFAULT 'usuario'"))


def crear_usuario_demo():
    """Crea el único usuario administrador inicial del sistema: Santiago."""
    db = SessionLocal()
    try:
        usuario_existente = db.query(models.Usuario).filter(models.Usuario.username == "Santiago").first()
        if not usuario_existente:
            nuevo = models.Usuario(
                username="Santiago",
                password=auth_routes.pwd_context.hash("Ss010305+"),
                rol="administrador",
            )
            db.add(nuevo)
            db.commit()
        elif not usuario_existente.rol:
            usuario_existente.rol = "administrador"
            db.commit()
    finally:
        db.close()


Base.metadata.create_all(bind=engine)
migrar_columnas_faltantes()
crear_usuario_demo()

app.include_router(auth_routes.router)