from sqlalchemy import Column, Integer, String, Boolean
from database import Base


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    categoria = Column(String, index=True, default="General")
    stock = Column(Integer, default=0)
    activo = Column(Boolean, default=True, nullable=False)
