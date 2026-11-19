# Matriz de trazabilidad · LABOREA IA

Cada elemento del diseño se puede rastrear hasta una historia de usuario (incluida la de IA).
Las HU y sus nombres son las que figuran en el documento del Grupo 9; **completá la HU-06** con el número y el título que usan ustedes.

| HU | Historia (según el documento) | Componente | Endpoint | Tabla | Prueba |
|---|---|---|---|---|---|
| HU-01 | Cuestionario de perfilamiento inicial (3 preguntas) | `Orquestador.crear_sesion()` / `_perfilar()` | `POST /api/sesion`, `POST /api/chat` | `SESION_CHAT`, `PERFIL_OBJETIVO` | `test_flujo_completo_con_pdf`, `test_puesto_no_reconocido_no_avanza` |
| HU-02 | Subida de documentos PDF / Word | `cv_extractor.extraer_cv()`, `Orquestador.recibir_cv()` | `POST /api/cv` | `DOCUMENTO_CV` | `test_flujo_completo_con_pdf`, `test_cv_en_word_con_tabla_marca_problema_ats` |
| HU-03 | Manejo de errores y validación de formatos no permitidos | `cv_extractor._formato()` + bucle del chat | `POST /api/cv` → 422 | — (queda en `MENSAJE_CHAT`) | `test_formato_invalido_vuelve_a_pedir_y_luego_acepta` |
| HU-04 | Evaluación de la brecha de habilidades (skills gap) vs. el puesto deseado | `rag.Recuperador`, `Orquestador._armar_resultado()` | `POST /api/cv`, `GET /api/analisis/{id}` | `ANALISIS_IA.skills_gap` | `test_flujo_completo_con_pdf`, `test_recuperador` |
| HU-05 | **Historia de IA:** diagnóstico automatizado y recomendaciones de capacitación | `ComponenteIA.diagnosticar()`, `gemini_service.py`, `validar_diagnostico()` | `POST /api/cv` | `ANALISIS_IA.plan_estudio_json` | `test_modo_gemini_valida_y_no_deja_inflar_el_puntaje`, `test_si_gemini_falla_sigue_en_modo_reglas` |
| HU-06 | *(completar)* Asesoría en tiempo real / enlaces de formación | `ComponenteIA.asesorar()` | `POST /api/chat`, `GET /api/enlaces/{id}` | `MENSAJE_CHAT` | `test_flujo_completo_con_pdf` (pasos 6 y 7) |
| HU-07 | Memoria de sesión y persistencia de datos | `Orquestador` (guarda cada etapa), `GET /api/sesion/{id}` | `GET /api/sesion/{id}`, `DELETE /api/sesion/{id}` | las 5 tablas | `test_flujo_completo_con_pdf` (pasos 5, 7 y 8) |

## Checklist de la Etapa 5 (integración de IA)

1. **¿Qué componente llama a la API/modelo?** El orquestador del backend (`ComponenteIA` → `ServicioGemini.generar`).
2. **¿Qué datos le envía?** Contexto de sesión (perfil con los objetivos), texto del CV con datos personales enmascarados, y el contexto de mercado recuperado (habilidades requeridas del puesto).
3. **¿Qué devuelve?** Diagnóstico estructurado: habilidades detectadas con evidencia, experiencias, brecha de competencias y plan de estudio.
4. **¿Qué hace la aplicación con la respuesta?** La valida, la combina con la detección por reglas, calcula el puntaje, la **guarda** (`ANALISIS_IA`) y la **muestra** en el chat y en la tarjeta de diagnóstico.
5. **¿Cada elemento se traza a una HU?** Sí: ver la tabla de arriba.
