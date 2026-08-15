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


def compactar_ids_productos(db: Session):
    """Reordena todos los IDs de productos de forma consecutiva y devuelve el mapeo anterior -> nuevo."""
    productos = db.query(models.Producto).order_by(models.Producto.id).all()
    id_mapping = {producto.id: index + 1 for index, producto in enumerate(productos)}

    for old_id in id_mapping.keys():
        db.execute(text("UPDATE productos SET id = :temp_id WHERE id = :old_id"), {
            "temp_id": -old_id,
            "old_id": old_id,
        })

    db.flush()

    for old_id, new_id in id_mapping.items():
        db.execute(text("UPDATE productos SET id = :new_id WHERE id = :temp_id"), {
            "new_id": new_id,
            "temp_id": -old_id,
        })

    db.commit()
    return id_mapping


@router.post("/productos", response_model=schemas.ProductoResponse)
def crear_producto(
    producto: schemas.ProductoCreate,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("gerente")),
):
    nuevo = models.Producto(**producto.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("/productos", response_model=list[schemas.ProductoResponse])
def listar_productos(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    # Consulta única (sin N+1): todo el inventario se trae en una sola query ordenada por índice.
    return db.query(models.Producto).order_by(models.Producto.id).all()


@router.get("/productos/{producto_id}", response_model=schemas.ProductoResponse)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.put("/productos/{producto_id}")
def actualizar_producto(
    producto_id: int,
    datos: schemas.ProductoUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("gerente")),
):
    """Actualiza los datos generales del producto (nombre y categoría).
    El stock se gestiona de forma independiente mediante /stock, /reducir y /aumentar."""
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.nombre = datos.nombre
    producto.categoria = datos.categoria
    db.commit()
    db.refresh(producto)
    return {"mensaje": "Producto actualizado", "producto": producto}


@router.patch("/productos/{producto_id}/estado")
def cambiar_estado_producto(
    producto_id: int,
    datos: schemas.ProductoEstadoUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("gerente")),
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.activo = datos.activo
    db.commit()
    db.refresh(producto)
    return {"mensaje": "Estado actualizado", "producto": producto}


@router.put("/productos/{producto_id}/stock")
def actualizar_stock(
    producto_id: int,
    stock: int,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("gerente")),
):
    if stock < 0:
        raise HTTPException(status_code=400, detail="El stock no puede ser negativo")

    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.stock = stock
    db.commit()
    db.refresh(producto)
    return {"mensaje": "Stock actualizado", "producto": producto}


@router.put("/productos/{producto_id}/reducir")
def reducir_stock(producto_id: int, cantidad: int, db: Session = Depends(get_db)):
    """Descuenta stock del inventario. Lo invoca pedidos-service al procesar un pedido."""
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if producto.stock < cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    producto.stock -= cantidad
    db.commit()
    return {"mensaje": "Stock actualizado", "stock_actual": producto.stock}


@router.put("/productos/{producto_id}/aumentar")
def aumentar_stock(producto_id: int, cantidad: int, db: Session = Depends(get_db)):
    """Reingresa stock al inventario general. Lo invoca pedidos-service cuando se
    procesa la devolución de un pedido, sumando de nuevo la cantidad devuelta."""
    if cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad a reingresar debe ser mayor a 0")

    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.stock += cantidad
    db.commit()
    db.refresh(producto)
    return {"mensaje": "Stock reingresado por devolución", "stock_actual": producto.stock}


@router.delete("/productos/{producto_id}")
def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(requiere_rol("administrador")),
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    db.delete(producto)
    db.commit()
    id_mapping = compactar_ids_productos(db)

    return {
        "mensaje": "Producto eliminado",
        "producto_id_eliminado": producto_id,
        "id_mapping": id_mapping,
    }
