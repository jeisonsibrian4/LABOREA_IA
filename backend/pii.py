"""
LABOREA IA - Privacidad de datos (gobernanza ética de datos).

- enmascarar_pii: tapa email, teléfono, DNI/CUIL y tarjetas ANTES de mandar texto a Gemini.
- detectar_datos_sensibles: en el chat, avisa si alguien pega una tarjeta, una clave o un DNI.
"""

import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CUIL = re.compile(r"\b\d{2}-?\d{8}-?\d\b")
_TARJETA = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_DNI = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}\b")
_TELEFONO = re.compile(r"(?<!\w)(?:\+?54[ -]?)?(?:9[ -]?)?(?:\(?\d{2,4}\)?[ -]?)\d{3,4}[ -]?\d{4}(?!\w)")
_CLAVE = re.compile(r"\b(contraseña|contrasena|password|clave)\s*(es|:|=)", re.I)


def enmascarar_pii(texto: str) -> str:
    """Reemplaza datos personales por marcadores. No toca años ni rangos de fechas."""
    texto = _EMAIL.sub("[EMAIL]", texto)
    texto = _CUIL.sub("[DOCUMENTO]", texto)
    texto = _TARJETA.sub("[NUMERO]", texto)
    texto = _DNI.sub("[DOCUMENTO]", texto)
    texto = _TELEFONO.sub("[TELEFONO]", texto)
    return texto


def detectar_datos_sensibles(texto: str) -> bool:
    """True si el mensaje trae algo que no debería guardarse ni procesarse (tarjeta, clave, DNI/CUIL)."""
    return bool(_TARJETA.search(texto) or _CLAVE.search(texto) or _CUIL.search(texto) or _DNI.search(texto))
