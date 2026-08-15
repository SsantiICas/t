from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal
import models
import schemas
from auth import verificar_token, requiere_rol

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def compactar_ids_clientes(db: Session):
    """Reordena todos los IDs de clientes de forma consecutiva y devuelve el mapeo anterior -> nuevo."""
    clientes = db.query(models.Cliente).order_by(models.Cliente.id).all()
    id_mapping = {cliente.id: index + 1 for index, cliente in enumerate(clientes)}

    # Primero pasamos IDs a negativo para evitar choques con claves primarias existentes.
    for old_id in id_mapping.keys():
        db.execute(text("UPDATE clientes SET id = :temp_id WHERE id = :old_id"), {
            "temp_id": -old_id,
            "old_id": old_id,
        })

    db.flush()

    # Luego asignamos los IDs definitivos consecutivos.
    for old_id, new_id in id_mapping.items():
        db.execute(text("UPDATE clientes SET id = :new_id WHERE id = :temp_id"), {
            "new_id": new_id,
            "temp_id": -old_id,
        })

    db.commit()
    return id_mapping


@router.post("/clientes", response_model=schemas.ClienteResponse)
def crear_cliente(
    cliente: schemas.ClienteCreate,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("gerente")),
):
    nuevo = models.Cliente(**cliente.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("/clientes", response_model=list[schemas.ClienteResponse])
def listar_clientes(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    # Consulta única (sin N+1): todos los clientes se traen en una sola query ordenada por índice.
    return db.query(models.Cliente).order_by(models.Cliente.id).all()


@router.get("/clientes/{cliente_id}", response_model=schemas.ClienteResponse)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.put("/clientes/{cliente_id}")
def actualizar_cliente(
    cliente_id: int,
    datos: schemas.ClienteUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("gerente")),
):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cliente.nombre = datos.nombre
    cliente.cedula_rif = datos.cedula_rif
    cliente.email = datos.email
    cliente.telefono = datos.telefono
    db.commit()
    db.refresh(cliente)
    return {"mensaje": "Cliente actualizado", "cliente": cliente}


@router.patch("/clientes/{cliente_id}/estado")
def cambiar_estado_cliente(
    cliente_id: int,
    datos: schemas.ClienteEstadoUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("gerente")),
):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cliente.activo = datos.activo
    db.commit()
    db.refresh(cliente)
    return {"mensaje": "Estado actualizado", "cliente": cliente}


@router.delete("/clientes/{cliente_id}")
def eliminar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("administrador")),
):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    db.delete(cliente)
    db.commit()
    id_mapping = compactar_ids_clientes(db)

    return {
        "mensaje": "Cliente eliminado",
        "cliente_id_eliminado": cliente_id,
        "id_mapping": id_mapping,
    }
