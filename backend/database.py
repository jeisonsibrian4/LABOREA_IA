"""
LABOREA IA - Conexión a la base de datos.

Por defecto usa SQLite (un archivo laborea.db, no hace falta instalar nada).
Para PostgreSQL, poné en backend/.env:
    DATABASE_URL=postgresql://usuario:clave@localhost:5432/laborea
Nunca se deja ninguna clave escrita en el código.
"""

import os

import config  # noqa: F401  (carga el .env antes de leer DATABASE_URL)
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or "sqlite:///./laborea.db"


def _forzar_psycopg2(url: str) -> str:
    """Si la URL es de PostgreSQL sin driver explícito, usa psycopg2."""
    esquema, separador, resto = url.partition("://")
    if separador and esquema in ("postgres", "postgresql"):
        return "postgresql+psycopg2" + separador + resto
    return url


DATABASE_URL = _forzar_psycopg2(DATABASE_URL)

if DATABASE_URL.startswith("sqlite"):
    # SQLite + FastAPI (varios hilos): hay que desactivar la verificación de hilo.
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", "5") or 5),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10") or 10),
        pool_recycle=1800,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: una sesión de base de datos por pedido."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
