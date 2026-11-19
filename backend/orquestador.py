"""
LABOREA IA - Orquestador del backend y componente de IA (diagrama de integración, Etapa 5).

Flujo y dónde vive cada etapa:
  1. Inicia la conversación (SESION_CHAT)        -> Orquestador.crear_sesion()
  2. Perfilamiento: 3 preguntas (PERFIL_OBJETIVO) -> Orquestador._perfilar()
  3. Recibe el CV y valida el formato (HU-03)     -> Orquestador.recibir_cv() + cv_extractor
  4. Extrae y guarda el texto (DOCUMENTO_CV)      -> Orquestador.recibir_cv()
  5. Recupera contexto de mercado (RAG)           -> rag.Recuperador
  6. Llama a Gemini con prompts y contexto        -> ComponenteIA.diagnosticar() -> gemini_service
  7. Valida la respuesta de la IA                 -> validar_diagnostico()
  8. Guarda (ANALISIS_IA) y muestra en el chat    -> Orquestador._analizar()
  9. Asesoría en tiempo real sobre el diagnóstico -> ComponenteIA.asesorar()

El componente que llama a Gemini es el backend (este orquestador). La IA nunca accede a la base
de datos: solo recibe lo que el backend le manda, y todo lo que devuelve se valida antes de usarse.
Sin clave de Gemini (o sin cuota) todo funciona igual en "modo reglas".
"""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from cv_extractor import CVExtraido, CVInvalido, detectar_problemas_ats, extraer_cv
from gemini_service import SISTEMA_ASESOR, SISTEMA_DIAGNOSTICO, IANoDisponible, ServicioGemini
from models import AnalisisIA, DocumentoCV, MensajeChat, PerfilObjetivo, SesionChat
from pii import detectar_datos_sensibles, enmascarar_pii
from rag import Recuperador, normalizar
from schemas import DiagnosticoIA

log = logging.getLogger("laborea")

AVISO_PUNTAJE = "El puntaje es una estimación orientativa según requisitos generales del mercado; no garantiza ni descarta una contratación."

PREGUNTAS = [
    "¿A qué puesto o área técnica querés postularte prioritariamente?",
    "¿Cuál es tu meta profesional a corto o mediano plazo? (por ejemplo: conseguir tu primer puesto junior o cambiar de industria)",
    "¿Qué proyectos personales, académicos o experiencia informal querés destacar y que todavía no figuran en tu CV?",
]

SALUDO = ("¡Hola! Soy Laborea IA y estoy acá para acompañarte, sin juicios y sin costo. "
          "Te voy a hacer 3 preguntas cortas para conocerte mejor y después analizamos tu CV juntos.\n\n")

MSG_PEDIR_CV = ("¡Gracias por contarme todo eso! Ahora necesito tu currículum en PDF o Word (.docx). "
                "Tocá el clip 📎 del chat (o la sección «Mi CV») para subirlo.")


def _importancia(peso: int) -> str:
    return "alta" if peso >= 3 else "media" if peso == 2 else "baja"


# =========================================================================
# Validación de lo que devuelve la IA (etapa 7)
# =========================================================================
def _txt(valor: Any, maximo: int) -> str:
    return valor.strip()[:maximo] if isinstance(valor, str) else ""


def validar_diagnostico(crudo: Any) -> Dict[str, Any]:
    """Filtra la salida de Gemini: tipos correctos, textos acotados, listas con tope.
    Lo que no cumple se descarta; nunca se confía en el modelo para campos numéricos críticos."""
    if not isinstance(crudo, dict):
        raise IANoDisponible("La IA no devolvió un objeto JSON")

    def lista(clave: str, tope: int) -> list:
        v = crudo.get(clave)
        return [x for x in v if isinstance(x, dict)][:tope] if isinstance(v, list) else []

    hard = [{"nombre": _txt(x.get("nombre"), 80), "evidencia": _txt(x.get("evidencia"), 160)} for x in lista("hard_skills", 30)]
    soft = [{"nombre": _txt(x.get("nombre"), 80), "evidencia": _txt(x.get("evidencia"), 160)} for x in lista("soft_skills", 15)]
    exp = [{"rol": _txt(x.get("rol"), 100), "organizacion": _txt(x.get("organizacion"), 100),
            "periodo": _txt(x.get("periodo"), 40), "resumen": _txt(x.get("resumen"), 240)} for x in lista("experiencias", 8)]
    falt = [{"habilidad": _txt(x.get("habilidad"), 80), "motivo": _txt(x.get("motivo"), 200)} for x in lista("faltantes", 15)]
    plan = []
    for x in lista("plan", 8):
        try:
            sem = max(1, min(26, int(x.get("duracion_semanas", 0))))
        except (TypeError, ValueError):
            sem = 0
        plan.append({"habilidad": _txt(x.get("habilidad"), 80), "accion": _txt(x.get("accion"), 240), "duracion_semanas": sem})
    return {
        "hard_skills": [x for x in hard if x["nombre"]],
        "soft_skills": [x for x in soft if x["nombre"]],
        "experiencias": [x for x in exp if x["rol"] or x["resumen"]],
        "faltantes": [x for x in falt if x["habilidad"]],
        "plan": [x for x in plan if x["habilidad"] and x["accion"]],
        "resumen": _txt(crudo.get("resumen"), 600),
    }


