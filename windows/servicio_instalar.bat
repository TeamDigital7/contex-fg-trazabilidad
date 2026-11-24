@echo off
REM Ejecutar con clic derecho > "Ejecutar como administrador".
REM Registra la app para que arranque sola al encender el servidor y abre el puerto 8501 en la red interna.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0servicio_instalar.ps1"
pause
