from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError

SECRET_KEY = "clave_super_secreta"
ALGORITHM = "HS256"

# Jerarquía de roles: a mayor número, mayor privilegio.
JERARQUIA_ROLES = {"usuario": 1, "gerente": 2, "administrador": 3}


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
    """Dependencia de FastAPI que exige un rol con privilegio >= rol_minimo.

    Jerarquía: administrador > gerente > usuario.
    """

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
