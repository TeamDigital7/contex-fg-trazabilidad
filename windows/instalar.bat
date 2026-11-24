@echo off
REM ==========================================================================
REM  Contex FYG - Trazabilidad: instalacion en un servidor Windows de Contex
REM  Ejecutar UNA vez (doble clic). Requiere Python 3.11 o superior instalado
REM  "para todos los usuarios" y con la casilla "Add python.exe to PATH".
REM ==========================================================================
setlocal
cd /d "%~dp0.."
echo.
echo  Instalando la app de Trazabilidad de Contex FYG...
echo.

where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo  [ERROR] No se encontro Python. Instalalo desde https://www.python.org/downloads/
  echo          marcando "Install for all users" y "Add python.exe to PATH".
  pause & exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo  Creando el entorno de Python en .venv ...
  %PY% -m venv .venv || (echo  [ERROR] No se pudo crear el entorno. & pause & exit /b 1)
)

echo  Instalando librerias (puede tardar unos minutos)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo  [ERROR] Fallo la instalacion de librerias. & pause & exit /b 1)

if not exist ".streamlit\secrets.toml" (
  copy ".streamlit\secrets.local.example.toml" ".streamlit\secrets.toml" >nul
  echo.
  echo  Se creo .streamlit\secrets.toml a partir del ejemplo.
  echo  EDITALO con los datos de su SQL Server antes de usar la app con datos reales.
  echo  Mientras no lo edites, la app funciona con datos de demostracion.
)
if not exist "logs" mkdir logs

echo.
echo  Listo. Siguientes pasos:
echo    1. Editar .streamlit\secrets.toml  (conexion al SQL Server)
echo    2. Probar la conexion:   windows\probar_conexion.bat
echo    3. Abrir la app ahora:   windows\iniciar.bat
echo    4. Que arranque sola al encender el servidor:  windows\servicio_instalar.bat (como administrador)
echo.
pause
