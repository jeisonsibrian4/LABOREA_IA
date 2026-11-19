"""
LABOREA IA - Validación y extracción de currículums (PDF o Word).

Flujo del diagrama: si el archivo no cumple el formato, se vuelve a pedir (HU-03).
Se valida por extensión Y por el contenido real del archivo (no alcanza con el nombre).
"""

import io
import re
import zipfile
from dataclasses import dataclass, field
from typing import List, Tuple

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGINAS = 15
MIN_CARACTERES = 80   # menos que esto: probablemente un PDF escaneado (solo imagen)


class CVInvalido(Exception):
    """El archivo no sirve; el mensaje se le muestra a la persona para que suba otro."""


@dataclass
class CVExtraido:
    formato: str
    texto: str
    metadatos: dict = field(default_factory=dict)


def _formato(nombre: str, contenido: bytes) -> str:
    ext = nombre.lower().rsplit(".", 1)[-1] if "." in nombre else ""
    if ext == "pdf" and contenido.startswith(b"%PDF"):
        return "pdf"
    if ext == "docx" and contenido[:2] == b"PK" and zipfile.is_zipfile(io.BytesIO(contenido)):
        return "docx"
    if ext in ("doc", "odt", "rtf", "txt", "jpg", "jpeg", "png", "pages"):
        raise CVInvalido("Ese formato no lo puedo leer (.%s). Guardá tu CV como PDF o Word (.docx) y subilo de nuevo." % ext)
    raise CVInvalido("No pude reconocer el archivo como un PDF o un Word (.docx) válido. Probá exportarlo de nuevo y subilo otra vez.")


def _leer_pdf(contenido: bytes) -> Tuple[str, dict]:
    from pypdf import PdfReader
    try:
        lector = PdfReader(io.BytesIO(contenido))
        if lector.is_encrypted:
            raise CVInvalido("El PDF tiene contraseña. Subilo sin contraseña así lo puedo leer.")
        paginas = lector.pages[:MAX_PAGINAS]
        texto = "\n".join((p.extract_text() or "") for p in paginas)
        imagenes = 0
        for p in paginas:
            try:
                imagenes += len(list(p.images))
            except Exception:
                # Si una imagen interna tiene un formato que pypdf no decodifica, la contamos igual sin fallar
                imagenes += len(getattr(p, "images", [])) if hasattr(p, "images") else 1
        return texto, {"paginas": len(lector.pages), "imagenes": imagenes, "tablas": 0}
    except CVInvalido:
        raise
    except Exception as e:
        print("ERROR REAL AL LEER PDF:", repr(e))
        raise CVInvalido("El PDF parece estar dañado y no lo pude abrir. Probá exportarlo de nuevo.")

def _leer_docx(contenido: bytes) -> Tuple[str, dict]:
    import docx
    try:
        d = docx.Document(io.BytesIO(contenido))
    except Exception:
        raise CVInvalido("El Word parece estar dañado y no lo pude abrir. Probá guardarlo de nuevo como .docx.")
    partes: List[str] = [p.text for p in d.paragraphs if p.text.strip()]
    for t in d.tables:
        for fila in t.rows:
            celdas = [c.text.strip() for c in fila.cells if c.text.strip()]
            if celdas:
                partes.append(" | ".join(celdas))
    return "\n".join(partes), {"paginas": None, "imagenes": len(d.inline_shapes), "tablas": len(d.tables)}


def extraer_cv(nombre_archivo: str, contenido: bytes) -> CVExtraido:
    if not contenido:
        raise CVInvalido("El archivo llegó vacío. Subilo de nuevo.")
    if len(contenido) > MAX_BYTES:
        raise CVInvalido("El archivo pesa más de 5 MB. Probá con una versión más liviana.")
    formato = _formato(nombre_archivo or "", contenido)
    texto, meta = _leer_pdf(contenido) if formato == "pdf" else _leer_docx(contenido)
    texto = re.sub(r"[ \t]+", " ", texto).strip()
    if len(texto) < MIN_CARACTERES:
        raise CVInvalido("No encontré texto en el archivo (¿es una foto o un PDF escaneado?). "
                         "Subí una versión con texto seleccionable, exportada desde Word o Google Docs.")
    return CVExtraido(formato=formato, texto=texto[:30000], metadatos=meta)


def detectar_problemas_ats(cv: CVExtraido) -> List[str]:
    """Errores comunes que hacen que un sistema de filtrado automático (ATS) descarte un CV."""
    problemas: List[str] = []
    m = cv.metadatos
    if m.get("tablas"):
        problemas.append("Tiene tablas: muchos sistemas automáticos las leen desordenadas. Usá títulos y viñetas simples.")
    if (m.get("imagenes") or 0) > 0:
        problemas.append("Tiene imágenes o íconos gráficos: el sistema no puede leerlos. Usá texto para los datos importantes.")
    if not re.search(r"(?:19|20)\d{2}", cv.texto):
        problemas.append("No encontré fechas: agregá años o rangos (ej. 2022 - 2024) en cada experiencia y estudio.")
    if not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", cv.texto):
        problemas.append("No encontré un email de contacto visible en el texto.")
    if len(cv.texto) < 400:
        problemas.append("El CV es muy corto: sumá logros concretos y las herramientas que usaste.")
    if (m.get("paginas") or 0) > 2:
        problemas.append("Tiene más de 2 páginas: para un perfil junior conviene que entre en 1 o 2.")
    return problemas
