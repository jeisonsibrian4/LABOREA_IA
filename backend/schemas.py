"""
LABOREA IA - Esquemas (Pydantic).

Parte 1: entrada de la API.
Parte 2: forma que se le pide a Gemini (esquema de respuesta JSON).
         Todos los campos son obligatorios porque así lo exige el esquema de Gemini;
         la validación estricta de lo que vuelve la hace orquestador.validar_diagnostico().
"""

from typing import List

from pydantic import BaseModel, Field

ID_SESION_PATRON = r"^[0-9a-f]{32}$"


# ---- API ------------------------------------------------------------------
class ChatMensaje(BaseModel):
    session_id: str = Field(pattern=ID_SESION_PATRON)
    message: str = Field(min_length=1, max_length=2000)


# ---- Respuesta pedida a Gemini --------------------------------------------
class EvidenciaIA(BaseModel):
    nombre: str
    evidencia: str


class ExperienciaIA(BaseModel):
    rol: str
    organizacion: str
    periodo: str
    resumen: str


class FaltanteIA(BaseModel):
    habilidad: str
    motivo: str


class PasoPlanIA(BaseModel):
    habilidad: str
    accion: str
    duracion_semanas: int


class DiagnosticoIA(BaseModel):
    hard_skills: List[EvidenciaIA]
    soft_skills: List[EvidenciaIA]
    experiencias: List[ExperienciaIA]
    faltantes: List[FaltanteIA]
    plan: List[PasoPlanIA]
    resumen: str
