"""
LABOREA IA - API (FastAPI).

Endpoints:
  POST   /api/sesion               inicia la conversación (SESION_CHAT) y devuelve la 1.ª pregunta
  GET    /api/sesion/{id}          estado, historial y último análisis (retoma la conversación)
  POST   /api/chat                 mensajes: perfilamiento (3 preguntas) y asesoría posterior
  POST   /api/cv                   sube el CV (PDF o Word), lo valida y devuelve el diagnóstico
  GET    /api/analisis/{id}        último diagnóstico guardado (ANALISIS_IA)
  GET    /api/enlaces/{id}         recursos gratuitos del plan de estudio
  DELETE /api/sesion/{id}          borra la sesión y todos sus datos (CV incluido)
  GET    /health                   estado del servicio

Para correrlo:   cd backend  ->  uvicorn main:app --port 8001 --reload
"""

import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

import config  # noqa: F401  (carga el .env primero)
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import models  # noqa: F401  (registra las tablas)
from cv_extractor import MAX_BYTES
from database import Base, SessionLocal, engine, get_db
from models import MensajeChat, SesionChat
from orquestador import ComponenteIA, Orquestador
from rag import Recuperador
from schemas import ID_SESION_PATRON, ChatMensaje

log = logging.getLogger("laborea")
logging.basicConfig(level=logging.INFO)

ENTORNO = os.getenv("ENTORNO", "desarrollo").strip().lower()
_RE_ID = re.compile(ID_SESION_PATRON)


# ---- límites por IP (en memoria) --------------------------------------------
class LimitePorVentana:
    """Máximo `maximo` pedidos por clave (IP) en una ventana de `segundos`."""

    def __init__(self, maximo: int, segundos: int = 3600) -> None:
        self.maximo, self.segundos = maximo, segundos
        self._eventos = defaultdict(deque)
        self._lock = threading.Lock()

    def consumir(self, clave: str) -> bool:
        ahora = time.monotonic()
        with self._lock:
            cola = self._eventos[clave]
            while cola and ahora - cola[0] > self.segundos:
                cola.popleft()
            if len(cola) >= self.maximo:
                return False
            cola.append(ahora)
            return True


_lim_sesion = LimitePorVentana(int(os.getenv("LIMITE_SESIONES_HORA", "20")))
_lim_chat = LimitePorVentana(int(os.getenv("LIMITE_CHAT_HORA", "80")))
_lim_cv = LimitePorVentana(int(os.getenv("LIMITE_CV_HORA", "10")))


def _limitar(limite: LimitePorVentana):
    def dependencia(request: Request) -> None:
        ip = request.client.host if request.client else "desconocida"
        if not limite.consumir(ip):
            raise HTTPException(status_code=429, detail="Hiciste muchos pedidos en poco tiempo. Esperá un rato y probá de nuevo.")
    return dependencia


# ---- componentes compartidos -------------------------------------------------
_RECUPERADOR = Recuperador()
_IA = ComponenteIA()


def get_ia() -> ComponenteIA:
    return _IA


def get_recuperador() -> Recuperador:
    return _RECUPERADOR


def get_orquestador(db: Session = Depends(get_db), ia: ComponenteIA = Depends(get_ia),
                    rag: Recuperador = Depends(get_recuperador)) -> Orquestador:
    return Orquestador(db, ia, rag)


def _sesion_o_404(db: Session, session_id: str) -> SesionChat:
    if not _RE_ID.match(session_id):
        raise HTTPException(status_code=422, detail="Identificador de sesión inválido.")
    sesion = db.get(SesionChat, session_id)
    if sesion is None or not sesion.activa:
        raise HTTPException(status_code=404, detail="La sesión no existe o venció. Empezá una nueva.")
    return sesion


def purgar_sesiones_viejas(dias: int) -> int:
    """Privacidad: borra las sesiones (y sus CV) sin actividad hace más de `dias` días. 0 = no borra nada."""
    if dias <= 0:
        return 0
    db = SessionLocal()
    try:
        corte = datetime.now(timezone.utc) - timedelta(days=dias)
        viejas = db.query(SesionChat).filter(SesionChat.ultima_actividad < corte).all()
        for s in viejas:
            db.delete(s)
        db.commit()
        return len(viejas)
    finally:
        db.close()


