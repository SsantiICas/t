// Variables y funciones de sesión, alertas, modo oscuro y fetchJSON viven en common.js
// (compartido con admin.html). Aquí solo la lógica propia del SPA principal.
let clientesCache = [];
let productosCache = [];
let pedidosCache = [];
let contadorLineaOrden = 0;

function showSection(section, button = null) {
  document.querySelectorAll(".section").forEach(s => s.classList.add("hidden"));
  document.getElementById(section).classList.remove("hidden");

  document.querySelectorAll(".nav-btn").forEach(btn => btn.classList.remove("active"));
  if (button) button.classList.add("active");

  const titles = {
    panel: "Panel principal",
    clientes: "Gestión de clientes",
    productos: "Control de almacén",
    pedidos: "Registro de pedidos",
    historial: "Historial de pedidos"
  };

  document.getElementById("sectionTitle").innerText = titles[section] || "SmartLogistic";

  if (section === "historial") cargarHistorialPedidos();
}

function logout() {
  localStorage.removeItem("smartlogistic_token");
  localStorage.removeItem("smartlogistic_rol");
  token = "";
  rolActual = "usuario";
  document.getElementById("app").classList.add("hidden");
  document.getElementById("login").style.display = "flex";
  document.getElementById("email").value = "";
  document.getElementById("password").value = "";
  showAlert("Sesión cerrada correctamente");
}

// Ajusta la visibilidad de formularios según el rol del usuario autenticado, y
// muestra el acceso a "Administración" en el menú lateral solo para administradores.
// Regla: Usuario -> solo lectura. Gerente -> crear/editar/cambiar estado. Administrador -> todo.
function aplicarPermisosUI() {
  const puedeCrear = tieneRolMinimo("gerente");
  document.querySelectorAll("[data-requiere-gerente]").forEach(el => {
    el.classList.toggle("hidden", !puedeCrear);
  });

  const navAdmin = document.getElementById("navAdminBtn");
  if (navAdmin) navAdmin.classList.toggle("hidden", rolActual !== "administrador");
}

function validarEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

async function login(event) {
  if (event) event.preventDefault();

  const username = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();

  if (!username || !password) {
    document.getElementById("loginError").innerText = "Usuario y contraseña son obligatorios";
    return;
  }

  try {
    const data = await fetchJSON(`${API_GATEWAY}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    if (data.access_token) {
      token = data.access_token;
      rolActual = data.rol || "usuario";
      localStorage.setItem("smartlogistic_token", token);
      localStorage.setItem("smartlogistic_rol", rolActual);

      document.getElementById("loginError").innerText = "";
      document.getElementById("login").style.display = "none";
      document.getElementById("app").classList.remove("hidden");

      showAlert("Bienvenido a SmartLogistic");
      aplicarPermisosUI();
      await cargarDatosIniciales();
      showSection("panel", document.querySelector(".nav-btn"));
    } else {
      document.getElementById("loginError").innerText = "Credenciales incorrectas";
    }
  } catch (error) {
    console.error(error);
    showAlert("No se pudo conectar con autenticación", true);
  }
}

/* ============================ PANELES DE EDICIÓN ============================ */
// Abre/cierra el panel de edición (selección + actualización) de clientes o productos.
function togglePanelEdicion(tipo) {
  const panel = document.getElementById(tipo === "cliente" ? "panelEditarCliente" : "panelEditarProducto");
  panel.classList.toggle("hidden");
}

function cargarClienteEnPanel() {
  const id = parseInt(document.getElementById("editar_cliente_select").value);
  const cliente = clientesCache.find(c => c.id === id);

  document.getElementById("editar_cliente_nombre").value = cliente ? cliente.nombre : "";
  document.getElementById("editar_cliente_cedula_rif").value = cliente ? (cliente.cedula_rif || "") : "";
  document.getElementById("editar_cliente_telefono").value = cliente ? (cliente.telefono || "") : "";
  document.getElementById("editar_cliente_email").value = cliente ? (cliente.email || "") : "";
}

async function actualizarClienteDesdePanel(event) {
  if (event) event.preventDefault();

  const clienteId = parseInt(document.getElementById("editar_cliente_select").value);
  if (Number.isNaN(clienteId)) {
    showAlert("Seleccione un cliente para actualizar", true);
    return;
  }

  const nombre = document.getElementById("editar_cliente_nombre").value.trim();
  const cedula_rif = document.getElementById("editar_cliente_cedula_rif").value.trim();
  const telefono = document.getElementById("editar_cliente_telefono").value.trim();
  const email = document.getElementById("editar_cliente_email").value.trim();

  if (!nombre || !cedula_rif || !telefono || !validarEmail(email)) {
    showAlert("Verifique los datos: todos los campos son obligatorios y el correo debe ser válido", true);
    return;
  }

  try {
    await fetchJSON(`${API_GATEWAY}/clientes/${clienteId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, cedula_rif, telefono, email })
    });
    showAlert("Cliente actualizado correctamente");
    togglePanelEdicion("cliente");
    await cargarClientes();
    await cargarHistorialPedidos();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al actualizar cliente", true);
  }
}

