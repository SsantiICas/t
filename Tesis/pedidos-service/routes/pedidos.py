import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal
import models
import schemas
import requests
from auth import verificar_token, requiere_rol

router = APIRouter()

CLIENTES_URL = "http://127.0.0.1:8000"
ALMACEN_URL = "http://127.0.0.1:8003"

ESTADOS_VALIDOS = ["pendiente", "completado", "rechazado", "devuelto"]

# Estados en los que el stock del pedido YA fue reingresado al almacén (rechazo o
# devolución). Un pedido en cualquier otro estado ("pendiente"/"completado") todavía
# tiene el stock reservado/descontado y por lo tanto sí debe reingresarse si se elimina.
ESTADOS_CON_STOCK_YA_REINGRESADO = {"rechazado", "devuelto"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def compactar_ids_pedidos(db: Session):
    pedidos = db.query(models.Pedido).order_by(models.Pedido.id).all()
    id_mapping = {pedido.id: index + 1 for index, pedido in enumerate(pedidos)}

    for old_id in id_mapping.keys():
        db.execute(text("UPDATE pedidos SET id = :temp_id WHERE id = :old_id"), {
            "temp_id": -old_id,
            "old_id": old_id,
        })

    db.flush()

    for old_id, new_id in id_mapping.items():
        db.execute(text("UPDATE pedidos SET id = :new_id WHERE id = :temp_id"), {
            "new_id": new_id,
            "temp_id": -old_id,
        })

    db.commit()
    return id_mapping


def obtener_productos(headers: dict) -> list:
    """Consulta el catálogo completo de almacen-service reenviando el token del
    usuario (GET /productos exige autenticación) y valida que la respuesta sea
    realmente una lista de productos antes de usarla, para nunca reventar con
    un TypeError si el upstream responde con un error en formato JSON."""
    try:
        res = requests.get(f"{ALMACEN_URL}/productos", headers=headers, timeout=10)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="No fue posible contactar el servicio de almacén")

    if res.status_code != 200:
        detalle = res.json().get("detail") if res.headers.get("content-type", "").startswith("application/json") else res.text
        raise HTTPException(
            status_code=502,
            detail=f"El servicio de almacén respondió con error ({res.status_code}): {detalle}",
        )

    productos = res.json()
    if not isinstance(productos, list):
        raise HTTPException(status_code=502, detail="Respuesta inesperada del servicio de almacén")

    return productos


def aumentar_stock_producto(producto_id: int, cantidad: int, headers: dict):
    """Reingresa stock al almacén (rechazo/devolución/eliminación de pedidos)."""
    aumentar_url = f"{ALMACEN_URL}/productos/{producto_id}/aumentar?cantidad={cantidad}"
    try:
        res = requests.put(aumentar_url, headers=headers, timeout=10)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="No fue posible contactar el servicio de almacén")

    if res.status_code != 200:
        raise HTTPException(status_code=400, detail="No se pudo reingresar el stock al almacén")


