from fastapi import FastAPI
from sqlalchemy import inspect, text
from database import Base, engine
from routes import clientes

app = FastAPI(title="SmartLogistic - Servicio de Clientes")


def migrar_columnas_faltantes():
    """Agrega columnas nuevas a bases de datos ya existentes (SQLite no soporta
    migraciones automáticas de esquema al usar create_all)."""
    inspector = inspect(engine)
    if "clientes" not in inspector.get_table_names():
        return

    columnas = {col["name"] for col in inspector.get_columns("clientes")}
    with engine.begin() as conexion:
        if "cedula_rif" not in columnas:
            conexion.execute(text("ALTER TABLE clientes ADD COLUMN cedula_rif VARCHAR DEFAULT ''"))
        if "activo" not in columnas:
            conexion.execute(text("ALTER TABLE clientes ADD COLUMN activo BOOLEAN DEFAULT 1"))


Base.metadata.create_all(bind=engine)
migrar_columnas_faltantes()

app.include_router(clientes.router)
