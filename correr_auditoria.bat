@echo off
REM LABOREA IA - Ejecucion de la Suite de Auditoria y Pruebas
cd /d "%~dp0"
echo ========================================================
echo   LABOREA IA - AUDITORIA TECNICA Y SUITE DE PRUEBAS
echo ========================================================
echo.

if not exist .venv (
    echo [ERROR] No se encontro el entorno virtual .venv.
    echo Por favor ejecuta primero 'setup.bat' para instalar el proyecto.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Instalando dependencias de prueba (pytest, httpx, reportlab)...
pip install -r backend\requirements-dev.txt -q

echo.
echo Ejecutando las 20 pruebas de auditoria...
echo.
cd backend
python -m pytest tests -v
cd ..

echo.
echo ========================================================
echo Auditoria finalizada.
echo ========================================================
pause