@router.post("/pedidos", response_model=schemas.PedidoResponse)
def crear_pedido(
    pedido: schemas.PedidoCreate,
    db: Session = Depends(get_db),
    user=Depends(verificar_token),
    authorization: str = Header(default=""),
):
    """Crea un pedido de un solo producto. Se conserva por compatibilidad;
    para registrar varios productos en una misma orden usar POST /pedidos/orden."""
    headers = {"Authorization": authorization}

    cliente_url = f"{CLIENTES_URL}/clientes/{pedido.cliente_id}"
    cliente_res = requests.get(cliente_url, headers=headers, timeout=10)

    if cliente_res.status_code != 200:
        raise HTTPException(status_code=404, detail="Cliente no existe")

    cliente = cliente_res.json()
    if not cliente.get("activo", True):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede crear el pedido: el cliente '{cliente.get('nombre', '')}' está INACTIVO",
        )

    productos = obtener_productos(headers)
    producto = next((p for p in productos if p["id"] == pedido.producto_id), None)

    if not producto:
        raise HTTPException(status_code=404, detail="Producto no existe")

    if not producto.get("activo", True):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede crear el pedido: el producto '{producto['nombre']}' está INACTIVO",
        )

    if producto["stock"] < pedido.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    reducir_url = f"{ALMACEN_URL}/productos/{pedido.producto_id}/reducir?cantidad={pedido.cantidad}"
    reducir_res = requests.put(reducir_url, headers=headers, timeout=10)

    if reducir_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Error al actualizar stock")

    nuevo = models.Pedido(**pedido.model_dump(), grupo_pedido=uuid.uuid4().hex[:8])
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.post("/pedidos/orden", response_model=list[schemas.PedidoResponse])
def crear_orden(
    orden: schemas.OrdenCreate,
    db: Session = Depends(get_db),
    user=Depends(verificar_token),
    authorization: str = Header(default=""),
):
    """Registra una orden para un cliente con uno o varios productos.

    Validación en dos fases (todo o nada): primero se confirma que el cliente
    exista, esté ACTIVO, y que cada producto solicitado exista, esté ACTIVO y
    tenga stock suficiente (sumando cantidades si el mismo producto aparece
    más de una vez en la orden); solo si todo es válido se descuenta el stock
    de cada producto y se registran las líneas de la orden, todas bajo el
    mismo código de agrupación.
    """
    headers = {"Authorization": authorization}

    cliente_url = f"{CLIENTES_URL}/clientes/{orden.cliente_id}"
    cliente_res = requests.get(cliente_url, headers=headers, timeout=10)
    if cliente_res.status_code != 200:
        raise HTTPException(status_code=404, detail="Cliente no existe")

    cliente = cliente_res.json()
    if not cliente.get("activo", True):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede crear la orden: el cliente '{cliente.get('nombre', '')}' está INACTIVO",
        )

    productos = {p["id"]: p for p in obtener_productos(headers)}

    # Suma cantidades por producto (por si el mismo producto se agregó en más de una línea).
    cantidad_total_por_producto = defaultdict(int)
    for item in orden.items:
        cantidad_total_por_producto[item.producto_id] += item.cantidad

    # Fase 1: validar existencia, estado ACTIVO y stock suficiente de TODOS los
    # productos antes de tocar nada.
    for producto_id, cantidad_requerida in cantidad_total_por_producto.items():
        producto = productos.get(producto_id)
        if not producto:
            raise HTTPException(status_code=404, detail=f"El producto {producto_id} no existe")
        if not producto.get("activo", True):
            raise HTTPException(
                status_code=400,
                detail=f"No se puede crear la orden: el producto '{producto['nombre']}' está INACTIVO",
            )
        if producto["stock"] < cantidad_requerida:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{producto['nombre']}' "
                       f"(disponible: {producto['stock']}, solicitado: {cantidad_requerida})",
            )

    # Fase 2: descontar stock y crear las líneas de la orden, ya validado todo.
    grupo_pedido = uuid.uuid4().hex[:8]
    nuevos_pedidos = []

    for item in orden.items:
        reducir_url = f"{ALMACEN_URL}/productos/{item.producto_id}/reducir?cantidad={item.cantidad}"
        reducir_res = requests.put(reducir_url, headers=headers, timeout=10)
        if reducir_res.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Error al actualizar stock del producto {item.producto_id}",
            )

        nuevo = models.Pedido(
            cliente_id=orden.cliente_id,
            producto_id=item.producto_id,
            cantidad=item.cantidad,
            estado="pendiente",
            grupo_pedido=grupo_pedido,
        )
        db.add(nuevo)
        nuevos_pedidos.append(nuevo)

    db.commit()
    for pedido in nuevos_pedidos:
        db.refresh(pedido)

    return nuevos_pedidos


@router.get("/pedidos")
def listar_pedidos(db: Session = Depends(get_db), user=Depends(verificar_token)):
    return db.query(models.Pedido).order_by(models.Pedido.id).all()


@router.delete("/pedidos/{pedido_id}")
def eliminar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    user=Depends(requiere_rol("administrador")),
    authorization: str = Header(default=""),
):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    # Si el pedido todavía tenía el stock reservado (pendiente/completado), se
    # reingresa al almacén antes de borrar el registro. Si ya estaba
    # rechazado/devuelto, el stock ya fue reingresado en ese momento y no se
    # vuelve a sumar (evita duplicar el reingreso).
    if pedido.estado not in ESTADOS_CON_STOCK_YA_REINGRESADO:
        aumentar_stock_producto(pedido.producto_id, pedido.cantidad, {"Authorization": authorization})

    db.delete(pedido)
    db.commit()
    id_mapping = compactar_ids_pedidos(db)

    return {
        "mensaje": "Pedido eliminado del historial y stock reingresado al almacén",
        "pedido_id_eliminado": pedido_id,
        "id_mapping": id_mapping,
    }


