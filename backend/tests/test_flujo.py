"""Prueba de punta a punta del flujo del diagrama (modo reglas, sin Gemini)."""
from conftest import avanzar_perfil, hacer_docx, hacer_pdf
from database import SessionLocal
from models import AnalisisIA, DocumentoCV, MensajeChat, PerfilObjetivo, SesionChat


def test_flujo_completo_con_pdf(client):
    # 1. inicio de sesión: saluda y hace la primera pregunta (HU-01)
    r = client.post("/api/sesion").json()
    sid = r["session_id"]
    assert r["estado"] == "perfilamiento" and "puesto" in r["response"]
    # 2. las 3 preguntas
    r = client.post("/api/chat", json={"session_id": sid, "message": "Quiero ser desarrolladora frontend"}).json()
    assert r["paso"] == 1 and "meta profesional" in r["response"]
    r = client.post("/api/chat", json={"session_id": sid, "message": "Mi primer trabajo junior"}).json()
    assert r["paso"] == 2 and "proyectos" in r["response"]
    r = client.post("/api/chat", json={"session_id": sid, "message": "Hice una página con React y Docker"}).json()
    assert r["estado"] == "esperando_cv"
    # 3. si escribe en vez de adjuntar, se le vuelve a pedir el CV
    r = client.post("/api/chat", json={"session_id": sid, "message": "ya lo mandé"}).json()
    assert r["estado"] == "esperando_cv" and "CV" in r["response"]
    # 4. sube el PDF -> diagnóstico (HU-02, HU-04, HU-05)
    r = client.post("/api/cv", data={"session_id": sid}, files={"file": ("cv.pdf", hacer_pdf(), "application/pdf")})
    assert r.status_code == 200, r.text
    out = r.json()
    a = out["analisis"]
    assert out["estado"] == "analizado" and a["modo"] == "reglas"
    assert a["puesto"]["id"] == "frontend-jr"
    assert 0 <= a["match_score"] <= 100
    assert {"HTML y CSS", "JavaScript", "React", "Git y GitHub"} <= set(a["compatibles"])
    faltan = [g["habilidad"] for g in a["skills_gap"]]
    assert "TypeScript" in faltan and "HTML y CSS" not in faltan
    assert a["plan_estudio_json"] and all(p["recurso"]["url"].startswith("https://") for p in a["plan_estudio_json"])
    assert a["plan_estudio_json"][0]["orden"] == 1
    assert a["aviso"]
    # "datos no aportados": mencionó Docker en el perfil pero no está en el CV
    # (Docker no es requisito de frontend, por eso no aparece; React sí figura en el CV)
    assert "React" not in a["fortalezas_no_en_cv"]
    # 5. persistencia (HU-07): una fila en cada tabla del diagrama
    db = SessionLocal()
    try:
        assert db.get(SesionChat, sid).estado == "analizado"
        assert db.query(PerfilObjetivo).filter_by(id_sesion=sid).one().id_puesto_base == "frontend-jr"
        cv = db.query(DocumentoCV).filter_by(id_sesion=sid).one()
        assert cv.formato == "pdf" and "JavaScript" in cv.texto_extraido
        fila = db.query(AnalisisIA).filter_by(id_sesion=sid).one()
        assert fila.match_score == a["match_score"] and fila.skills_gap and fila.plan_estudio_json
        assert db.query(MensajeChat).filter_by(id_sesion=sid).count() >= 8
    finally:
        db.close()
    # 6. asesoría en tiempo real: enlaces solo de la base
    r = client.post("/api/chat", json={"session_id": sid, "message": "¿Me pasás enlaces para estudiar?"}).json()
    assert "https://" in r["response"]
    r = client.post("/api/chat", json={"session_id": sid, "message": "¿Cuál es mi puntaje?"}).json()
    assert str(a["match_score"]) in r["response"]
    # 7. retomar la conversación y consultar lo guardado
    s = client.get("/api/sesion/" + sid).json()
    assert s["estado"] == "analizado" and s["analisis"]["match_score"] == a["match_score"] and len(s["mensajes"]) > 8
    assert client.get("/api/analisis/" + sid).json()["match_score"] == a["match_score"]
    assert client.get("/api/enlaces/" + sid).json()["enlaces"]
    # 8. derecho a borrar: se elimina todo
    assert client.delete("/api/sesion/" + sid).status_code == 200
    assert client.get("/api/sesion/" + sid).status_code == 404
    db = SessionLocal()
    try:
        assert db.query(DocumentoCV).filter_by(id_sesion=sid).count() == 0
        assert db.query(AnalisisIA).filter_by(id_sesion=sid).count() == 0
    finally:
        db.close()


