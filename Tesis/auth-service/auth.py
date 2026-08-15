from datetime import datetime, timedelta

from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError

SECRET_KEY = "clave_super_secreta"
ALGORITHM = "HS256"

# Jerarquía de roles: a mayor número, mayor privilegio.
JERARQUIA_ROLES = {"usuario": 1, "gerente": 2, "administrador": 3}


def crear_token(data: dict):
    data_copy = data.copy()
    expire = datetime.utcnow() + timedelta(hours=2)
    data_copy.update({"exp": expire})
    token = jwt.encode(data_copy, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verificar_token_opcional(authorization: str = Header(default="")):
    """Igual que verificar_token, pero no falla si no hay header: retorna None.
    Se usa en /register para permitir auto-registro público (rol usuario) y,
    si viene un token de administrador válido, permitir asignar otro rol."""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ")[1]
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def verificar_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Token inválido")

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


def requiere_rol(rol_minimo: str):
    def dependencia(payload: dict = Depends(verificar_token)):
        rol_usuario = (payload.get("rol") or "usuario").lower()
        nivel_usuario = JERARQUIA_ROLES.get(rol_usuario, 0)
        nivel_requerido = JERARQUIA_ROLES.get(rol_minimo, 99)

        if nivel_usuario < nivel_requerido:
            raise HTTPException(
                status_code=403,
                detail=f"Requiere rol '{rol_minimo}' o superior",
            )
        return payload

    return dependencia
