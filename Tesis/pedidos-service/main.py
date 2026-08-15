from fastapi import FastAPI
from sqlalchemy import inspect, text
from database import Base, engine
from routes import pedidos

app = FastAPI(title="SmartLogistic - Servicio de Pedidos")


def migrar_columnas_faltantes():
    """Agrega columnas nuevas a bases de datos ya existentes (SQLite no soporta
    migraciones automáticas de esquema al usar create_all)."""
    inspector = inspect(engine)
    if "pedidos" not in inspector.get_table_names():
        return

    columnas = {col["name"] for col in inspector.get_columns("pedidos")}
    with engine.begin() as conexion:
        if "grupo_pedido" not in columnas:
            conexion.execute(text("ALTER TABLE pedidos ADD COLUMN grupo_pedido VARCHAR"))


Base.metadata.create_all(bind=engine)
migrar_columnas_faltantes()

app.include_router(pedidos.router)
