# LABOREA IA — Guía de Actualizaciones en GitHub (Commits y Push)

Usa esta guía rápida cada vez que hagas cambios en el código y quieras guardarlos y subirlos a tu repositorio de GitHub: `https://github.com/jeisonsibrian4/LABOREA_IA`.

---

## 🚀 El Flujo Rápido (Los 4 pasos de siempre)

Cada vez que termines de hacer modificaciones, abre tu terminal (PowerShell o CMD) y corre estos comandos en orden:

### Paso 1: Entrar a la carpeta del proyecto
```cmd
cd "C:\LABOREA\proyecto LABOREA1\proyecto LABOREA\LABOREA_Prototipo"
```

---

### Paso 2: Seleccionar los cambios realizados
Prepara todos los archivos que modificaste, agregaste o borraste:
```cmd
git add .
```
*(El punto `.` al final significa "incluye todo lo que cambió").*

---

### Paso 3: Crear el punto de guardado (Commit)
Guarda la "foto" de tus cambios con una frase breve entre comillas explicando qué hiciste:
```cmd
git commit -m "Escribe aqui una breve explicacion de lo que cambiaste"
```

**Ejemplos de mensajes útiles:**
- `git commit -m "Actualizacion de textos en la pantalla de inicio"`
- `git commit -m "Correccion de estilos en botones del frontend"`
- `git commit -m "Agregado nuevo test de auditoria"`
- `git commit -m "Ajuste en la clave o conexion de Gemini"`

---

### Paso 4: Subir todo a GitHub (Push)
Envía tus cambios a la nube:
```cmd
git push
```

¡Listo! Cuando termine, entra a tu repositorio en el navegador y verás los cambios reflejados al instante con tu mensaje.

---

## 🔍 Comando extra muy útil: `git status`

Si tienes dudas de qué archivos modificaste antes de hacer el commit, puedes escribir en cualquier momento:
```cmd
git status
```
- Los archivos en **rojo** son los que cambiaste pero aún no agregaste (`git add .`).
- Los archivos en **verde** son los que ya están listos para el commit (`git commit`).
- Si dice *"working tree clean"*, significa que no hay cambios pendientes por guardar.
