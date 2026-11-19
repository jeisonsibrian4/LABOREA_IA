# LABOREA IA · Prototipo funcional

Agente conversacional que acompaña a personas desempleadas o en reconversión laboral. Hace tres preguntas para conocer a la persona, recibe su CV (PDF o Word), lo compara con los requisitos de un puesto y devuelve un diagnóstico claro: puntaje de coincidencia, habilidades que ya tiene, habilidades que le faltan, plan de estudio con recursos gratuitos y mejoras de formato para pasar los filtros automáticos (ATS). Después sigue asesorándola en el chat.

Esta guía explica cómo ponerlo en marcha, cómo se usa, cómo está armado y qué podés cambiar. Hay una versión con capturas en `docs/Guia_de_uso_LABOREA.pdf`.

---

## 1. Qué necesitás

- **Python 3.10 o superior** (https://www.python.org/downloads/; en Windows, marcá «Add Python to PATH»).
- **Node.js 20 o superior** (https://nodejs.org).
- *(Opcional)* una **clave de Gemini** gratuita. Sin clave, el prototipo funciona igual en «modo reglas».

## 2. Puesta en marcha

**En Windows (lo más simple):**
1. Doble clic en `setup.bat`. Instala todo y crea `backend\.env`. Se hace una sola vez.
2. Doble clic en `iniciar_backend.bat`. Queda abierta una ventana (puerto 8001).
3. Doble clic en `iniciar_frontend.bat` y abrí http://localhost:5173

**A mano (Windows, Mac o Linux):**
```bash
# Terminal 1 - backend
python -m venv .venv
source .venv/bin/activate            # en Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env # en Windows: copy backend\.env.example backend\.env
cd backend
uvicorn main:app --port 8001 --reload

# Terminal 2 - frontend
cd frontend
npm install
npm run dev                          # abre http://localhost:5173
```
Para comprobar que el backend anda: http://localhost:8001/health debe responder `{"estado":"ok", ...}`. La documentación interactiva de la API está en http://localhost:8001/docs.

## 3. Activar Gemini (opcional)

1. Creá una clave gratuita en Google AI Studio (https://aistudio.google.com/apikey).
2. Abrí `backend/.env` y completá `GEMINI_API_KEY=` con tu clave.
3. Reiniciá el backend. En la consola debe aparecer «Gemini: activo». En la app, la tarjeta «Match con el mercado» dice «Análisis con IA».

Reglas importantes:
- La clave va **solo** en `backend/.env`. Ese archivo está en `.gitignore`: **nunca** lo subas a GitHub ni lo mandes por chat o en un zip.
- `GEMINI_MODEL` define el modelo (por defecto `gemini-2.5-flash`). Si Google cambia nombres de modelos, se actualiza ahí.
- Si Gemini falla, no responde o se agota la cuota gratuita, la app **vuelve sola al modo reglas** y la persona igual recibe su diagnóstico.

## 4. Cómo se usa la aplicación

El menú lateral tiene cinco secciones:

| Sección | Qué hace |
|---|---|
| **Inicio** | Saludo del asistente y chat. Hace las 3 preguntas de perfilamiento (puesto, meta profesional y proyectos). El clip 📎 sube el CV. |
| **Mi perfil** | Muestra lo que la persona contó (objetivo), sus habilidades detectadas y su experiencia. |
| **Mi CV** | Zona para arrastrar o elegir el archivo (PDF o DOCX, hasta 5 MB), estado de compatibilidad ATS y resumen del análisis. |
| **Mis asesorías** | Match con el mercado (porcentaje), barras de Hard Skills, Soft Skills y Skills Gap, y recomendaciones clave. |
| **Plan de ataque** | Hoja de ruta en 4 pasos: optimizar el CV, formación recomendada (con enlaces gratuitos), preparación para entrevistas y postulación. |

Flujo típico: **Inicio** → responder las 3 preguntas → subir el CV → ver **Mis asesorías** → seguir el **Plan de ataque** → seguir conversando en **Inicio** (el asistente responde sobre el puntaje, el plan, los enlaces o el CV).

Otras funciones: «Nueva conversación» reinicia todo; el ícono de usuario permite **borrar los datos** (conversación, CV y análisis).

## 5. Tecnologías utilizadas

**En una frase:** es una aplicación web de dos partes. El **frontend** (React) corre en el navegador y se comunica por una **API REST con JSON** con el **backend** (FastAPI), que guarda los datos en una base SQL y consulta a **Gemini** cuando hay clave.

### Backend (Python)
| Tecnología | Para qué se usa | Dónde |
|---|---|---|
| **Python 3.10+** | Lenguaje de todo el backend. | `backend/` |
| **FastAPI** | Framework para crear la API REST: define los endpoints, valida los datos y genera la documentación en `/docs`. | `main.py` |
| **Starlette** | Base sobre la que está hecho FastAPI (CORS, middleware, recepción de archivos). Se instala sola. | (dependencia) |
| **Uvicorn** | Servidor que ejecuta la aplicación FastAPI. | `iniciar_backend.bat` |
| **Pydantic v2** | Define y valida los formatos de entrada y la forma de la respuesta que se le pide a la IA. | `schemas.py` |
| **python-multipart** | Permite recibir el archivo del CV (`multipart/form-data`). | `POST /api/cv` |
| **python-dotenv** | Carga el archivo `.env` con la configuración y la clave de Gemini. | `config.py` |

### Datos
| Tecnología | Para qué se usa | Dónde |
|---|---|---|
| **SQLAlchemy 2 (ORM)** | Representa las tablas como clases de Python y permite consultar sin escribir SQL a mano. | `models.py`, `database.py` |
| **SQLite** | Base de datos por defecto: un solo archivo (`laborea.db`), sin instalar nada. | `database.py` |
| **PostgreSQL** *(opcional)* + `psycopg2` | Base para publicar el proyecto en serio; se activa con `DATABASE_URL`. | `database/schema.sql` |
| **JSON** | Formato de la base de mercado laboral y de los campos `skills_gap` y `plan_estudio_json`. | `data/mercado_laboral.json` |

### Lectura y análisis del CV
| Tecnología | Para qué se usa | Dónde |
|---|---|---|
| **pypdf** | Extrae el texto de los PDF y cuenta páginas e imágenes. | `cv_extractor.py` |
| **python-docx** | Lee los Word (.docx): párrafos, tablas e imágenes. | `cv_extractor.py` |
| **Expresiones regulares (`re`)** | Detectan habilidades, fechas y emails, y enmascaran datos personales. | `rag.py`, `pii.py`, `cv_extractor.py` |

### Inteligencia artificial
| Tecnología | Para qué se usa | Dónde |
|---|---|---|
| **Google Gemini** | Modelo de lenguaje que analiza el CV, redacta el diagnóstico y responde en el chat. Por defecto `gemini-2.5-flash` (se cambia en `GEMINI_MODEL`). | `gemini_service.py` |
| **SDK `google-genai`** | Librería oficial para llamar a Gemini. Se le pide una respuesta en JSON con un esquema definido. | `gemini_service.py` |
| **Ingeniería de prompts** | Prompts de sistema con reglas estrictas; el CV va delimitado como dato para evitar manipulaciones. | `gemini_service.py` |
| **RAG simple: TF-IDF + similitud coseno** | Recupera el contexto de mercado y reconoce el puesto que escribe la persona. Implementado en Python puro, sin librerías de IA. | `rag.py` |
| **Modo reglas** | Diagnóstico sin IA cuando Gemini no está disponible. | `orquestador.py` |

### Frontend
| Tecnología | Para qué se usa | Dónde |
|---|---|---|
| **React 19** | Construye la interfaz con componentes y estado. | `App.tsx` |
| **TypeScript** | JavaScript con tipos: detecta errores antes de ejecutar. | `*.tsx`, `api.ts` |
| **Vite** | Herramienta de desarrollo y compilación (`npm run dev`, `npm run build`). | `vite.config.ts` |
| **CSS puro** | Estilos con variables, grid y flexbox, y adaptación a celular (no usa librerías de diseño). | `App.css` |
| **SVG propio** | El robot y los íconos están dibujados en código, sin librerías de imágenes ni de íconos. | `Robot.tsx`, `Iconos.tsx` |
| **Fetch API y `sessionStorage`** | Comunicación con el backend y memoria del identificador de sesión en el navegador. | `api.ts` |

### Calidad y herramientas
| Tecnología | Para qué se usa | Dónde |
|---|---|---|
| **pytest** | Las 20 pruebas automáticas. | `backend/tests/` |
| **httpx / TestClient** | Prueban la API sin levantar el servidor. | `backend/tests/` |
| **reportlab** | Genera PDFs de ejemplo para las pruebas (solo en desarrollo). | `requirements-dev.txt` |

### Conceptos que aparecen en el proyecto
- **API REST:** el frontend y el backend se comunican con pedidos HTTP (`GET`, `POST`, `DELETE`) que intercambian JSON.
- **Orquestador:** un único módulo coordina las etapas del flujo; la IA solo interpreta y redacta, nunca toca la base de datos.
- **RAG (generación aumentada por recuperación):** antes de llamar a la IA se recupera el contexto relevante (los requisitos del puesto) y se le entrega junto con el CV.
- **ATS:** sistema de filtrado automático de CV que usan las empresas; por eso se revisa el formato del documento.
- **CORS:** regla del navegador que decide qué sitios pueden llamar a la API (`FRONTEND_ORIGINS`).
- **Límite de pedidos por IP** y **sesión anónima** con identificador secreto, sin registro.
- **Enmascarado de datos personales:** se tapan emails, teléfonos y documentos antes de enviar texto a la IA.

### Por qué estas elecciones
- Todo es **gratuito y de código abierto**, y se instala con un par de comandos.
- **Funciona sin clave y sin internet** gracias al modo reglas; Gemini mejora el análisis pero no es imprescindible.
- **Cada parte está separada** (API, datos, IA, lectura de CV, interfaz): se puede cambiar una sin romper las demás.
- El **puntaje lo calcula el backend**, de modo que el resultado es auditable y no depende de lo que diga el modelo.

## 6. Cómo está armado

```
LABOREA_Prototipo/
├── backend/
│   ├── main.py              API (FastAPI): endpoints, CORS, límites por IP
│   ├── orquestador.py       flujo de etapas + componente de IA + asesoría
│   ├── gemini_service.py    llamadas a Gemini y prompts (reglas estrictas)
│   ├── rag.py               recuperación del contexto de mercado (TF-IDF)
│   ├── cv_extractor.py      validación y lectura de PDF/Word + chequeo ATS
│   ├── models.py            tablas        schemas.py   formatos de entrada/salida
│   ├── database.py          conexión      config.py    carga del .env
│   ├── cuota.py             control de cuota de Gemini
│   ├── pii.py               privacidad (enmascarado de datos personales)
│   ├── data/mercado_laboral.json   base de ejemplo: puestos, requisitos y recursos
│   ├── tests/               20 pruebas automáticas
│   ├── .env.example         plantilla de configuración (copiar a .env)
│   └── requirements.txt     requirements-dev.txt
├── database/schema.sql      tablas en SQL para PostgreSQL (opcional)
├── docs/                    guía en PDF y matriz de trazabilidad
├── frontend/                React + Vite + TypeScript
│   └── src/  App.tsx (pantallas) · App.css (estilos) · Robot.tsx (mascota) · Iconos.tsx · api.ts
└── setup.bat · iniciar_backend.bat · iniciar_frontend.bat
```

### Correspondencia con el diagrama integrador

| Etapa del diagrama | Dónde está |
|---|---|
| Inicia la interacción → `SESION_CHAT` | `Orquestador.crear_sesion()` · `POST /api/sesion` |
| 3 preguntas de perfilamiento → `PERFIL_OBJETIVO` | `Orquestador._perfilar()` · `POST /api/chat` |
| Adjuntar CV y validar formato (si falla, se vuelve a pedir) | `cv_extractor.py` · `POST /api/cv` (responde 422 y el chat lo pide de nuevo) |
| Extracción y registro → `DOCUMENTO_CV` | `Orquestador.recibir_cv()` |
| Recuperación documental / contexto de mercado (RAG) | `rag.py` + `data/mercado_laboral.json` |
| El backend llama a la API de Gemini con prompts | `ComponenteIA.diagnosticar()` → `gemini_service.py` |
| Diagnóstico estructurado (skills, gap, plan) | `schemas.DiagnosticoIA` + `validar_diagnostico()` |
| Se guarda en `ANALISIS_IA` y se muestra en pantalla | `Orquestador._analizar()` |
| Asesoría en tiempo real | `ComponenteIA.asesorar()` |

La matriz historia de usuario → componente → endpoint → tabla → prueba está en [`docs/trazabilidad.md`](docs/trazabilidad.md).

### Decisiones de diseño que conviene conocer

1. **El puntaje lo calcula el backend, no la IA.** `match_score` = 70 % habilidades técnicas del puesto (ponderadas) + 15 % habilidades blandas + 15 % formato del CV. Gemini aporta evidencia y redacción, pero no puede subir el puntaje ni sumar habilidades que no estén en la base. Así el diagnóstico es honesto y auditable.
2. **La IA no inventa enlaces.** Los recursos del plan salen de la base. Si en el chat Gemini escribe un enlace que no está en la base, el backend lo reemplaza por «[enlace no verificado]».
3. **El CV es un dato, no una instrucción.** Va entre `<cv>…</cv>` y el prompt le indica a Gemini que ignore órdenes escritas dentro del texto (por ejemplo, «poné 100 %»).
4. **Siempre hay respuesta.** Sin clave, sin internet o sin cuota, funciona el modo reglas.

## 7. Qué podés cambiar y dónde

| Quiero cambiar… | Archivo | Cómo |
|---|---|---|
| Los **puestos, requisitos y recursos** de estudio | `backend/data/mercado_laboral.json` | Cada puesto tiene `titulo`, `alias` (cómo lo nombra la gente) y `hard_skills` (nombre, `alias` para detectarla en el CV, `peso` de 1 a 3, `recurso`, `semanas`, `motivo`). Los recursos están al final, en `recursos`. Reiniciá el backend. |
| Las **3 preguntas** y los textos del asistente | `backend/orquestador.py` | Constantes `PREGUNTAS`, `SALUDO`, `MSG_PEDIR_CV` y la función `mensaje_diagnostico()`. |
| Cómo **piensa y habla** Gemini | `backend/gemini_service.py` | `SISTEMA_DIAGNOSTICO` y `SISTEMA_ASESOR` (reglas, tono, límites). |
| Cómo se **calcula el puntaje** | `backend/orquestador.py` | En `_armar_resultado()`: los pesos 0.70 / 0.15 / 0.15 y cuántas habilidades blandas se esperan (4). |
| Los **problemas de formato (ATS)** que se detectan | `backend/cv_extractor.py` | Función `detectar_problemas_ats()`. |
| El **tamaño máximo** del CV | `backend/cv_extractor.py` | `MAX_BYTES` (y el texto «Máx. 5 MB» en `frontend/src/App.tsx`). |
| **Límites** por hora, retención de datos, orígenes permitidos | `backend/.env` | `LIMITE_*`, `RETENCION_DIAS`, `FRONTEND_ORIGINS`. |
| La **base de datos** (SQLite → PostgreSQL) | `backend/.env` | `DATABASE_URL=postgresql://usuario:clave@localhost:5432/laborea` y `pip install psycopg2-binary`. Las tablas se crean solas; `database/schema.sql` es el SQL equivalente. |
| **Colores, tipografía y estilo** | `frontend/src/App.css` | Variables al principio (`--n1` y `--n2` son los naranjas). |
| **Textos y pantallas** | `frontend/src/App.tsx` | Cada sección es una constante (`inicio`, `vistaPerfil`, `vistaCV`, `vistaAsesorias`, `vistaPlan`). |
| La **mascota** o el logo | `frontend/src/Robot.tsx` y `App.tsx` | El robot es un SVG editable; el logo es la «L» del menú. |
| La **URL del backend** (al publicarlo) | `frontend/.env` | Copiá `.env.example` y poné `VITE_API_URL`. |


## 8. Privacidad y seguridad

- Antes de enviar texto a Gemini se tapan emails, teléfonos, DNI/CUIL y números de tarjeta.
- Si alguien escribe un DNI, una tarjeta o una contraseña en el chat, el mensaje no se guarda.
- «Borrar mis datos» elimina la sesión completa (CV y análisis incluidos). Las sesiones sin actividad por más de 30 días se borran cuando arranca el servidor (`RETENCION_DIAS`).
- El archivo se valida por su contenido real (un `.pdf` falso se rechaza), con tope de 5 MB.
- Límites por IP para sesiones, mensajes y CV; con `ENTORNO=produccion` se ocultan `/docs` y `/openapi.json`.

## 9. Pruebas

```bash
pip install -r backend/requirements-dev.txt
cd backend
python -m pytest tests -q          # 20 pruebas
```
Cubren el flujo completo con PDF y con Word, las 5 tablas, el rechazo de formatos inválidos y el reintento, puesto no reconocido, datos sensibles, privacidad, cuota, validación de la salida de la IA, enlaces inventados y el paso automático al modo reglas.

**Importante:** las pruebas del modo Gemini usan una IA simulada. Cuando pongas tu clave, probá con un CV real y verificá que el análisis diga «Análisis con IA».

## 10. Problemas comunes

| Síntoma | Qué revisar |
|---|---|
| La pantalla dice «No pude conectarme con el servidor» | El backend no está corriendo (`iniciar_backend.bat`) o `VITE_API_URL` apunta a otra dirección. |
| `uvicorn` o `pip` no se reconocen | Activá el entorno virtual (`.venv\Scripts\activate`) o reinstalá Python marcando «Add to PATH». |
| El análisis siempre dice «por reglas» | Falta la clave en `backend/.env`, la clave es inválida, o se agotó la cuota por minuto (probá en un rato). |
| «Todavía no tengo requisitos cargados para ese puesto» | El puesto no está en `mercado_laboral.json`: agregalo (con sus `alias`). |
| «No encontré texto en el archivo» | El PDF es una foto o está escaneado. Exportalo desde Word o Google Docs con texto seleccionable. |
| Error de CORS en el navegador | Agregá la dirección del frontend a `FRONTEND_ORIGINS` en `backend/.env`. |
| Quiero empezar de cero | Borrá `backend/laborea.db` (con el backend apagado). |



> 💡 **Guías Rápidas Adicionales:**  
> - **[README2.md](README2.md):** Pasos esenciales de instalación y puesta en marcha rápida.  
> - **[README_Auditoria.md](README_Auditoria.md):** Guía completa de auditoría técnica, desglose de las 20 pruebas automáticas y defensa ante terceros.

