@echo off
setlocal
cd /d "%~dp0"
title SmartLogistic - Iniciador del Sistema

echo ========================================
echo     SMARTLOGISTIC OPERACIONES
echo     Iniciando microservicios...
echo ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python no esta instalado o no esta agregado al PATH.
  echo Instala Python y marca la opcion "Add Python to PATH".
  pause
  exit /b
)

REM Iniciar microservicios
start "SmartLogistic - Clientes" cmd /k "cd /d "%~dp0clientes-service" && python -m uvicorn main:app --reload --port 8000"
start "SmartLogistic - Almacen" cmd /k "cd /d "%~dp0almacen-service" && python -m uvicorn main:app --reload --port 8003"
start "SmartLogistic - Auth" cmd /k "cd /d "%~dp0auth-service" && python -m uvicorn main:app --reload --port 8004"
start "SmartLogistic - Pedidos" cmd /k "cd /d "%~dp0pedidos-service" && python -m uvicorn main:app --reload --port 8001"
start "SmartLogistic - Gateway" cmd /k "cd /d "%~dp0gateway" && python -m uvicorn main:app --reload --port 8002"
start "SmartLogistic - Frontend" cmd /k "cd /d "%~dp0frontend" && python -m http.server 5500"

echo.
echo Esperando que los servicios inicien...
timeout /t 4 /nobreak >nul

echo Abriendo SmartLogistic en el navegador...
start http://127.0.0.1:5500

echo.
echo ========================================
echo Sistema iniciado.
echo URL principal: http://127.0.0.1:5500
echo Gateway docs:   http://127.0.0.1:8002/docs
echo ========================================
echo.
echo Puedes cerrar esta ventana. Las terminales de servicios quedan abiertas.
pause
