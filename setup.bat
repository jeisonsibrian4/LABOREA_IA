@echo off
REM LABOREA IA - instalación (se corre una sola vez)
cd /d "%~dp0"
echo === Backend ===
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r backend\requirements.txt
if not exist backend\.env copy backend\.env.example backend\.env
echo.
echo === Frontend ===
cd frontend
call npm install
cd ..
echo.
echo Listo. Abri backend\.env y pega tu clave de Gemini (opcional: sin clave funciona en modo reglas).
pause