def sanear_urls(texto: str, permitidas: set) -> str:
    """Anti-invención: cualquier enlace que no esté en la base se reemplaza (la IA no puede inventar links)."""
    def _reemplazo(m: "re.Match") -> str:
        url = m.group(0).rstrip(".,;)")
        return m.group(0) if url in permitidas else "[enlace no verificado]"
    return re.sub(r"https?://\S+", _reemplazo, texto)


# =========================================================================
# Componente de IA: interpreta y redacta. Nunca consulta la base de datos.
# =========================================================================
class ComponenteIA:
    def __init__(self, gemini: Optional[ServicioGemini] = None) -> None:
        self.gemini = gemini or ServicioGemini()

    def diagnosticar(self, perfil: PerfilObjetivo, texto_cv: str, puesto: dict) -> Dict[str, Any]:
        """Etapa 6: Gemini recibe perfil + CV (sin datos personales) + requisitos del mercado."""
        contexto = {
            "puesto": puesto["titulo"],
            "habilidades_requeridas": [h["nombre"] for h in puesto["hard_skills"]],
        }
        prompt = (
            "Analizá el CV para el puesto indicado y devolvé el diagnóstico en el JSON pedido.\n"
            "En 'plan' proponé hasta 5 pasos, uno por cada habilidad requerida que falte, con una acción concreta y gratuita "
            "(sin enlaces) y una duración estimada en semanas.\n"
            "<contexto_mercado>%s</contexto_mercado>\n"
            "<perfil>\nPuesto deseado: %s\nMeta: %s\nProyectos a destacar: %s\n</perfil>\n"
            "<cv>\n%s\n</cv>"
        ) % (json.dumps(contexto, ensure_ascii=False),
             perfil.puesto_deseado or "", perfil.meta_profesional or "", perfil.proyectos_destacar or "",
             enmascarar_pii(texto_cv)[:12000])
        salida = self.gemini.generar(prompt, sistema=SISTEMA_DIAGNOSTICO, esquema=DiagnosticoIA, temperatura=0.2)
        try:
            return validar_diagnostico(json.loads(re.sub(r"^```(?:json)?|```$", "", salida, flags=re.M).strip()))
        except json.JSONDecodeError:
            raise IANoDisponible("JSON inválido")

    def asesorar(self, pregunta: str, resultado: dict, historial: List[MensajeChat], urls: set) -> str:
        """Etapa 9: responde dudas sobre el diagnóstico (con Gemini si hay; si no, por reglas)."""
        if self.gemini.disponible:
            try:
                recursos = [p["recurso"] for p in resultado["plan_estudio_json"] if p.get("recurso")]
                ctx = {"puesto": resultado["puesto"]["titulo"], "puntaje": resultado["match_score"],
                       "compatibles": resultado["compatibles"], "faltan": [g["habilidad"] for g in resultado["skills_gap"]],
                       "plan": [{k: p[k] for k in ("orden", "habilidad", "accion", "duracion_semanas")} for p in resultado["plan_estudio_json"]],
                       "recursos_gratuitos": recursos, "problemas_cv": resultado["problemas_ats"]}
                previo = "\n".join("%s: %s" % ("Persona" if m.rol == "user" else "Laborea", m.contenido[:300]) for m in historial[-6:])
                prompt = ("<diagnostico>%s</diagnostico>\n<conversacion_previa>\n%s\n</conversacion_previa>\n<pregunta>%s</pregunta>"
                          % (json.dumps(ctx, ensure_ascii=False), previo, pregunta[:1000]))
                texto = self.gemini.generar(prompt, sistema=SISTEMA_ASESOR, temperatura=0.4)
                return sanear_urls(texto, urls)[:1500]
            except IANoDisponible:
                pass
        return _asesoria_reglas(pregunta, resultado)


