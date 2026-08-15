@echo off
title SmartLogistic - Detener Sistema
echo Deteniendo procesos uvicorn y servidor frontend...

taskkill /F /IM python.exe /FI "WINDOWTITLE eq SmartLogistic*" >nul 2>&1

echo Si alguna ventana queda abierta, cierrala manualmente con CTRL+C.
pause