function cargarProductoEnPanel() {
  const id = parseInt(document.getElementById("editar_producto_select").value);
  const producto = productosCache.find(p => p.id === id);

  document.getElementById("editar_producto_nombre").value = producto ? producto.nombre : "";
  document.getElementById("editar_producto_categoria").value = producto ? (producto.categoria || "") : "";
}

async function actualizarProductoDesdePanel(event) {
  if (event) event.preventDefault();

  const productoId = parseInt(document.getElementById("editar_producto_select").value);
  if (Number.isNaN(productoId)) {
    showAlert("Seleccione un producto para actualizar", true);
    return;
  }

  const nombre = document.getElementById("editar_producto_nombre").value.trim();
  const categoria = document.getElementById("editar_producto_categoria").value.trim() || "General";

  if (!nombre) {
    showAlert("El nombre del producto no puede estar vacío", true);
    return;
  }

  try {
    await fetchJSON(`${API_GATEWAY}/productos/${productoId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, categoria })
    });
    showAlert("Producto actualizado correctamente");
    togglePanelEdicion("producto");
    await cargarProductos();
    await cargarHistorialPedidos();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al actualizar producto", true);
  }
}

/* ============================ BUSCADORES ============================ */
function filtrarClientes() {
  const termino = document.getElementById("buscador_clientes").value.trim().toLowerCase();
  document.querySelectorAll("#lista_clientes .item-row[data-nombre]").forEach(row => {
    const coincide = row.dataset.nombre.includes(termino);
    row.classList.toggle("hidden", !coincide);
  });
}

function filtrarProductos() {
  const termino = document.getElementById("buscador_productos").value.trim().toLowerCase();
  document.querySelectorAll("#lista_productos .item-row[data-nombre]").forEach(row => {
    const coincide = row.dataset.nombre.includes(termino) || row.dataset.categoria.includes(termino);
    row.classList.toggle("hidden", !coincide);
  });
}

/* ============================ CLIENTES ============================ */
async function crearCliente(event) {
  if (event) event.preventDefault();

  const nombre = document.getElementById("cliente_nombre").value.trim();
  const cedula_rif = document.getElementById("cliente_cedula_rif").value.trim();
  const telefono = document.getElementById("cliente_telefono").value.trim();
  const email = document.getElementById("cliente_email").value.trim();

  if (!nombre || !cedula_rif || !telefono || !email) {
    showAlert("Complete nombre/razón social, cédula o RIF, teléfono y correo", true);
    return;
  }

  if (!validarEmail(email)) {
    showAlert("Ingrese un correo válido", true);
    return;
  }

  try {
    await fetchJSON(`${API_GATEWAY}/clientes`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ nombre, cedula_rif, telefono, email })
    });

    document.getElementById("cliente_nombre").value = "";
    document.getElementById("cliente_cedula_rif").value = "";
    document.getElementById("cliente_telefono").value = "";
    document.getElementById("cliente_email").value = "";
    showAlert("Cliente registrado correctamente");
    await cargarClientes();
    await cargarHistorialPedidos();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al registrar cliente", true);
  }
}

async function cambiarEstadoCliente(clienteId, activo) {
  try {
    await fetchJSON(`${API_GATEWAY}/clientes/${clienteId}/estado`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activo })
    });
    showAlert(`Cliente marcado como ${activo ? "ACTIVO" : "INACTIVO"}`);
    await cargarClientes();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al cambiar el estado del cliente", true);
    await cargarClientes(); // revierte visualmente el switch si falló
  }
}

async function eliminarCliente(clienteId) {
  const confirmado = confirm("¿Desea eliminar este cliente? Los IDs se reordenarán automáticamente.");
  if (!confirmado) return;

  try {
    await fetchJSON(`${API_GATEWAY}/clientes/${clienteId}`, { method: "DELETE" });
    showAlert("Cliente eliminado y numeración actualizada");
    await cargarClientes();
    await cargarHistorialPedidos();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al eliminar cliente", true);
  }
}

function renderSwitchEstado(id, activo, onChangeFn) {
  // Switch ACTIVO/INACTIVO con utilidades de Tailwind. Bordes poco redondeados (rounded-md)
  // para una estética más firme, en vez del típico interruptor tipo píldora (rounded-full).
  return `
    <label class="relative inline-flex items-center cursor-pointer select-none">
      <input type="checkbox" class="sr-only peer" ${activo ? "checked" : ""}
        onchange="${onChangeFn}(${id}, this.checked)">
      <div class="w-11 h-6 bg-gray-300 peer-checked:bg-green-700 rounded-md border border-slate-400 transition-colors"></div>
      <div class="absolute left-1 top-1 bg-white w-4 h-4 rounded-sm shadow transition-transform peer-checked:translate-x-5"></div>
      <span class="ml-2 text-xs font-bold ${activo ? "text-green-700" : "text-gray-500"}">${activo ? "ACTIVO" : "INACTIVO"}</span>
    </label>
  `;
}

async function cargarClientes() {
  clientesCache = await fetchJSON(`${API_GATEWAY}/clientes`);

  const lista = document.getElementById("lista_clientes");
  const select = document.getElementById("pedido_cliente");
  const selectEditar = document.getElementById("editar_cliente_select");
  lista.innerHTML = "";
  select.innerHTML = '<option value="">Seleccione un cliente</option>';
  selectEditar.innerHTML = '<option value="">Seleccione un cliente para editar</option>';

  if (!clientesCache.length) {
    lista.innerHTML = `<div class="item-row no-id"><div><div class="item-title">Sin clientes registrados</div><div class="item-subtitle">Registre un cliente para iniciar operaciones.</div></div><span class="badge">Clientes</span></div>`;
  }

  const puedeEliminar = tieneRolMinimo("administrador");

  clientesCache.forEach(cliente => {
    const row = document.createElement("div");
    row.className = "item-row with-actions no-id";
    row.dataset.nombre = cliente.nombre.toLowerCase();
    row.innerHTML = `
      <div>
        <div class="item-title">${cliente.nombre}</div>
        <div class="item-subtitle">${cliente.cedula_rif || "Sin cédula/RIF"} · ${cliente.telefono || "Sin teléfono"} · ${cliente.email}</div>
      </div>
      <div class="item-actions">
        ${renderSwitchEstado(cliente.id, cliente.activo, "cambiarEstadoCliente")}
        ${puedeEliminar ? `<button type="button" class="danger-btn" onclick="eliminarCliente(${cliente.id})">Eliminar</button>` : ""}
      </div>
    `;
    lista.appendChild(row);

    const option = document.createElement("option");
    option.value = cliente.id;
    option.textContent = `${cliente.nombre}${cliente.activo ? "" : " (INACTIVO)"}`;
    if (!cliente.activo) option.disabled = true; // no se pueden crear pedidos para clientes inactivos
    select.appendChild(option);

    const optionEditar = document.createElement("option");
    optionEditar.value = cliente.id;
    optionEditar.textContent = `${cliente.nombre}${cliente.activo ? "" : " (INACTIVO)"}`;
    selectEditar.appendChild(optionEditar);
  });

  document.getElementById("total_clientes").innerText = clientesCache.length;

  const buscador = document.getElementById("buscador_clientes");
  if (buscador && buscador.value.trim()) filtrarClientes();
}

/* ============================ ALMACÉN / PRODUCTOS ============================ */
async function crearProducto(event) {
  if (event) event.preventDefault();

  const nombre = document.getElementById("producto_nombre").value.trim();
  const categoria = document.getElementById("producto_categoria").value.trim() || "General";
  const stock = parseInt(document.getElementById("producto_stock").value);

  if (!nombre || Number.isNaN(stock) || stock <= 0) {
    showAlert("Complete producto y stock mayor a 0", true);
    return;
  }

  try {
    await fetchJSON(`${API_GATEWAY}/productos`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ nombre, categoria, stock })
    });

    document.getElementById("producto_nombre").value = "";
    document.getElementById("producto_categoria").value = "";
    document.getElementById("producto_stock").value = "";
    showAlert("Producto registrado en almacén");
    await cargarProductos();
    await cargarHistorialPedidos();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al registrar producto", true);
  }
}

async function cambiarEstadoProducto(productoId, activo) {
  try {
    await fetchJSON(`${API_GATEWAY}/productos/${productoId}/estado`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activo })
    });
    showAlert(`Producto marcado como ${activo ? "ACTIVO" : "INACTIVO"}`);
    await cargarProductos();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al cambiar el estado del producto", true);
    await cargarProductos();
  }
}

async function actualizarStock(productoId) {
  const input = document.getElementById(`stock_producto_${productoId}`);
  const stock = parseInt(input.value);

  if (Number.isNaN(stock) || stock < 0) {
    showAlert("Ingrese un stock válido", true);
    return;
  }

  try {
    await fetchJSON(`${API_GATEWAY}/productos/${productoId}/stock`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ stock })
    });
    showAlert("Stock actualizado correctamente");
    await cargarProductos();
    await cargarHistorialPedidos();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al actualizar stock", true);
  }
}

async function eliminarProducto(productoId) {
  const confirmado = confirm("¿Desea eliminar este producto? Los IDs se reordenarán automáticamente.");
  if (!confirmado) return;

  try {
    await fetchJSON(`${API_GATEWAY}/productos/${productoId}`, { method: "DELETE" });
    showAlert("Producto eliminado y numeración actualizada");
    await cargarProductos();
    await cargarHistorialPedidos();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al eliminar producto", true);
  }
}

async function cargarProductos() {
  productosCache = await fetchJSON(`${API_GATEWAY}/productos`);

  const lista = document.getElementById("lista_productos");
  const selectEditar = document.getElementById("editar_producto_select");
  lista.innerHTML = "";
  selectEditar.innerHTML = '<option value="">Seleccione un producto para editar</option>';

  if (!productosCache.length) {
    lista.innerHTML = `<div class="item-row no-id"><div><div class="item-title">Sin productos registrados</div><div class="item-subtitle">Registre productos para controlar el almacén.</div></div><span class="badge">Almacén</span></div>`;
  }

  const puedeEliminar = tieneRolMinimo("administrador");

  productosCache.forEach(producto => {
    const row = document.createElement("div");
    row.className = "item-row with-actions no-id";
    row.dataset.nombre = producto.nombre.toLowerCase();
    row.dataset.categoria = (producto.categoria || "").toLowerCase();
    row.innerHTML = `
      <div>
        <div class="item-title">${producto.nombre}</div>
        <div class="item-subtitle">${producto.categoria || "General"} · Stock disponible: ${producto.stock}</div>
      </div>
      <div class="item-actions">
        ${renderSwitchEstado(producto.id, producto.activo, "cambiarEstadoProducto")}
        <input class="inline-input" id="stock_producto_${producto.id}" type="number" min="0" value="${producto.stock}">
        <button type="button" class="small-btn" onclick="actualizarStock(${producto.id})">Actualizar stock</button>
        ${puedeEliminar ? `<button type="button" class="danger-btn" onclick="eliminarProducto(${producto.id})">Eliminar</button>` : ""}
      </div>
    `;
    lista.appendChild(row);

    const option = document.createElement("option");
    option.value = producto.id;
    option.textContent = `${producto.nombre} | Stock: ${producto.stock}`;
    selectEditar.appendChild(option);
  });

  document.getElementById("total_productos").innerText = productosCache.length;

  const buscador = document.getElementById("buscador_productos");
  if (buscador && buscador.value.trim()) filtrarProductos();

  refrescarSelectsDeOrden();
}

/* ============================ PEDIDOS: ORDEN MULTI-PRODUCTO ============================ */
function opcionesProductosHTML(idSeleccionado) {
  let opciones = '<option value="">Seleccione un producto</option>';
  productosCache.forEach(p => {
    const seleccionado = String(p.id) === String(idSeleccionado) ? "selected" : "";
    const inactivo = !p.activo;
    const etiqueta = `${p.nombre} | Stock: ${p.stock}${inactivo ? " (INACTIVO)" : ""}`;
    opciones += `<option value="${p.id}" ${seleccionado} ${inactivo ? "disabled" : ""}>${etiqueta}</option>`;
  });
  return opciones;
}

function renderLineaOrden(lineaId) {
  return `
    <div class="flex flex-wrap gap-2 items-center border border-slate-300 rounded-md p-2" data-linea-id="${lineaId}">
      <select class="linea-producto flex-1 min-w-[180px] border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/30 focus:border-blue-800">
        ${opcionesProductosHTML("")}
      </select>
      <input type="number" min="1" placeholder="Cantidad"
        class="linea-cantidad w-28 border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/30 focus:border-blue-800">
      <button type="button" class="danger-btn" onclick="eliminarLineaOrden(${lineaId})">Quitar</button>
    </div>
  `;
}

function agregarLineaOrden() {
  contadorLineaOrden += 1;
  const contenedor = document.getElementById("lineas_orden");
  const envoltorio = document.createElement("div");
  envoltorio.innerHTML = renderLineaOrden(contadorLineaOrden).trim();
  contenedor.appendChild(envoltorio.firstElementChild);
}

function eliminarLineaOrden(lineaId) {
  const contenedor = document.getElementById("lineas_orden");
  const fila = contenedor.querySelector(`[data-linea-id="${lineaId}"]`);
  if (fila) fila.remove();
  if (!contenedor.children.length) agregarLineaOrden();
}

function refrescarSelectsDeOrden() {
  document.querySelectorAll("#lineas_orden .linea-producto").forEach(select => {
    const valorActual = select.value;
    select.innerHTML = opcionesProductosHTML(valorActual);
  });
}

async function crearOrdenPedido(event) {
  if (event) event.preventDefault();

  const cliente_id = parseInt(document.getElementById("pedido_cliente").value);
  if (Number.isNaN(cliente_id)) {
    showAlert("Seleccione un cliente", true);
    return;
  }

  const filas = document.querySelectorAll("#lineas_orden [data-linea-id]");
  const items = [];
  for (const fila of filas) {
    const producto_id = parseInt(fila.querySelector(".linea-producto").value);
    const cantidad = parseInt(fila.querySelector(".linea-cantidad").value);
    if (!Number.isNaN(producto_id) && !Number.isNaN(cantidad) && cantidad > 0) {
      items.push({ producto_id, cantidad });
    }
  }

  if (!items.length) {
    showAlert("Agregue al menos un producto con una cantidad válida", true);
    return;
  }

  try {
    await fetchJSON(`${API_GATEWAY}/pedidos/orden`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ cliente_id, items })
    });

    document.getElementById("pedido_cliente").value = "";
    document.getElementById("lineas_orden").innerHTML = "";
    agregarLineaOrden();
    showAlert("Orden procesada correctamente");

    await cargarProductos();
    await cargarHistorialPedidos();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al procesar la orden", true);
  }
}

/* ============================ HISTORIAL DE PEDIDOS ============================ */
function badgeEstado(estado) {
  if (estado === "completado") return "badge done";
  if (estado === "rechazado") return "badge rejected";
  if (estado === "devuelto") return "badge returned";
  return "badge";
}

async function actualizarEstadoPedido(pedidoId, estado) {
  try {
    await fetchJSON(`${API_GATEWAY}/pedidos/${pedidoId}/estado`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ estado })
    });
    showAlert(`Pedido marcado como ${estado}`);
    await cargarHistorialPedidos();
    await cargarProductos(); // el stock puede cambiar al procesar una devolución
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al actualizar estado", true);
  }
}

async function eliminarPedido(pedidoId) {
  const confirmado = confirm("¿Desea eliminar este pedido del historial? La numeración se actualizará automáticamente.");
  if (!confirmado) return;

  try {
    await fetchJSON(`${API_GATEWAY}/pedidos/${pedidoId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      }
    });

    showAlert("Pedido eliminado del historial");
    await cargarHistorialPedidos();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al eliminar pedido", true);
  }
}

