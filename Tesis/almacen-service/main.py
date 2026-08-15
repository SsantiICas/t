from fastapi import FastAPI
from sqlalchemy import inspect, text
from database import Base, engine
from routes import almacen

app = FastAPI(title="SmartLogistic - Servicio de Almacén")


def migrar_columnas_faltantes():
    """Agrega columnas nuevas a bases de datos ya existentes (SQLite no soporta
    migraciones automáticas de esquema al usar create_all)."""
    inspector = inspect(engine)
    if "productos" not in inspector.get_table_names():
        return

    columnas = {col["name"] for col in inspector.get_columns("productos")}
    with engine.begin() as conexion:
        if "categoria" not in columnas:
            conexion.execute(text("ALTER TABLE productos ADD COLUMN categoria VARCHAR DEFAULT 'General'"))
        if "activo" not in columnas:
            conexion.execute(text("ALTER TABLE productos ADD COLUMN activo BOOLEAN DEFAULT 1"))


Base.metadata.create_all(bind=engine)
migrar_columnas_faltantes()

app.include_router(almacen.router)
