from typing import List, Optional

from pydantic import BaseModel, field_validator


class PedidoCreate(BaseModel):
    cliente_id: int
    producto_id: int
    cantidad: int
    estado: str


class PedidoResponse(PedidoCreate):
    id: int
    grupo_pedido: Optional[str] = None

    class Config:
        from_attributes = True


class ItemOrden(BaseModel):
    """Una línea de producto dentro de una orden (una orden puede tener varias)."""
    producto_id: int
    cantidad: int

    @field_validator("cantidad")
    @classmethod
    def _cantidad_positiva(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        return value


class OrdenCreate(BaseModel):
    """Permite registrar en una sola orden varios productos para un mismo cliente."""
    cliente_id: int
    items: List[ItemOrden]

    @field_validator("items")
    @classmethod
    def _al_menos_un_item(cls, value: List[ItemOrden]) -> List[ItemOrden]:
        if not value:
            raise ValueError("La orden debe incluir al menos un producto")
        return value
