from sqlalchemy import Column, Integer, String
from database import Base

# Roles jerárquicos soportados por el sistema (de mayor a menor privilegio).
ROLES_VALIDOS = ["administrador", "gerente", "usuario"]


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    rol = Column(String, default="usuario", nullable=False)