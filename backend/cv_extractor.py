"""
LABOREA IA - Validación y extracción de currículums (PDF o Word).

Flujo del diagrama: si el archivo no cumple el formato, se vuelve a pedir (HU-03).
Se valida por extensión Y por el contenido real del archivo (no alcanza con el nombre).
Soporta PDF, Word moderno (.docx) y Word binario clásico (.doc).
"""

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Tuple

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGINAS = 15
MIN_CARACTERES = 80   # menos que esto: probablemente un documento vacío o escaneado (solo imagen)


class CVInvalido(Exception):
    """El archivo no sirve; el mensaje se le muestra a la persona para que suba otro."""


@dataclass
class CVExtraido:
    formato: str
    texto: str
    metadatos: dict = field(default_factory=dict)


def _formato(nombre: str, contenido: bytes) -> str:
    ext = nombre.lower().rsplit(".", 1)[-1] if "." in nombre else ""
    
    # 1. PDF
    if ext == "pdf" or contenido.startswith(b"%PDF"):
        if contenido.startswith(b"%PDF"):
            return "pdf"
        raise CVInvalido("El archivo tiene extensión .pdf pero su contenido no es un PDF válido.")

    # 2. Word moderno (.docx): archivo ZIP con estructura WordprocessingML
    es_zip = contenido[:2] == b"PK" and zipfile.is_zipfile(io.BytesIO(contenido))
    if es_zip:
        try:
            with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                nombres = z.namelist()
                if any(n.startswith("word/") or n == "[Content_Types].xml" for n in nombres):
                    return "docx"
        except Exception:
            pass
        if ext == "docx":
            return "docx"

    if ext == "docx":
        raise CVInvalido("El archivo Word (.docx) parece estar dañado o no es un documento válido. Probá guardarlo de nuevo.")

    # 3. Word binario clásico (.doc OLE)
    es_ole_doc = contenido.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1") or ext == "doc"
    if es_ole_doc:
        return "doc"

    if ext in ("odt", "rtf", "txt", "jpg", "jpeg", "png", "pages"):
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
                imagenes += len(getattr(p, "images", [])) if hasattr(p, "images") else 1
        return texto, {"paginas": len(lector.pages), "imagenes": imagenes, "tablas": 0}
    except CVInvalido:
        raise
    except Exception as e:
        print("ERROR REAL AL LEER PDF:", repr(e))
        raise CVInvalido("El PDF parece estar dañado y no lo pude abrir. Probá exportarlo de nuevo.")


def _leer_docx(contenido: bytes) -> Tuple[str, dict]:
    import docx
    partes: List[str] = []
    tablas = 0
    imagenes = 0
    
    # 1. Extracción estructurada mediante python-docx
    try:
        d = docx.Document(io.BytesIO(contenido))
        for p in d.paragraphs:
            t = p.text.strip()
            if t:
                partes.append(t)
                
        try:
            for t in d.tables:
                tablas += 1
                for fila in t.rows:
                    celdas = [c.text.strip() for c in fila.cells if c.text.strip()]
                    if celdas:
                        celdas_unicas = []
                        for c in celdas:
                            if not celdas_unicas or c != celdas_unicas[-1]:
                                celdas_unicas.append(c)
                        if celdas_unicas:
                            partes.append(" | ".join(celdas_unicas))
        except Exception:
            pass
            
        try:
            for sec in d.sections:
                for hp in sec.header.paragraphs:
                    ht = hp.text.strip()
                    if ht and ht not in partes:
                        partes.insert(0, ht)
                for fp in sec.footer.paragraphs:
                    ft = fp.text.strip()
                    if ft and ft not in partes:
                        partes.append(ft)
        except Exception:
            pass
            
        try:
            imagenes = len(d.inline_shapes)
        except Exception:
            imagenes = 0
    except Exception:
        d = None

    # 2. Extracción profunda desde XML interno para cuadros de texto, formas y smart tags
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            if imagenes == 0:
                imagenes = len([n for n in z.namelist() if n.startswith("word/media/")])
            
            texto_actual = "\n".join(partes)
            if len(texto_actual.strip()) < MIN_CARACTERES:
                xml_textos = []
                for n in z.namelist():
                    if n == "word/document.xml" or n.startswith("word/header") or n.startswith("word/footer"):
                        try:
                            arbol = ET.fromstring(z.read(n))
                            if tablas == 0 and any(elem.tag.endswith("}tbl") for elem in arbol.iter()):
                                tablas += 1
                            for elem in arbol.iter():
                                if elem.tag.endswith("}t") and elem.text and elem.text.strip():
                                    xml_textos.append(elem.text.strip())
                        except Exception:
                            pass
                if xml_textos:
                    texto_xml = " ".join(xml_textos)
                    if len(texto_xml) > len(texto_actual):
                        partes = [texto_xml]
    except Exception:
        pass

    texto_final = "\n".join(partes).strip()
    if not texto_final:
        raise CVInvalido("El Word parece estar dañado y no lo pude abrir. Probá guardarlo de nuevo como .docx.")
    return texto_final, {"paginas": None, "imagenes": imagenes, "tablas": tablas}


def _leer_doc(contenido: bytes) -> Tuple[str, dict]:
    """Extrae texto de archivos Word en formato clásico .doc (Word 97-2003 OLE)."""
    partes: List[str] = []
    
    def tiene_palabras(txt: str) -> bool:
        return len(re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{2,}", txt)) >= 3
        
    # 1. Extraer secuencias UTF-16LE
    patron_utf16 = re.compile(b'(?:[\x20-\x7e\xa0-\xff]\x00){4,}')
    for m in patron_utf16.finditer(contenido):
        try:
            txt = m.group().decode('utf-16le').strip()
            if len(txt) >= 4 and tiene_palabras(txt):
                if not any(meta in txt for meta in ('Normal', 'Default Paragraph', 'Heading', 'Times New', 'Calibri', 'Arial', 'Symbol', 'Table Grid')):
                    partes.append(txt)
        except Exception:
            pass
            
    # 2. Si no hay suficiente texto, buscar secuencias ASCII / Latin-1
    if sum(len(p) for p in partes) < MIN_CARACTERES:
        patron_ascii = re.compile(b'[\x20-\x7e\xa0-\xff]{4,}')
        for m in patron_ascii.finditer(contenido):
            try:
                txt = m.group().decode('latin-1').strip()
                if len(txt) >= 4 and tiene_palabras(txt):
                    if not any(meta in txt for meta in ('Microsoft', 'WordDocument', 'CompObj', 'SummaryInformation', 'DocumentSummary', 'ObjectPool')):
                        partes.append(txt)
            except Exception:
                pass
                
    texto = "\n".join(partes).strip()
    if len(texto) < MIN_CARACTERES:
        raise CVInvalido("No se pudo extraer texto suficiente del archivo Word (.doc). Probá guardarlo como .docx o exportarlo a PDF.")
    return texto, {"paginas": None, "imagenes": 0, "tablas": 0}


def extraer_cv(nombre_archivo: str, contenido: bytes) -> CVExtraido:
    if not contenido:
        raise CVInvalido("El archivo llegó vacío. Subilo de nuevo.")
    if len(contenido) > MAX_BYTES:
        raise CVInvalido("El archivo pesa más de 5 MB. Probá con una versión más liviana.")
    formato = _formato(nombre_archivo or "", contenido)
    if formato == "pdf":
        texto, meta = _leer_pdf(contenido)
    elif formato == "docx":
        texto, meta = _leer_docx(contenido)
    elif formato == "doc":
        texto, meta = _leer_doc(contenido)
    else:
        raise CVInvalido("Formato no soportado.")
        
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
