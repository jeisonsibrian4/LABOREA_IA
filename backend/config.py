"""
LABOREA IA - Configuración.

Lee backend/.env (si existe) y deja las variables disponibles con os.getenv().
Este módulo se importa primero (database.py y main.py lo usan) para que el .env
esté cargado antes de crear la conexión o el cliente de Gemini.
"""

from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
