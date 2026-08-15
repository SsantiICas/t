from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
import json

app = FastAPI(title="SmartLogistic API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLIENTES_URL = "http://127.0.0.1:8000"
PEDIDOS_URL = "http://127.0.0.1:8001"
ALMACEN_URL = "http://127.0.0.1:8003"
AUTH_URL = "http://127.0.0.1:8004"


def json_response_from_service(res):
    try:
        return JSONResponse(content=res.json(), status_code=res.status_code)
    except Exception:
        return JSONResponse(
            content={
                "error": "El servicio no devolvió una respuesta JSON válida",
                "status_code": getattr(res, "status_code", 502),
                "respuesta": getattr(res, "text", ""),
            },
            status_code=getattr(res, "status_code", 502),
        )


def get_auth_header(request: Request):
    """Return an Authorization header only when present in the incoming request.

    Avoid sending an empty Authorization header to upstream services, which can
    cause unexpected rejections in some setups.
    """
    auth = request.headers.get("Authorization")
    return {"Authorization": auth} if auth else {}


async def get_json_or_empty(request: Request):
    """Safely parse JSON from the request.

    Returns an empty dict when the body is empty or not valid JSON.
    Tries these in order:
      - await request.json()
      - if body empty -> {}
      - try to decode body bytes as JSON
      - try to read form data and return as dict
      - fallback to {}
    """
    try:
        return await request.json()
    except Exception:
        # If body is empty, return empty dict
        body = await request.body()
        if not body:
            return {}
        # Try to decode bytes as JSON
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            # Try form data
            try:
                form = await request.form()
                return dict(form)
            except Exception:
                return {}


def proxy_request(method: str, url: str, request: Request = None, **kwargs):
    headers = kwargs.pop("headers", {}) or {}
    if request is not None:
        headers = {**get_auth_header(request), **headers}

    try:
        res = requests.request(method, url, headers=headers, timeout=10, **kwargs)
    except requests.RequestException as exc:
        return JSONResponse(
            content={"detail": f"No fue posible contactar el servicio upstream: {exc}"},
            status_code=502,
        )

    return json_response_from_service(res)


@app.get("/")
def home():
    return {"mensaje": "SmartLogistic API Gateway activo"}


@app.post("/login")
async def login(request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("POST", f"{AUTH_URL}/login", request=request, json=data)


@app.post("/register")
async def register(request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("POST", f"{AUTH_URL}/register", request=request, json=data)


@app.get("/usuarios")
def get_usuarios(request: Request):
    return proxy_request("GET", f"{AUTH_URL}/usuarios", request=request)


@app.put("/usuarios/{usuario_id}")
async def update_usuario(usuario_id: int, request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("PUT", f"{AUTH_URL}/usuarios/{usuario_id}", request=request, json=data)


@app.get("/clientes")
def get_clientes(request: Request):
    return proxy_request("GET", f"{CLIENTES_URL}/clientes", request=request)


@app.post("/clientes")
async def create_cliente(request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("POST", f"{CLIENTES_URL}/clientes", request=request, json=data)


@app.get("/clientes/{cliente_id}")
def get_cliente(cliente_id: int, request: Request):
    return proxy_request("GET", f"{CLIENTES_URL}/clientes/{cliente_id}", request=request)


@app.put("/clientes/{cliente_id}")
async def update_cliente(cliente_id: int, request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("PUT", f"{CLIENTES_URL}/clientes/{cliente_id}", request=request, json=data)


@app.patch("/clientes/{cliente_id}/estado")
async def update_cliente_estado(cliente_id: int, request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("PATCH", f"{CLIENTES_URL}/clientes/{cliente_id}/estado", request=request, json=data)


@app.delete("/clientes/{cliente_id}")
def delete_cliente(cliente_id: int, request: Request):
    res = requests.delete(f"{CLIENTES_URL}/clientes/{cliente_id}", headers=get_auth_header(request), timeout=10)
    if res.status_code == 200:
        try:
            data = res.json()
            requests.put(
                f"{PEDIDOS_URL}/pedidos/remap/cliente",
                json={
                    "deleted_id": data.get("cliente_id_eliminado", cliente_id),
                    "id_mapping": data.get("id_mapping", {}),
                },
                headers=get_auth_header(request),
                timeout=10,
            )
        except Exception:
            pass
    return json_response_from_service(res)


@app.get("/productos")
def get_productos(request: Request):
    return proxy_request("GET", f"{ALMACEN_URL}/productos", request=request)


@app.post("/productos")
async def create_producto(request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("POST", f"{ALMACEN_URL}/productos", request=request, json=data)


@app.put("/productos/{producto_id}/stock")
async def update_producto_stock(producto_id: int, request: Request):
    data = await get_json_or_empty(request)
    stock = data.get("stock")
    return proxy_request(
        "PUT",
        f"{ALMACEN_URL}/productos/{producto_id}/stock?stock={stock}",
        request=request,
    )


@app.put("/productos/{producto_id}")
async def update_producto(producto_id: int, request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("PUT", f"{ALMACEN_URL}/productos/{producto_id}", request=request, json=data)


@app.patch("/productos/{producto_id}/estado")
async def update_producto_estado(producto_id: int, request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("PATCH", f"{ALMACEN_URL}/productos/{producto_id}/estado", request=request, json=data)


@app.delete("/productos/{producto_id}")
def delete_producto(producto_id: int, request: Request):
    res = requests.delete(f"{ALMACEN_URL}/productos/{producto_id}", headers=get_auth_header(request), timeout=10)
    if res.status_code == 200:
        try:
            data = res.json()
            requests.put(
                f"{PEDIDOS_URL}/pedidos/remap/producto",
                json={
                    "deleted_id": data.get("producto_id_eliminado", producto_id),
                    "id_mapping": data.get("id_mapping", {}),
                },
                headers=get_auth_header(request),
                timeout=10,
            )
        except Exception:
            pass
    return json_response_from_service(res)


@app.get("/pedidos")
def get_pedidos(request: Request):
    return proxy_request("GET", f"{PEDIDOS_URL}/pedidos", request=request)


@app.post("/pedidos")
async def create_pedido(request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("POST", f"{PEDIDOS_URL}/pedidos", request=request, json=data)


@app.post("/pedidos/orden")
async def create_orden(request: Request):
    data = await get_json_or_empty(request)
    return proxy_request("POST", f"{PEDIDOS_URL}/pedidos/orden", request=request, json=data)


@app.put("/pedidos/{pedido_id}/estado")
async def update_pedido_estado(pedido_id: int, request: Request):
    data = await get_json_or_empty(request)
    estado = data.get("estado")
    return proxy_request(
        "PUT",
        f"{PEDIDOS_URL}/pedidos/{pedido_id}/estado?estado={estado}",
        request=request,
    )


@app.delete("/pedidos/{pedido_id}")
def delete_pedido(pedido_id: int, request: Request):
    return proxy_request("DELETE", f"{PEDIDOS_URL}/pedidos/{pedido_id}", request=request)


@app.get("/historial-pedidos")
def historial_pedidos(request: Request):
    pedidos_res = requests.get(f"{PEDIDOS_URL}/pedidos", headers=get_auth_header(request), timeout=10)
    clientes_res = requests.get(f"{CLIENTES_URL}/clientes", headers=get_auth_header(request), timeout=10)
    productos_res = requests.get(f"{ALMACEN_URL}/productos", headers=get_auth_header(request), timeout=10)

    if pedidos_res.status_code != 200:
        return json_response_from_service(pedidos_res)

    pedidos = pedidos_res.json()
    clientes = clientes_res.json() if clientes_res.status_code == 200 else []
    productos = productos_res.json() if productos_res.status_code == 200 else []

    clientes_por_id = {c.get("id"): c for c in clientes}
    productos_por_id = {p.get("id"): p for p in productos}

    historial = []
    for pedido in pedidos:
        cliente = clientes_por_id.get(pedido.get("cliente_id"), {})
        producto = productos_por_id.get(pedido.get("producto_id"), {})

        historial.append({
            "id": pedido.get("id"),
            "cliente_id": pedido.get("cliente_id"),
            "cliente_nombre": cliente.get("nombre", "Cliente eliminado" if pedido.get("cliente_id") == 0 else "Cliente no encontrado"),
            "cliente_email": cliente.get("email", "Sin correo"),
            "producto_id": pedido.get("producto_id"),
            "producto_nombre": producto.get("nombre", "Producto eliminado" if pedido.get("producto_id") == 0 else "Producto no encontrado"),
            "cantidad": pedido.get("cantidad"),
            "estado": pedido.get("estado"),
            "grupo_pedido": pedido.get("grupo_pedido"),
        })

    return historial