@router.put("/pedidos/{pedido_id}/estado")
def actualizar_estado_pedido(
    pedido_id: int,
    estado: str,
    db: Session = Depends(get_db),
    user=Depends(requiere_rol("gerente")),
    authorization: str = Header(default=""),
):
    estado = estado.lower().strip()
    headers = {"Authorization": authorization}

    if estado not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Estado inválido")

    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if estado == "rechazado":
        # Solo se puede rechazar un pedido que todavía está pendiente.
        if pedido.estado != "pendiente":
            raise HTTPException(
                status_code=400,
                detail="Solo se pueden rechazar pedidos que estén en estado 'pendiente'",
            )
        # Regla de negocio: al rechazar un pedido, el stock reservado se
        # reingresa automáticamente al inventario general (nunca se llegó a entregar).
        aumentar_stock_producto(pedido.producto_id, pedido.cantidad, headers)

    if estado == "devuelto":
        # Solo se puede devolver un pedido que ya fue completado (entregado).
        if pedido.estado != "completado":
            raise HTTPException(
                status_code=400,
                detail="Solo se pueden devolver pedidos que estén en estado 'completado'",
            )
        # Regla de negocio: al procesar la devolución, la cantidad devuelta se
        # recarga y suma automáticamente de nuevo al inventario general.
        aumentar_stock_producto(pedido.producto_id, pedido.cantidad, headers)

    pedido.estado = estado
    db.commit()
    db.refresh(pedido)
    return {"mensaje": "Estado actualizado", "pedido": pedido}


@router.put("/pedidos/remap/cliente")
def remapear_clientes_en_pedidos(payload: dict, db: Session = Depends(get_db)):
    deleted_id = int(payload.get("deleted_id", 0))
    raw_mapping = payload.get("id_mapping", {}) or {}
    mapping = {int(k): int(v) for k, v in raw_mapping.items()}

    pedidos = db.query(models.Pedido).all()
    for pedido in pedidos:
        if pedido.cliente_id == deleted_id:
            pedido.cliente_id = 0
        elif pedido.cliente_id in mapping:
            pedido.cliente_id = mapping[pedido.cliente_id]
    db.commit()
    return {"mensaje": "Referencias de clientes actualizadas"}


@router.put("/pedidos/remap/producto")
def remapear_productos_en_pedidos(payload: dict, db: Session = Depends(get_db)):
    deleted_id = int(payload.get("deleted_id", 0))
    raw_mapping = payload.get("id_mapping", {}) or {}
    mapping = {int(k): int(v) for k, v in raw_mapping.items()}

    pedidos = db.query(models.Pedido).all()
    for pedido in pedidos:
        if pedido.producto_id == deleted_id:
            pedido.producto_id = 0
        elif pedido.producto_id in mapping:
            pedido.producto_id = mapping[pedido.producto_id]
    db.commit()
    return {"mensaje": "Referencias de productos actualizadas"}


# Se conservan estos endpoints por compatibilidad con versiones anteriores del gateway.
@router.put("/pedidos/reindex/cliente/{deleted_id}")
def reindexar_cliente_en_pedidos(deleted_id: int, db: Session = Depends(get_db)):
    pedidos = db.query(models.Pedido).all()
    for pedido in pedidos:
        if pedido.cliente_id == deleted_id:
            pedido.cliente_id = 0
        elif pedido.cliente_id > deleted_id:
            pedido.cliente_id -= 1
    db.commit()
    return {"mensaje": "Referencias de clientes actualizadas"}


@router.put("/pedidos/reindex/producto/{deleted_id}")
def reindexar_producto_en_pedidos(deleted_id: int, db: Session = Depends(get_db)):
    pedidos = db.query(models.Pedido).all()
    for pedido in pedidos:
        if pedido.producto_id == deleted_id:
            pedido.producto_id = 0
        elif pedido.producto_id > deleted_id:
            pedido.producto_id -= 1
    db.commit()
    return {"mensaje": "Referencias de productos actualizadas"}
