"""
LABOREA IA - Modelos (tablas del diagrama de integración).

SESION_CHAT      -> SesionChat      (HU-01 / HU-07)
PERFIL_OBJETIVO  -> PerfilObjetivo  (HU-01)
DOCUMENTO_CV     -> DocumentoCV     (HU-02 / HU-03)
ANALISIS_IA      -> AnalisisIA      (HU-04 / HU-05)
MENSAJE_CHAT     -> MensajeChat     (HU-07, memoria de la conversación; tabla agregada)
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class SesionChat(Base):
    __tablename__ = "sesion_chat"

    id_sesion: Mapped[str] = mapped_column(String(32), primary_key=True)
    estado: Mapped[str] = mapped_column(String(20), default="perfilamiento")  # perfilamiento | esperando_cv | analizado
    paso_perfil: Mapped[int] = mapped_column(Integer, default=0)  # cuántas de las 3 preguntas ya se respondieron
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    creada: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    ultima_actividad: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora, onupdate=_ahora)

    perfil = relationship("PerfilObjetivo", back_populates="sesion", uselist=False, cascade="all, delete-orphan")
    documentos = relationship("DocumentoCV", back_populates="sesion", cascade="all, delete-orphan")
    analisis = relationship("AnalisisIA", back_populates="sesion", cascade="all, delete-orphan")
    mensajes = relationship("MensajeChat", back_populates="sesion", cascade="all, delete-orphan",
                            order_by="MensajeChat.id_mensaje")


class PerfilObjetivo(Base):
    __tablename__ = "perfil_objetivo"

    id_perfil: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_sesion: Mapped[str] = mapped_column(ForeignKey("sesion_chat.id_sesion", ondelete="CASCADE"), unique=True)
    puesto_deseado: Mapped[str | None] = mapped_column(String(200))   # pregunta 1
    meta_profesional: Mapped[str | None] = mapped_column(Text)        # pregunta 2
    proyectos_destacar: Mapped[str | None] = mapped_column(Text)      # pregunta 3
    id_puesto_base: Mapped[str | None] = mapped_column(String(60))    # puesto reconocido en la base de mercado
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    sesion = relationship("SesionChat", back_populates="perfil")


class DocumentoCV(Base):
    __tablename__ = "documento_cv"

    id_cv: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_sesion: Mapped[str] = mapped_column(ForeignKey("sesion_chat.id_sesion", ondelete="CASCADE"), index=True)
    nombre_archivo: Mapped[str] = mapped_column(String(255))
    formato: Mapped[str] = mapped_column(String(10))                  # pdf | docx
    tamano_bytes: Mapped[int] = mapped_column(Integer)
    texto_extraido: Mapped[str] = mapped_column(Text)
    metadatos: Mapped[dict | None] = mapped_column(JSON)              # páginas, tablas, imágenes
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    sesion = relationship("SesionChat", back_populates="documentos")


class AnalisisIA(Base):
    __tablename__ = "analisis_ia"

    id_analisis: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_sesion: Mapped[str] = mapped_column(ForeignKey("sesion_chat.id_sesion", ondelete="CASCADE"), index=True)
    id_cv: Mapped[int] = mapped_column(ForeignKey("documento_cv.id_cv", ondelete="CASCADE"))
    id_puesto_base: Mapped[str] = mapped_column(String(60))
    match_score: Mapped[float] = mapped_column(Float)
    skills_gap: Mapped[list] = mapped_column(JSON)                    # habilidades que faltan
    plan_estudio_json: Mapped[list] = mapped_column(JSON)             # plan de estudio personalizado
    resultado_json: Mapped[dict] = mapped_column(JSON)                # diagnóstico completo (hard/soft skills, experiencias, ATS...)
    modo: Mapped[str] = mapped_column(String(10))                     # gemini | reglas
    modelo: Mapped[str | None] = mapped_column(String(60))
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    sesion = relationship("SesionChat", back_populates="analisis")


class MensajeChat(Base):
    __tablename__ = "mensaje_chat"

    id_mensaje: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_sesion: Mapped[str] = mapped_column(ForeignKey("sesion_chat.id_sesion", ondelete="CASCADE"), index=True)
    rol: Mapped[str] = mapped_column(String(10))                      # user | bot
    contenido: Mapped[str] = mapped_column(Text)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    sesion = relationship("SesionChat", back_populates="mensajes")
