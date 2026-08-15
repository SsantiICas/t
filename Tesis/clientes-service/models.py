from sqlalchemy import Column, Integer, String, Boolean
from database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)          # Nombre o Razón Social
    cedula_rif = Column(String, index=True)          # Cédula o RIF
    telefono = Column(String)
    email = Column(String)
    activo = Column(Boolean, default=True, nullable=False)
