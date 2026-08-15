// Lógica de la página de administración (admin.html): crear/actualizar usuarios y
// listar/buscar/filtrar los usuarios del sistema. Requiere sesión con rol
// administrador (ver exigirAdministrador() en common.js).

let usuariosCache = [];

function logout() {
  localStorage.removeItem("smartlogistic_token");
  localStorage.removeItem("smartlogistic_rol");
  window.location.href = "index.html";
}

async function crearUsuarioAdmin(event) {
  if (event) event.preventDefault();

  const username = document.getElementById("admin_username").value.trim();
  const password = document.getElementById("admin_password").value;
  const rol = document.getElementById("admin_rol").value;

  if (!username || !password) {
    showAlert("Complete usuario y contraseña", true);
    return;
  }

  if (!passwordCumpleRequisitos(password)) {
    showAlert("La contraseña no cumple todos los requisitos de seguridad", true);
    return;
  }

  try {
    await fetchJSON(`${API_GATEWAY}/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ username, password, rol })
    });

    document.getElementById("admin_username").value = "";
    document.getElementById("admin_password").value = "";
    document.getElementById("admin_rol").value = "usuario";
    renderChecklistPassword("", "checklist_admin_password");
    showAlert(`Usuario "${username}" creado con rol ${rol}`);
    await cargarUsuariosAdmin();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al crear el usuario", true);
  }
}

/* ============================ EDICIÓN DE USUARIOS ============================ */
function togglePanelEdicionUsuario() {
  document.getElementById("panelEditarUsuario").classList.toggle("hidden");
}

function cargarUsuarioEnPanel() {
  const id = parseInt(document.getElementById("editar_usuario_select").value);
  const usuario = usuariosCache.find(u => u.id === id);

  document.getElementById("editar_usuario_username").value = usuario ? usuario.username : "";
  document.getElementById("editar_usuario_rol").value = usuario ? usuario.rol : "usuario";
  document.getElementById("editar_usuario_password").value = "";
  renderChecklistPassword("", "checklist_editar_usuario_password");
}

// Abre el panel de edición ya con un usuario específico seleccionado (botón "Editar" de la fila).
function editarUsuarioDesde(usuarioId) {
  const panel = document.getElementById("panelEditarUsuario");
  panel.classList.remove("hidden");
  document.getElementById("editar_usuario_select").value = usuarioId;
  cargarUsuarioEnPanel();
  panel.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function actualizarUsuarioDesdePanel(event) {
  if (event) event.preventDefault();

  const usuarioId = parseInt(document.getElementById("editar_usuario_select").value);
  if (Number.isNaN(usuarioId)) {
    showAlert("Seleccione un usuario para actualizar", true);
    return;
  }

  const username = document.getElementById("editar_usuario_username").value.trim();
  const password = document.getElementById("editar_usuario_password").value;
  const rol = document.getElementById("editar_usuario_rol").value;

  if (!username) {
    showAlert("El nombre de usuario no puede estar vacío", true);
    return;
  }

  if (password && !passwordCumpleRequisitos(password)) {
    showAlert("La nueva contraseña no cumple todos los requisitos de seguridad", true);
    return;
  }

  try {
    await fetchJSON(`${API_GATEWAY}/usuarios/${usuarioId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password: password || null, rol })
    });

    showAlert("Usuario actualizado correctamente");
    togglePanelEdicionUsuario();
    await cargarUsuariosAdmin();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "Error al actualizar el usuario", true);
  }
}

/* ============================ LISTADO / BÚSQUEDA / FILTRO ============================ */
function renderUsuariosAdmin(usuarios) {
  const contenedor = document.getElementById("lista_usuarios_admin");

  if (!usuarios.length) {
    contenedor.innerHTML = `<div class="item-row user-row"><span class="item-title">Sin resultados</span><span></span><span></span><span></span></div>`;
    return;
  }

  contenedor.innerHTML = usuarios.map(u => `
    <div class="item-row user-row">
      <span class="item-title">${u.username}</span>
      <span class="badge">${u.rol}</span>
      <span class="item-subtitle">#${u.id}</span>
      <span><button type="button" class="small-btn" onclick="editarUsuarioDesde(${u.id})">Editar</button></span>
    </div>
  `).join("");
}

function filtrarUsuariosAdmin() {
  const termino = document.getElementById("buscador_usuarios").value.trim().toLowerCase();
  const rolFiltro = document.getElementById("filtro_rol_usuarios").value;

  const filtrados = usuariosCache.filter(u => {
    const coincideNombre = u.username.toLowerCase().includes(termino);
    const coincideRol = !rolFiltro || u.rol === rolFiltro;
    return coincideNombre && coincideRol;
  });

  renderUsuariosAdmin(filtrados);
}

function refrescarSelectEdicionUsuarios() {
  const select = document.getElementById("editar_usuario_select");
  const valorActual = select.value;
  select.innerHTML = '<option value="">Seleccione un usuario para editar</option>';

  usuariosCache.forEach(u => {
    const option = document.createElement("option");
    option.value = u.id;
    option.textContent = `${u.username} (${u.rol})`;
    select.appendChild(option);
  });

  if (valorActual) select.value = valorActual;
}

async function cargarUsuariosAdmin() {
  try {
    usuariosCache = await fetchJSON(`${API_GATEWAY}/usuarios`);
    filtrarUsuariosAdmin();
    refrescarSelectEdicionUsuarios();
  } catch (error) {
    console.error(error);
    showAlert(error.message || "No se pudo cargar la lista de usuarios", true);
    document.getElementById("lista_usuarios_admin").innerHTML =
      `<div class="item-row user-row"><span class="item-title">No se pudo cargar la lista de usuarios</span><span></span><span></span><span></span></div>`;
  }
}

window.addEventListener("load", async () => {
  aplicarModoGuardado();

  if (!exigirAdministrador()) return;

  await cargarUsuariosAdmin();
});
