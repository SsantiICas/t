from sqlalchemy import Column, Integer, String
from database import Base


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer)
    producto_id = Column(Integer)
    cantidad = Column(Integer)
    estado = Column(String)
    # Agrupa varias líneas de producto que pertenecen a una misma orden de un
    # cliente (una orden puede incluir más de un producto). Cada línea sigue
    # llevando su propio estado (pendiente/completado/rechazado/devuelto) de
    # forma independiente, ya que un cliente puede devolver un producto de la
    # orden sin afectar a los demás.
    grupo_pedido = Column(String, index=True, nullable=True)
