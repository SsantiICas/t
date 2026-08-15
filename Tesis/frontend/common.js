// Utilidades compartidas entre index.html (app.js) y admin.html (admin.js):
// sesión (token/rol), notificaciones, modo oscuro y helper de fetch autenticado.

const API_GATEWAY = "http://127.0.0.1:8002";
let token = localStorage.getItem("smartlogistic_token") || "";
let rolActual = localStorage.getItem("smartlogistic_rol") || "usuario";

// Jerarquía de roles: Administrador > Gerente > Usuario.
const NIVEL_ROL = { administrador: 3, gerente: 2, usuario: 1 };

function tieneRolMinimo(rolMinimo) {
  return (NIVEL_ROL[rolActual] || 0) >= (NIVEL_ROL[rolMinimo] || 99);
}

function showAlert(msg, error = false) {
  const alertBox = document.getElementById("alert");
  if (!alertBox) return;
  alertBox.innerText = msg || "Ocurrió un error";
  alertBox.style.background = error ? "#d93838" : "#18864b";
  alertBox.classList.remove("hidden");

  setTimeout(() => {
    alertBox.classList.add("hidden");
  }, 3200);
}

function toggleDarkMode() {
  document.body.classList.toggle("dark-mode");
  const active = document.body.classList.contains("dark-mode");
  localStorage.setItem("smartlogistic_dark_mode", active ? "1" : "0");
}

function aplicarModoGuardado() {
  if (localStorage.getItem("smartlogistic_dark_mode") === "1") {
    document.body.classList.add("dark-mode");
  }
}

async function fetchJSON(url, options = {}) {
  const headers = { ...(options.headers || {}) };

  if (token && !headers.Authorization && !headers.authorization) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(url, { ...options, headers });
  let data = null;

  try {
    data = await res.json();
  } catch (error) {
    data = { error: "Respuesta no válida del servidor" };
  }

  if (!res.ok) {
    throw new Error(data.detail || data.error || "Error en la solicitud");
  }

  return data;
}

// Muestra/oculta el texto de un campo de contraseña y actualiza la etiqueta del botón.
function togglePasswordVisibility(inputId, boton) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const mostrar = input.type === "password";
  input.type = mostrar ? "text" : "password";
  if (boton) boton.textContent = mostrar ? "Ocultar" : "Ver";
}

// Misma regla de contraseña exigida por auth-service (schemas.py -> validar_password):
// mínimo 8 caracteres, al menos una letra, una mayúscula y un carácter especial.
function validarRequisitosPassword(password) {
  return {
    longitud: password.length >= 8,
    letra: /[A-Za-z]/.test(password),
    mayuscula: /[A-Z]/.test(password),
    especial: /[^A-Za-z0-9]/.test(password),
  };
}

function passwordCumpleRequisitos(password) {
  const req = validarRequisitosPassword(password);
  return req.longitud && req.letra && req.mayuscula && req.especial;
}

// Pinta la lista de requisitos (check/cruz) debajo de un campo de contraseña.
function renderChecklistPassword(password, contenedorId) {
  const contenedor = document.getElementById(contenedorId);
  if (!contenedor) return;

  const req = validarRequisitosPassword(password);
  const items = [
    [req.longitud, "Mínimo 8 caracteres"],
    [req.letra, "Al menos una letra"],
    [req.mayuscula, "Al menos una letra mayúscula"],
    [req.especial, "Al menos un carácter especial"],
  ];

  contenedor.innerHTML = items.map(([cumple, texto]) => `
    <li class="flex items-center gap-1.5 ${cumple ? "text-green-700" : "text-slate-400"}">
      <span>${cumple ? "✓" : "○"}</span><span>${texto}</span>
    </li>
  `).join("");
}

// Redirige a index.html si no hay una sesión iniciada. Se usa en páginas
// aparte del SPA principal (ej. admin.html) que requieren sesión activa.
function exigirSesion() {
  if (!token) {
    window.location.href = "index.html";
    return false;
  }
  return true;
}

// Redirige al panel principal si el usuario autenticado no es administrador.
function exigirAdministrador() {
  if (!exigirSesion()) return false;
  if (rolActual !== "administrador") {
    showAlert("Esta sección es exclusiva para el rol administrador", true);
    setTimeout(() => { window.location.href = "index.html"; }, 1200);
    return false;
  }
  return true;
}
