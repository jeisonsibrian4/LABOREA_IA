# LABOREA IA — Guía Rápida de Instalación y Ejecución

Guía resumida y directa para instalar y poner en marcha el sistema sin pasos innecesarios.

---

## 1. Requisitos Previos

- **Python 3.10 o superior** (al instalar en Windows, marcar la casilla **"Add python.exe to PATH"**).
- **Node.js 20 o superior** (descargar desde [nodejs.org](https://nodejs.org/)).
- *(Opcional)* **Clave de Google Gemini**: si no tienes clave, el sistema funciona igualmente en **modo reglas**.

---

## 2. Instalación (Solo la primera vez)

### Opción A — Automática (Recomendada en Windows)
Haz doble clic en:
```
setup.bat
```
*Esto crea el entorno virtual `.venv`, instala las dependencias de Python, crea el archivo `backend/.env` e instala los paquetes de Node.js en el frontend.*

---

### Opción B — Manual por consola
Abre una terminal en la carpeta principal del proyecto:

```bash
# 1. Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate

# 2. Instalar dependencias del backend
pip install -r backend/requirements.txt
copy backend\.env.example backend\.env

# 3. Instalar dependencias del frontend
cd frontend
npm install
cd ..
```

*(Opcional: Si tienes API Key de Gemini, abre `backend/.env` con el Bloc de notas y completa `GEMINI_API_KEY=tu_clave`)*.

---

## 3. Cómo Iniciar el Sistema

Para usar la aplicación necesitas tener corriendo el **backend** y el **frontend** al mismo tiempo:

### Paso 1: Iniciar el Backend
- Haz doble clic en **`iniciar_backend.bat`**  
- O por consola:
  ```bash
  .venv\Scripts\activate
  cd backend
  uvicorn main:app --port 8001 --reload
  ```
  *(Disponible en: `http://localhost:8001` — Documentación API en: `http://localhost:8001/docs`)*

### Paso 2: Iniciar el Frontend
- Haz doble clic en **`iniciar_frontend.bat`**  
- O por consola:
  ```bash
  cd frontend
  npm run dev
  ```
- Abre tu navegador en: **`http://localhost:5173`**

---

## 4. Cómo Correr el Test de Auditoría (Pruebas del Sistema)

El proyecto incluye una suite de pruebas que audita de punta a punta el cumplimiento de las **Historias de Usuario (HU-01 a HU-07)**, la persistencia en base de datos, el cálculo matemático del match score (70/15/15), los filtros ATS y los guardrails éticos/PII.

- **Opción rápida:** Haz doble clic en **`correr_auditoria.bat`**.
- **Opción por consola:**
  ```bash
  .venv\Scripts\activate
  pip install -r backend/requirements-dev.txt
  cd backend
  python -m pytest tests -v
  ```

> 📖 Para una explicación completa de las 20 pruebas y cómo defender la auditoría ante terceros, consulta [README_Auditoria.md](README_Auditoria.md) y [`docs/trazabilidad.md`](docs/trazabilidad.md).
