from pydantic import BaseModel


class ProductoBase(BaseModel):
    nombre: str
    categoria: str = "General"
    stock: int


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre: str
    categoria: str = "General"


class ProductoEstadoUpdate(BaseModel):
    activo: bool


class ProductoResponse(ProductoBase):
    id: int
    activo: bool

    class Config:
        from_attributes = True
