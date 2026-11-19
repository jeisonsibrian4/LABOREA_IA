// Comunicación con el backend. La sesión (un identificador largo y secreto) se guarda en sessionStorage:
// al cerrar la pestaña se pierde, pero mientras tanto se puede retomar la conversación con GET /api/sesion/{id}.
export const API: string = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'
const CLAVE = 'laborea_session'

export interface Recurso { nombre: string; url: string; descripcion: string }
export interface PasoPlan { orden: number; habilidad: string; accion: string; duracion_semanas: number; recurso: Recurso | null }
export interface Brecha { habilidad: string; importancia: 'alta' | 'media' | 'baja'; motivo: string }
export interface Evidencia { nombre: string; evidencia: string }
export interface Analisis {
  id_analisis: number
  puesto: { id: string; titulo: string }
  match_score: number
  desglose: { hard_pct: number; soft_pct: number; ats_pct: number; gap_pct: number }
  experiencias: { rol: string; organizacion: string; periodo: string; resumen: string }[]
  hard_skills: Evidencia[]
  soft_skills: Evidencia[]
  compatibles: string[]
  skills_gap: Brecha[]
  plan_estudio_json: PasoPlan[]
  problemas_ats: string[]
  fortalezas_no_en_cv: string[]
  resumen: string
  aviso: string
  modo: 'gemini' | 'reglas'
}
export type Estado = 'perfilamiento' | 'esperando_cv' | 'analizado'
export interface Mensaje { rol: 'user' | 'bot'; contenido: string }
export interface Respuesta { response: string; estado: Estado; paso: number; session_id?: string; analisis?: Analisis; error_cv?: boolean }
export interface Perfil { puesto: string | null; meta: string | null; proyectos: string | null; id_puesto: string | null }
export interface SesionGuardada { session_id: string; estado: Estado; paso: number; perfil: Perfil | null; mensajes: Mensaje[]; analisis: Analisis | null }

export const getSesion = (): string | null => { try { return sessionStorage.getItem(CLAVE) } catch { return null } }
export const guardarSesion = (id: string) => { try { sessionStorage.setItem(CLAVE, id) } catch { /* sin storage */ } }
export const olvidarSesion = () => { try { sessionStorage.removeItem(CLAVE) } catch { /* sin storage */ } }

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  let r: Response
  try { r = await fetch(API + ruta, init) } catch { throw new Error('No pude conectarme con el servidor. ¿Está encendido el backend?') }
  const cuerpo = await r.json().catch(() => ({}))
  if (!r.ok) {
    // 422 del CV: el backend manda el mensaje para la persona en "response"
    throw Object.assign(new Error(cuerpo.response || cuerpo.detail || 'Algo salió mal. Probá de nuevo.'), { cuerpo, status: r.status })
  }
  return cuerpo as T
}

export const crearSesion = () => pedir<Respuesta>('/api/sesion', { method: 'POST' })
export const cargarSesion = (id: string) => pedir<SesionGuardada>('/api/sesion/' + id)
export const enviarMensaje = (session_id: string, message: string) =>
  pedir<Respuesta>('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id, message }) })
export const subirCV = (session_id: string, archivo: File) => {
  const f = new FormData()
  f.append('session_id', session_id)
  f.append('file', archivo)
  return pedir<Respuesta>('/api/cv', { method: 'POST', body: f })
}
export const borrarSesion = (id: string) => pedir<{ estado: string }>('/api/sesion/' + id, { method: 'DELETE' })