def test_cv_en_word_con_tabla_marca_problema_ats(client):
    sid = avanzar_perfil(client)
    r = client.post("/api/cv", data={"session_id": sid}, files={"file": ("cv.docx", hacer_docx(con_tabla=True), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert r.status_code == 200, r.text
    assert any("tablas" in p for p in r.json()["analisis"]["problemas_ats"])


def test_puesto_no_reconocido_no_avanza(client):
    sid = client.post("/api/sesion").json()["session_id"]
    r = client.post("/api/chat", json={"session_id": sid, "message": "Quiero ser panadero"}).json()
    assert r["paso"] == 0 and "Todavía no tengo requisitos" in r["response"]
    r = client.post("/api/chat", json={"session_id": sid, "message": "analista de datos"}).json()
    assert r["paso"] == 1


def test_cv_antes_de_terminar_el_perfil_es_409(client):
    sid = client.post("/api/sesion").json()["session_id"]
    r = client.post("/api/cv", data={"session_id": sid}, files={"file": ("cv.pdf", hacer_pdf(), "application/pdf")})
    assert r.status_code == 409


def test_formato_invalido_vuelve_a_pedir_y_luego_acepta(client):
    sid = avanzar_perfil(client)
    # HU-03: .txt, .doc, un "pdf" falso y un archivo vacío se rechazan
    for nombre, datos in [("cv.txt", b"hola" * 50), ("cv.doc", b"\xd0\xcf\x11\xe0" + b"0" * 200),
                          ("cv.pdf", b"esto no es un pdf" * 20), ("cv.pdf", b"")]:
        r = client.post("/api/cv", data={"session_id": sid}, files={"file": (nombre, datos, "application/octet-stream")})
        assert r.status_code == 422, (nombre, r.text)
        assert r.json()["error_cv"] is True and r.json()["estado"] == "esperando_cv"
    # un PDF sin texto (escaneado) también se rechaza con un mensaje claro
    r = client.post("/api/cv", data={"session_id": sid}, files={"file": ("cv.pdf", hacer_pdf(["x"]), "application/pdf")})
    assert r.status_code == 422 and "texto" in r.json()["response"]
    # después de los errores, un archivo correcto funciona
    r = client.post("/api/cv", data={"session_id": sid}, files={"file": ("cv.pdf", hacer_pdf(), "application/pdf")})
    assert r.status_code == 200 and r.json()["estado"] == "analizado"


def test_sesion_invalida(client):
    assert client.post("/api/chat", json={"session_id": "no-es-valido", "message": "hola"}).status_code == 422
    assert client.get("/api/sesion/" + "a" * 32).status_code == 404


def test_desglose_perfil_y_consejos_de_entrevista(client):
    sid = avanzar_perfil(client)
    s = client.get("/api/sesion/" + sid).json()
    assert s["perfil"]["id_puesto"] == "frontend-jr" and "primer trabajo" in s["perfil"]["meta"]
    a = client.post("/api/cv", data={"session_id": sid}, files={"file": ("cv.pdf", hacer_pdf(), "application/pdf")}).json()["analisis"]
    d = a["desglose"]
    assert all(0 <= d[k] <= 100 for k in ("hard_pct", "soft_pct", "ats_pct", "gap_pct"))
    assert d["hard_pct"] + d["gap_pct"] in (99, 100, 101)      # redondeo
    r = client.post("/api/chat", json={"session_id": sid, "message": "¿Cómo me preparo para la entrevista?"}).json()["response"]
    assert "entrevista" in r and "1 minuto" in r
