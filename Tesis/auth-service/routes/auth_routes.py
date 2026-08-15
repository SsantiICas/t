from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
import models, schemas
from passlib.context import CryptContext
from auth import crear_token, verificar_token_opcional, requiere_rol

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
def register(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    solicitante: dict = Depends(verificar_token_opcional),
):
    """Registro de usuarios.

    - Sin token (auto-registro público): el rol solicitado se ignora y se
      fuerza a "usuario", para que nadie pueda auto-asignarse un rol elevado.
    - Con token de administrador válido: se respeta el rol solicitado
      (usuario, gerente o administrador). Esta es la vía que usa el
      Panel de Administración para crear cuentas con rol específico.
    """
    existente = db.query(models.Usuario).filter(models.Usuario.username == user.username).first()
    if existente:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")

    rol_final = "usuario"
    if solicitante and (solicitante.get("rol") or "").lower() == "administrador":
        rol_final = user.rol

    hashed = pwd_context.hash(user.password)
    nuevo = models.Usuario(username=user.username, password=hashed, rol=rol_final)
    db.add(nuevo)
    db.commit()
    return {"mensaje": "Usuario creado", "username": nuevo.username, "rol": nuevo.rol}


@router.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.Usuario).filter(models.Usuario.username == user.username).first()

    if not db_user or not pwd_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = crear_token({"sub": user.username, "rol": db_user.rol})

    return {"access_token": token, "rol": db_user.rol, "username": db_user.username}


@router.get("/usuarios")
def listar_usuarios(db: Session = Depends(get_db), admin=Depends(requiere_rol("administrador"))):
    """Lista los usuarios del sistema (solo administrador). Usado por el Panel de Administración."""
    usuarios = db.query(models.Usuario).order_by(models.Usuario.id).all()
    return [{"id": u.id, "username": u.username, "rol": u.rol} for u in usuarios]


@router.put("/usuarios/{usuario_id}")
def actualizar_usuario(
    usuario_id: int,
    datos: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    admin=Depends(requiere_rol("administrador")),
):
    """Actualiza nombre de usuario, rol y (opcionalmente) contraseña. Solo administrador."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if datos.username != usuario.username:
        existente = db.query(models.Usuario).filter(models.Usuario.username == datos.username).first()
        if existente:
            raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")

    usuario.username = datos.username
    usuario.rol = datos.rol
    if datos.password:
        usuario.password = pwd_context.hash(datos.password)

    db.commit()
    db.refresh(usuario)
    return {"mensaje": "Usuario actualizado", "id": usuario.id, "username": usuario.username, "rol": usuario.rol}
