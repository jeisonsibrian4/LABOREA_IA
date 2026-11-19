"""Configuración de las pruebas: base SQLite temporal y SIN clave de Gemini (modo reglas)."""
import io
import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="laborea_test_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TMP, "test.db")
os.environ["GEMINI_API_KEY"] = ""
os.environ["LIMITE_SESIONES_HORA"] = "10000"
os.environ["LIMITE_CHAT_HORA"] = "10000"
os.environ["LIMITE_CV_HORA"] = "10000"
os.environ["RETENCION_DIAS"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

CV_TEXTO = [
    "Lucía Pérez - Desarrolladora web",
    "lucia.perez@example.com",
    "Experiencia",
    "2023 - 2024 Proyecto freelance: sitio para un comercio barrial con HTML, CSS y JavaScript.",
    "2022 - 2023 Curso intensivo de programación web. Trabajo en equipo con GitHub y Git.",
    "Habilidades: HTML5, CSS3, JavaScript, React, Git, GitHub, diseño responsive.",
    "Soy autodidacta y me gusta la resolución de problemas y la comunicación con el cliente.",
    "Estudios: Tecnicatura en Programación 2021 - 2023.",
    "Idiomas: Inglés intermedio. Disponibilidad full time en CABA y GBA, con ganas de crecer.",
]


def hacer_pdf(lineas=CV_TEXTO) -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for linea in lineas:
        c.drawString(40, y, linea)
        y -= 18
    c.save()
    return buf.getvalue()


def hacer_docx(lineas=CV_TEXTO, con_tabla=False) -> bytes:
    import docx
    d = docx.Document()
    for linea in lineas:
        d.add_paragraph(linea)
    if con_tabla:
        t = d.add_table(rows=1, cols=2)
        t.rows[0].cells[0].text = "Skill"
        t.rows[0].cells[1].text = "Nivel"
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


@pytest.fixture(scope="session")
def app_main():
    import main
    return main


@pytest.fixture()
def client(app_main):
    with TestClient(app_main.app) as c:
        yield c


def avanzar_perfil(client, puesto="Quiero ser desarrolladora frontend"):
    """Crea una sesión y responde las 3 preguntas. Devuelve el session_id."""
    sid = client.post("/api/sesion").json()["session_id"]
    for texto in (puesto, "Conseguir mi primer trabajo junior en tecnología",
                  "Hice una página para el negocio de mi tía y trabajé con Docker en un curso"):
        r = client.post("/api/chat", json={"session_id": sid, "message": texto})
        assert r.status_code == 200, r.text
    return sid