@asynccontextmanager
async def ciclo_vida(_app):
    Base.metadata.create_all(bind=engine)
    borradas = purgar_sesiones_viejas(int(os.getenv("RETENCION_DIAS", "30") or 0))
    if borradas:
        log.info("Se borraron %d sesiones sin actividad", borradas)
    log.info("Gemini: %s", "activo (%s)" % _IA.gemini.modelo if _IA.gemini.disponible else "sin clave -> modo reglas")
    yield


app = FastAPI(
    title="LABOREA IA - Backend",
    version="1.0.0",
    lifespan=ciclo_vida,
    docs_url=None if ENTORNO == "produccion" else "/docs",
    redoc_url=None if ENTORNO == "produccion" else "/redoc",
    openapi_url=None if ENTORNO == "produccion" else "/openapi.json",
)

_origenes = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origenes, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])


@app.middleware("http")
async def cabeceras_seguras(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


# ---- endpoints ----------------------------------------------------------------
@app.get("/")
def root():
    return {"servicio": "LABOREA IA", "estado": "ok"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(models.SesionChat.__table__.select().limit(1))
    return {"estado": "ok", "ia": "gemini" if _IA.gemini.disponible else "reglas"}


@app.post("/api/sesion", dependencies=[Depends(_limitar(_lim_sesion))])
def crear_sesion(orq: Orquestador = Depends(get_orquestador)):
    return orq.crear_sesion()


@app.get("/api/sesion/{session_id}")
def ver_sesion(session_id: str, db: Session = Depends(get_db), orq: Orquestador = Depends(get_orquestador)):
    sesion = _sesion_o_404(db, session_id)
    mensajes = db.query(MensajeChat).filter(MensajeChat.id_sesion == session_id).order_by(MensajeChat.id_mensaje).all()
    perfil = sesion.perfil
    return {"session_id": session_id, "estado": sesion.estado, "paso": sesion.paso_perfil,
            "perfil": ({"puesto": perfil.puesto_deseado, "meta": perfil.meta_profesional, "proyectos": perfil.proyectos_destacar,
                        "id_puesto": perfil.id_puesto_base} if perfil else None),
            "mensajes": [{"rol": m.rol, "contenido": m.contenido} for m in mensajes],
            "analisis": orq.ultimo_resultado(sesion)}


@app.post("/api/chat", dependencies=[Depends(_limitar(_lim_chat))])
def chat(payload: ChatMensaje, db: Session = Depends(get_db), orq: Orquestador = Depends(get_orquestador)):
    sesion = _sesion_o_404(db, payload.session_id)
    return orq.procesar_mensaje(sesion, payload.message)


@app.post("/api/cv", dependencies=[Depends(_limitar(_lim_cv))])
def subir_cv(session_id: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db),
             orq: Orquestador = Depends(get_orquestador)):
    sesion = _sesion_o_404(db, session_id)
    contenido = file.file.read(MAX_BYTES + 1)   # se lee con tope: nunca se carga un archivo gigante en memoria
    try:
        out = orq.recibir_cv(sesion, file.filename or "cv", contenido)
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if out.get("error_cv"):
        return JSONResponse(status_code=422, content=out)   # HU-03: formato no permitido, se vuelve a pedir
    return out


@app.get("/api/analisis/{session_id}")
def ver_analisis(session_id: str, db: Session = Depends(get_db), orq: Orquestador = Depends(get_orquestador)):
    sesion = _sesion_o_404(db, session_id)
    resultado = orq.ultimo_resultado(sesion)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Todavía no hay un análisis. Subí tu CV primero.")
    return resultado


@app.get("/api/enlaces/{session_id}")
def ver_enlaces(session_id: str, db: Session = Depends(get_db), orq: Orquestador = Depends(get_orquestador)):
    sesion = _sesion_o_404(db, session_id)
    resultado = orq.ultimo_resultado(sesion)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Todavía no hay un análisis. Subí tu CV primero.")
    vistos, enlaces = set(), []
    for p in resultado["plan_estudio_json"]:
        r = p.get("recurso")
        if r and r["url"] not in vistos:
            vistos.add(r["url"])
            enlaces.append({**r, "para": p["habilidad"]})
    return {"enlaces": enlaces}


@app.delete("/api/sesion/{session_id}")
def borrar_sesion(session_id: str, db: Session = Depends(get_db)):
    sesion = _sesion_o_404(db, session_id)
    db.delete(sesion)
    db.commit()
    return {"estado": "borrada"}
