from pydantic import BaseModel, EmailStr


class ClienteBase(BaseModel):
    nombre: str            # Nombre o Razón Social
    cedula_rif: str        # Cédula o RIF
    telefono: str
    email: EmailStr


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ClienteBase):
    pass


class ClienteEstadoUpdate(BaseModel):
    activo: bool


class ClienteResponse(ClienteBase):
    id: int
    activo: bool

    class Config:
        from_attributes = True