async function cargarHistorialPedidos() {
  const contenedor = document.getElementById("lista_historial");
  contenedor.innerHTML = "";

  const puedeCambiarEstado = tieneRolMinimo("gerente");
  const puedeEliminar = tieneRolMinimo("administrador");

  try {
    pedidosCache = await fetchJSON(`${API_GATEWAY}/historial-pedidos`);

    if (!pedidosCache.length) {
      contenedor.innerHTML = `<div class="item-row"><span class="item-id">--</span><div><div class="item-title">Sin pedidos registrados</div><div class="item-subtitle">Procese una orden para visualizarla aquí.</div></div><span class="badge">Historial</span></div>`;
    }

    pedidosCache.forEach(pedido => {
      const row = document.createElement("div");
      row.className = "item-row with-actions";

      const acciones = [];
      if (puedeCambiarEstado) {
        if (pedido.estado === "pendiente") {
          acciones.push(`<button type="button" class="small-btn" onclick="actualizarEstadoPedido(${pedido.id}, 'completado')">Completado</button>`);
          acciones.push(`<button type="button" class="danger-btn" onclick="actualizarEstadoPedido(${pedido.id}, 'rechazado')">Rechazado</button>`);
        }
        if (pedido.estado === "completado") {
          acciones.push(`<button type="button" class="small-btn" onclick="actualizarEstadoPedido(${pedido.id}, 'devuelto')">Devolver</button>`);
        }
      }
      if (puedeEliminar) {
        acciones.push(`<button type="button" class="danger-btn" onclick="eliminarPedido(${pedido.id})">Eliminar pedido</button>`);
      }

      const etiquetaOrden = pedido.grupo_pedido ? `Orden #${pedido.grupo_pedido}` : `Cliente ID: ${pedido.cliente_id}`;

      row.innerHTML = `
        <span class="item-id">#${pedido.id}</span>
        <div>
          <div class="item-title">${pedido.cliente_nombre} solicitó ${pedido.cantidad} unidad(es) de ${pedido.producto_nombre}</div>
          <div class="item-subtitle">${etiquetaOrden} · Producto ID: ${pedido.producto_id}</div>
        </div>
        <div class="item-actions">
          <span class="${badgeEstado(pedido.estado)}">${pedido.estado}</span>
          ${acciones.join("")}
        </div>
      `;
      contenedor.appendChild(row);
    });

    document.getElementById("total_pedidos").innerText = pedidosCache.length;
  } catch (error) {
    console.error(error);
    contenedor.innerHTML = `<div class="item-row"><span class="item-id">!</span><div><div class="item-title">No se pudo cargar el historial</div><div class="item-subtitle">Verifique que gateway y pedidos-service estén activos.</div></div><span class="badge">Error</span></div>`;
  }
}

async function cargarDatosIniciales() {
  await cargarClientes();
  await cargarProductos();
  await cargarHistorialPedidos();

  if (!document.getElementById("lineas_orden").children.length) {
    agregarLineaOrden();
  }
}

window.addEventListener("load", async () => {
  aplicarModoGuardado();
  token = localStorage.getItem("smartlogistic_token") || "";
  rolActual = localStorage.getItem("smartlogistic_rol") || "usuario";

  if (token) {
    document.getElementById("login").style.display = "none";
    document.getElementById("app").classList.remove("hidden");
    aplicarPermisosUI();

    try {
      await cargarDatosIniciales();
      showSection("panel", document.querySelector(".nav-btn"));
    } catch (error) {
      console.error("Error cargando datos iniciales:", error);
    }
  }
});
