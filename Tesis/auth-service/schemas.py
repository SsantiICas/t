import re

from pydantic import BaseModel, field_validator

from models import ROLES_VALIDOS

# Regla de contraseña exigida:
#   - Mínimo 8 caracteres
#   - Al menos una letra
#   - Al menos una letra mayúscula
#   - Al menos un carácter especial (símbolo)
PATRON_LETRA = re.compile(r"[A-Za-z]")
PATRON_MAYUSCULA = re.compile(r"[A-Z]")
PATRON_ESPECIAL = re.compile(r"[^A-Za-z0-9]")


def validar_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if not PATRON_LETRA.search(password):
        raise ValueError("La contraseña debe contener al menos una letra")
    if not PATRON_MAYUSCULA.search(password):
        raise ValueError("La contraseña debe contener al menos una letra mayúscula")
    if not PATRON_ESPECIAL.search(password):
        raise ValueError("La contraseña debe contener al menos un carácter especial")
    return password


class UserCreate(BaseModel):
    username: str
    password: str
    rol: str = "usuario"

    @field_validator("password")
    @classmethod
    def _validar_password(cls, value: str) -> str:
        return validar_password(value)

    @field_validator("rol")
    @classmethod
    def _validar_rol(cls, value: str) -> str:
        rol = (value or "usuario").lower().strip()
        if rol not in ROLES_VALIDOS:
            raise ValueError(f"Rol inválido. Use uno de: {', '.join(ROLES_VALIDOS)}")
        return rol


class UserLogin(BaseModel):
    username: str
    password: str


class UsuarioUpdate(BaseModel):
    """Actualización de un usuario existente desde el Panel de Administración.
    La contraseña es opcional: si se deja vacía, no se modifica."""
    username: str
    password: str | None = None
    rol: str

    @field_validator("password")
    @classmethod
    def _validar_password_opcional(cls, value: str | None) -> str | None:
        if value:
            return validar_password(value)
        return value

    @field_validator("rol")
    @classmethod
    def _validar_rol(cls, value: str) -> str:
        rol = (value or "usuario").lower().strip()
        if rol not in ROLES_VALIDOS:
            raise ValueError(f"Rol inválido. Use uno de: {', '.join(ROLES_VALIDOS)}")
        return rol
