"""
LABOREA IA - Recuperación documental (RAG) del contexto de mercado.

Hace dos cosas con la base data/mercado_laboral.json:
  1. buscar_puesto(texto): reconoce a qué puesto se refiere la persona (TF-IDF + coseno).
  2. detectar_skills(texto, puesto): qué habilidades del puesto aparecen en un texto.

Es una versión simple, sin dependencias externas ("base vectorizada" liviana).
Para un RAG con embeddings (Gemini Embeddings, pgvector, etc.) se reemplaza solo esta clase:
el resto de la app usa únicamente los métodos públicos de Recuperador.
"""

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

RUTA_BASE = Path(__file__).resolve().parent / "data" / "mercado_laboral.json"
_STOPWORDS = {"de", "del", "la", "el", "los", "las", "un", "una", "y", "o", "en", "para", "por", "con",
              "a", "al", "que", "me", "mi", "quiero", "busco", "puesto", "trabajo", "trabajar", "como",
              "area", "junior", "jr", "ssr", "senior", "estoy", "soy", "ser", "ejemplo", "postularme",
              "postular", "empleo", "laburo", "algo", "tipo", "relacionado", "relacionada"}


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos (para comparar 'Comunicación' con 'comunicacion')."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _tokens(texto: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9+#]+", normalizar(texto)) if t not in _STOPWORDS and len(t) > 1]


def _patron_alias(alias: str) -> re.Pattern:
    """Coincidencia de palabra completa ('css' no coincide dentro de 'tailwindcss')."""
    return re.compile(r"(?<![a-z0-9])" + re.escape(normalizar(alias)) + r"(?![a-z0-9])")


class Recuperador:
    def __init__(self, ruta: Path = RUTA_BASE) -> None:
        with open(ruta, encoding="utf-8") as f:
            self.base: dict = json.load(f)
        self.puestos: List[dict] = self.base["puestos"]
        self.recursos: Dict[str, dict] = self.base["recursos"]
        self.soft: List[dict] = self.base["soft_skills"]
        self._indexar()

    # -- índice TF-IDF ----------------------------------------------------
    def _indexar(self) -> None:
        pesos: List[Counter] = []
        for p in self.puestos:
            c: Counter = Counter()
            for t in _tokens(p["titulo"]):
                c[t] += 2
            for a in p["alias"]:
                for t in _tokens(a):
                    c[t] += 3
            for h in p["hard_skills"]:
                for t in _tokens(h["nombre"]):
                    c[t] += 1
            pesos.append(c)
        n = len(self.puestos)
        df: Counter = Counter()
        for c in pesos:
            df.update(c.keys())
        self._idf = {t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()}
        self._vectores: List[Dict[str, float]] = []
        for c in pesos:
            v = {t: w * self._idf[t] for t, w in c.items()}
            norma = math.sqrt(sum(x * x for x in v.values())) or 1.0
            self._vectores.append({t: x / norma for t, x in v.items()})

    # -- API pública --------------------------------------------------------
    def listar_puestos(self) -> List[str]:
        return [p["titulo"] for p in self.puestos]

    def puesto_por_id(self, id_puesto: str) -> Optional[dict]:
        return next((p for p in self.puestos if p["id"] == id_puesto), None)

    def buscar_puesto(self, texto: str, minimo: float = 0.15) -> Tuple[Optional[dict], float]:
        """Devuelve (puesto, similitud). Si nada se parece lo suficiente: (None, similitud)."""
        q = Counter(t for t in _tokens(texto) if t in self._idf)
        if not q:
            return None, 0.0
        vq = {t: w * self._idf[t] for t, w in q.items()}
        norma = math.sqrt(sum(x * x for x in vq.values())) or 1.0
        mejor, mejor_s = None, 0.0
        for p, v in zip(self.puestos, self._vectores):
            s = sum(vq[t] / norma * v.get(t, 0.0) for t in vq)
            if s > mejor_s:
                mejor, mejor_s = p, s
        return (mejor, mejor_s) if mejor_s >= minimo else (None, mejor_s)

    def detectar_skills(self, texto: str, skills: List[dict]) -> Dict[str, str]:
        """{nombre_skill: evidencia} para las skills cuyo alias aparece en el texto.
        La evidencia es la línea del texto donde aparece (máx. 140 caracteres)."""
        lineas = [(l.strip(), normalizar(l)) for l in re.split(r"[\n\r]+", texto) if l.strip()]
        encontradas: Dict[str, str] = {}
        for s in skills:
            patrones = [_patron_alias(a) for a in s["alias"]]
            for original, norm in lineas:
                if any(p.search(norm) for p in patrones):
                    encontradas[s["nombre"]] = original[:140]
                    break
        return encontradas

    def recurso(self, id_recurso: Optional[str]) -> Optional[dict]:
        r = self.recursos.get(id_recurso or "")
        return {"nombre": r["nombre"], "url": r["url"], "descripcion": r["descripcion"]} if r else None

    def obtener_recursos(self, skill: dict) -> List[dict]:
        """Devuelve la lista de recursos (1 o más) asociados a una habilidad para que el usuario pueda elegir."""
        ids: List[str] = []
        if "recursos" in skill and isinstance(skill["recursos"], list):
            for item in skill["recursos"]:
                if isinstance(item, str) and item not in ids:
                    ids.append(item)
        if "recurso" in skill and isinstance(skill["recurso"], str) and skill["recurso"]:
            if skill["recurso"] not in ids:
                ids.insert(0, skill["recurso"])

        resultado: List[dict] = []
        for rid in ids:
            rec = self.recurso(rid)
            if rec and rec not in resultado:
                resultado.append(rec)
        return resultado

    def urls_permitidas(self) -> set:
        return {r["url"] for r in self.recursos.values()}