# =========================================================================
# Asesoría y mensajes en modo reglas
# =========================================================================
def _lista_humana(items: List[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return "—"
    return ", ".join(items[:-1]) + " y " + items[-1] if len(items) > 1 else items[0]


def _texto_enlaces(resultado: dict) -> str:
    vistos, lineas = set(), []
    for p in resultado["plan_estudio_json"]:
        r = p.get("recurso")
        if r and r["url"] not in vistos:
            vistos.add(r["url"])
            lineas.append("• %s (para %s): %s" % (r["nombre"], p["habilidad"], r["url"]))
    if not lineas:
        return "Por ahora no tengo enlaces cargados para tu plan."
    return "Estos recursos gratuitos te pueden servir:\n" + "\n".join(lineas) + "\n\nRevisá siempre que estén vigentes antes de empezar."


def _asesoria_reglas(pregunta: str, r: dict) -> str:
    q = normalizar(pregunta)
    if re.search(r"enlace|link|curso|academia|instituto|recurso|donde estudi|donde aprend", q):
        return _texto_enlaces(r)
    if re.search(r"postul", q):
        return ("Todavía no tengo el agente de postulaciones en esta versión. Mientras tanto, usá tu plan de estudio y "
                "las mejoras al CV para llegar más fuerte a cada postulación.")
    if re.search(r"puntaje|match|score|porcentaje|chance|probabilidad|coincidencia", q):
        return "Tu coincidencia estimada es %d%%. %s" % (r["match_score"], AVISO_PUNTAJE)
    if re.search(r"entrevist|simulador|practic", q):
        fuerte = _lista_humana(r["compatibles"][:2]) or "tus proyectos"
        falta = r["skills_gap"][0]["habilidad"] if r["skills_gap"] else ""
        consejos = ["Para prepararte para la entrevista de «%s»:" % r["puesto"]["titulo"],
                    "1. Elegí un ejemplo real de %s: qué problema había, qué hiciste vos y cómo terminó." % fuerte,
                    "2. Practicá en voz alta una presentación tuya de 1 minuto: quién sos, qué sabés hacer y qué buscás."]
        if falta:
            consejos.append("3. Si te preguntan por %s, contá con honestidad que lo estás estudiando y cuál es tu plan." % falta)
        consejos.append("%d. Llevá 2 preguntas para hacerle a la empresa (equipo, forma de trabajo, aprendizaje)." % (4 if falta else 3))
        consejos.append("Todavía no tengo el simulador de entrevistas en esta versión; mientras tanto, practicá con alguien de confianza.")
        return "\n".join(consejos)
    if re.search(r"plan|estudi|aprender|empez|por donde", q):
        pasos = ["%d. %s — %s (unas %d semanas)" % (p["orden"], p["habilidad"], p["accion"], p["duracion_semanas"]) for p in r["plan_estudio_json"]]
        return "Este es tu plan, en orden de prioridad:\n" + "\n".join(pasos) if pasos else "¡No encontré brechas importantes para este puesto! Podés empezar a postularte."
    if re.search(r"falta|brecha|skill|habilidad|mejorar|desarroll", q):
        faltan = [g["habilidad"] for g in r["skills_gap"]]
        return ("Las habilidades que más conviene desarrollar son: %s." % _lista_humana(faltan[:5])) if faltan else "No veo habilidades importantes pendientes para este puesto."
    if re.search(r"\bcv\b|curriculum|formato|ats|filtro", q):
        if r["problemas_ats"]:
            return "Para que tu CV pase mejor los filtros automáticos:\n" + "\n".join("• " + p for p in r["problemas_ats"])
        return "No detecté problemas de formato importantes en tu CV. ¡Buen trabajo!"
    return ("Puedo contarte tu puntaje, las habilidades que te faltan, tu plan de estudio paso a paso, "
            "enlaces gratuitos para estudiar o cómo mejorar el formato de tu CV. ¿Qué te gustaría ver primero?")


def mensaje_diagnostico(r: dict) -> str:
    partes = ["Listo, ya analicé tu CV para «%s». Tu coincidencia estimada es del %d%%. %s" % (r["puesto"]["titulo"], r["match_score"], AVISO_PUNTAJE)]
    if r["resumen"]:
        partes.append(r["resumen"])
    partes.append("Ya tenés: %s." % _lista_humana(r["compatibles"][:6]) if r["compatibles"] else "Todavía no vi habilidades técnicas del puesto en tu CV, y está bien: para eso armamos un plan.")
    if r["skills_gap"]:
        partes.append("Conviene desarrollar: %s." % _lista_humana([g["habilidad"] for g in r["skills_gap"][:5]]))
    if r["fortalezas_no_en_cv"]:
        partes.append("Me contaste que usaste %s, pero no figura en tu CV: sumalo, ¡es una fortaleza!" % _lista_humana(r["fortalezas_no_en_cv"][:4]))
    partes.append("Podés preguntarme por tu plan de estudio, por enlaces gratuitos o por cómo mejorar tu CV.")
    return "\n\n".join(partes)


# =========================================================================
# Orquestador
# =========================================================================
class Orquestador:
    def __init__(self, db: Session, ia: ComponenteIA, recuperador: Recuperador) -> None:
        self.db, self.ia, self.rag = db, ia, recuperador

    # -- utilidades -------------------------------------------------------
    def _guardar(self, sesion: SesionChat, rol: str, texto: str) -> None:
        self.db.add(MensajeChat(id_sesion=sesion.id_sesion, rol=rol, contenido=texto))
        sesion.ultima_actividad = datetime.now(timezone.utc)   # la retención se cuenta desde la última actividad real

    def _respuesta(self, sesion: SesionChat, texto: str, **extra: Any) -> Dict[str, Any]:
        self._guardar(sesion, "bot", texto)
        self.db.commit()
        return {"response": texto, "estado": sesion.estado, "paso": sesion.paso_perfil, **extra}

    # -- etapa 1 ---------------------------------------------------------
    def crear_sesion(self) -> Dict[str, Any]:
        sesion = SesionChat(id_sesion=uuid.uuid4().hex)
        self.db.add(sesion)
        self.db.flush()
        out = self._respuesta(sesion, SALUDO + PREGUNTAS[0])
        out["session_id"] = sesion.id_sesion
        return out

    # -- chat ------------------------------------------------------------
    def procesar_mensaje(self, sesion: SesionChat, texto: str, urls: Optional[set] = None) -> Dict[str, Any]:
        if detectar_datos_sensibles(texto):
            return {"response": "Por tu seguridad, no compartas documentos, tarjetas ni contraseñas por acá: no los necesito y no los guardo. "
                                "Contame lo que te pedí sin esos datos, por favor.",
                    "estado": sesion.estado, "paso": sesion.paso_perfil}
        texto = enmascarar_pii(texto.strip())
        self._guardar(sesion, "user", texto)
        if sesion.estado == "perfilamiento":
            return self._perfilar(sesion, texto)
        if sesion.estado == "esperando_cv":
            return self._respuesta(sesion, "Para seguir necesito tu CV en PDF o Word (.docx). Tocá el clip 📎 o entrá a «Mi CV». Si tenés dudas sobre el archivo, contame.")
        resultado = self._ultimo_resultado(sesion)
        if resultado is None:
            return self._respuesta(sesion, MSG_PEDIR_CV)
        historial = self.db.query(MensajeChat).filter(MensajeChat.id_sesion == sesion.id_sesion).order_by(MensajeChat.id_mensaje).all()
        return self._respuesta(sesion, self.ia.asesorar(texto, resultado, historial[:-1], urls or self.rag.urls_permitidas()))

    # -- etapa 2 ---------------------------------------------------------
    def _perfilar(self, sesion: SesionChat, texto: str) -> Dict[str, Any]:
        paso = sesion.paso_perfil
        perfil = sesion.perfil
        if paso == 0:
            puesto, _ = self.rag.buscar_puesto(texto)
            if puesto is None:
                return self._respuesta(sesion, "Todavía no tengo requisitos cargados para ese puesto. Hoy puedo ayudarte con: %s. "
                                       "¿Cuál se parece más a lo que buscás?" % _lista_humana(self.rag.listar_puestos()))
            perfil = PerfilObjetivo(puesto_deseado=texto[:200], id_puesto_base=puesto["id"])
            sesion.perfil = perfil
        elif paso == 1:
            perfil.meta_profesional = texto
        else:
            perfil.proyectos_destacar = texto
        sesion.paso_perfil = paso + 1
        if sesion.paso_perfil >= len(PREGUNTAS):
            sesion.estado = "esperando_cv"
            return self._respuesta(sesion, MSG_PEDIR_CV)
        extra = ""
        if paso == 0:
            extra = "Perfecto, tomo «%s» como objetivo. " % self.rag.puesto_por_id(perfil.id_puesto_base)["titulo"]
        return self._respuesta(sesion, extra + PREGUNTAS[sesion.paso_perfil])

    # -- etapas 3 y 4 ----------------------------------------------------
    def recibir_cv(self, sesion: SesionChat, nombre: str, contenido: bytes) -> Dict[str, Any]:
        if sesion.estado == "perfilamiento":
            raise PermissionError("Primero respondé las 3 preguntas del perfil y después subí tu CV.")
        try:
            cv = extraer_cv(nombre, contenido)
        except CVInvalido as e:
            # HU-03: error de validación y se vuelve a pedir un documento compatible
            out = self._respuesta(sesion, "%s" % e)
            out["error_cv"] = True
            return out
        fila = DocumentoCV(id_sesion=sesion.id_sesion, nombre_archivo=(nombre or "cv")[:255], formato=cv.formato,
                           tamano_bytes=len(contenido), texto_extraido=cv.texto, metadatos=cv.metadatos)
        self.db.add(fila)
        self.db.flush()
        self._guardar(sesion, "user", "📎 CV adjuntado: %s" % (nombre or "cv")[:120])
        return self._analizar(sesion, fila, cv)

    # -- etapas 5 a 8 ----------------------------------------------------
    def _analizar(self, sesion: SesionChat, fila_cv: DocumentoCV, cv: CVExtraido) -> Dict[str, Any]:
        perfil = sesion.perfil
        puesto = self.rag.puesto_por_id(perfil.id_puesto_base)
        # 5. Contexto de mercado y detección por reglas (siempre se hace: es la base auditable del puntaje)
        det = self.rag.detectar_skills(cv.texto, puesto["hard_skills"])
        det_soft = self.rag.detectar_skills(cv.texto, self.rag.soft)
        en_perfil = self.rag.detectar_skills(" ".join([perfil.meta_profesional or "", perfil.proyectos_destacar or ""]), puesto["hard_skills"])
        problemas = detectar_problemas_ats(cv)
        # 6 y 7. Gemini (validado) o modo reglas
        ia: Optional[dict] = None
        modo, modelo = "reglas", None
        try:
            ia = self.ia.diagnosticar(perfil, cv.texto, puesto)
            modo, modelo = "gemini", self.ia.gemini.modelo
        except IANoDisponible as e:
            log.info("Diagnóstico en modo reglas (%s)", e)
        hard_ev = dict(det)
        soft_ev = dict(det_soft)
        if ia:
            hard_ev.update(self._nombres_kb(ia["hard_skills"], puesto["hard_skills"], hard_ev))
            soft_ev.update(self._nombres_kb(ia["soft_skills"], self.rag.soft, soft_ev))
        resultado = self._armar_resultado(puesto, perfil, cv, hard_ev, soft_ev, en_perfil, set(det), problemas, ia)
        # 8. Persistencia + respuesta
        fila = AnalisisIA(id_sesion=sesion.id_sesion, id_cv=fila_cv.id_cv, id_puesto_base=puesto["id"],
                          match_score=resultado["match_score"], skills_gap=resultado["skills_gap"],
                          plan_estudio_json=resultado["plan_estudio_json"], resultado_json=resultado, modo=modo, modelo=modelo)
        self.db.add(fila)
        self.db.flush()
        resultado["id_analisis"] = fila.id_analisis
        resultado["modo"], resultado["modelo"] = modo, modelo
        fila.resultado_json = dict(resultado)
        sesion.estado = "analizado"
        return self._respuesta(sesion, mensaje_diagnostico(resultado), analisis=resultado)

    @staticmethod
    def _nombres_kb(items: List[dict], skills_kb: List[dict], ya: dict) -> Dict[str, str]:
        """Habilidades que la IA dice haber detectado y que además existen en la base (la IA no agrega skills nuevas al puntaje)."""
        from rag import _patron_alias
        res: Dict[str, str] = {}
        for it in items:
            nombre_norm = normalizar(it["nombre"])
            for s in skills_kb:
                if s["nombre"] in ya or s["nombre"] in res:
                    continue
                if normalizar(s["nombre"]) == nombre_norm or any(_patron_alias(a).search(nombre_norm) for a in s["alias"]):
                    res[s["nombre"]] = it["evidencia"] or "Detectada en el CV"
        return res

    def _armar_resultado(self, puesto, perfil, cv, hard_ev, soft_ev, en_perfil, en_cv, problemas, ia) -> Dict[str, Any]:
        skills = puesto["hard_skills"]
        total = sum(s["peso"] for s in skills) or 1
        tiene = sum(s["peso"] for s in skills if s["nombre"] in hard_ev)
        ratio_soft = min(1.0, len(soft_ev) / 4.0)
        ratio_ats = max(0.0, 1.0 - 0.2 * len(problemas))
        score = round(100 * (0.70 * tiene / total + 0.15 * ratio_soft + 0.15 * ratio_ats))
        score = max(0, min(100, score))
        faltan = sorted([s for s in skills if s["nombre"] not in hard_ev], key=lambda s: (-s["peso"], s["semanas"]))
        motivos_ia = {normalizar(f["habilidad"]): f["motivo"] for f in (ia or {}).get("faltantes", []) if f["motivo"]}
        gap = [{"habilidad": s["nombre"], "importancia": _importancia(s["peso"]),
                "motivo": motivos_ia.get(normalizar(s["nombre"])) or s["motivo"]} for s in faltan]
        acciones_ia = {normalizar(p["habilidad"]): p for p in (ia or {}).get("plan", [])}
        plan = []
        for i, s in enumerate(faltan[:5], start=1):
            p_ia = next((v for k, v in acciones_ia.items() if k == normalizar(s["nombre"]) or normalizar(s["nombre"]) in k or k in normalizar(s["nombre"])), None)
            plan.append({"orden": i, "habilidad": s["nombre"],
                         "accion": (p_ia["accion"] if p_ia else "Estudiá los fundamentos y armá un mini proyecto para mostrar en tu portfolio."),
                         "duracion_semanas": (p_ia["duracion_semanas"] if p_ia and p_ia["duracion_semanas"] else s["semanas"]),
                         "recurso": self.rag.recurso(s["recurso"])})
        if ia and ia["experiencias"]:
            exps = ia["experiencias"]
        else:
            exps = [{"rol": "", "organizacion": "", "periodo": "", "resumen": l.strip()[:200]}
                    for l in cv.texto.split("\n") if re.search(r"(?:19|20)\d{2}", l)][:5]
        compat = [s["nombre"] for s in skills if s["nombre"] in hard_ev]
        resumen = (ia or {}).get("resumen") or ""
        return {
            "puesto": {"id": puesto["id"], "titulo": puesto["titulo"]},
            "match_score": score,
            "desglose": {"hard_pct": round(100 * tiene / total), "soft_pct": round(100 * ratio_soft),
                         "ats_pct": round(100 * ratio_ats), "gap_pct": round(100 * (total - tiene) / total)},
            "hard_skills": [{"nombre": n, "evidencia": e} for n, e in hard_ev.items()],
            "soft_skills": [{"nombre": n, "evidencia": e} for n, e in soft_ev.items()],
            "experiencias": exps,
            "compatibles": compat,
            "skills_gap": gap,
            "plan_estudio_json": plan,
            "problemas_ats": problemas,
            "fortalezas_no_en_cv": [n for n in en_perfil if n not in en_cv],
            "resumen": resumen,
            "aviso": AVISO_PUNTAJE,
        }

    # -- consultas -------------------------------------------------------
    def _ultimo_resultado(self, sesion: SesionChat) -> Optional[dict]:
        fila = (self.db.query(AnalisisIA).filter(AnalisisIA.id_sesion == sesion.id_sesion)
                .order_by(AnalisisIA.id_analisis.desc()).first())
        return fila.resultado_json if fila else None

    def ultimo_resultado(self, sesion: SesionChat) -> Optional[dict]:
        return self._ultimo_resultado(sesion)

