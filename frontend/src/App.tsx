import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react'
import {
  borrarSesion, cargarSesion, crearSesion, enviarMensaje, getSesion, guardarSesion, olvidarSesion, subirCV,
  type Analisis, type Estado, type Mensaje, type Perfil, type Respuesta,
} from './api'
import Icono, { type IconoNombre } from './Iconos'
import Robot from './Robot'

type Vista = 'inicio' | 'perfil' | 'cv' | 'asesorias' | 'plan'
const NAV: { id: Vista; etiqueta: string; icono: IconoNombre }[] = [
  { id: 'inicio', etiqueta: 'Inicio', icono: 'inicio' },
  { id: 'perfil', etiqueta: 'Mi perfil', icono: 'perfil' },
  { id: 'cv', etiqueta: 'Mi CV', icono: 'cv' },
  { id: 'asesorias', etiqueta: 'Mis asesorías', icono: 'asesorias' },
  { id: 'plan', etiqueta: 'Plan de ataque', icono: 'plan' },
]
const SUGERENCIAS = ['¿Cómo es mi plan de estudio?', '¿Me pasás enlaces gratuitos?', '¿Cómo mejoro mi CV?', '¿Qué significa mi puntaje?']

// ---------- piezas reutilizables ----------
function Anillo({ valor, tam = 120, grosor = 11 }: { valor: number; tam?: number; grosor?: number }) {
  const r = (tam - grosor) / 2
  const c = 2 * Math.PI * r
  return (
    <div className="anillo" style={{ width: tam, height: tam }} role="img" aria-label={`${valor} por ciento`}>
      <svg width={tam} height={tam} viewBox={`0 0 ${tam} ${tam}`}>
        <defs><linearGradient id={`an${tam}`} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ffb24d" /><stop offset="1" stopColor="#f26a00" /></linearGradient></defs>
        <circle cx={tam / 2} cy={tam / 2} r={r} fill="none" stroke="#fde3cc" strokeWidth={grosor} />
        <circle cx={tam / 2} cy={tam / 2} r={r} fill="none" stroke={`url(#an${tam})`} strokeWidth={grosor} strokeLinecap="round"
          strokeDasharray={`${(c * valor) / 100} ${c}`} transform={`rotate(-90 ${tam / 2} ${tam / 2})`} />
      </svg>
      <b style={{ fontSize: tam * 0.235 }}>{valor}%</b>
    </div>
  )
}

function Encabezado({ icono, titulo, sub, onNueva, onUsuario, extra }: { icono: IconoNombre; titulo: string; sub: string; onNueva: () => void; onUsuario: () => void; extra?: React.ReactNode }) {
  return (
    <header className="enc">
      <div className="enc-t">
        <span className="enc-i"><Icono n={icono} tam={30} /></span>
        <div><h1>{titulo}</h1><p>{sub}</p></div>
      </div>
      <div className="enc-a">
        {extra}
        <button className="pildora" onClick={onNueva}><Icono n="chat" tam={16} />Nueva conversación</button>
        <button className="avatar-b" onClick={onUsuario} aria-label="Mi cuenta"><Icono n="perfil" tam={20} /></button>
      </div>
    </header>
  )
}

function Bloqueado({ texto, boton, onIr }: { texto: string; boton: string; onIr: () => void }) {
  return (
    <div className="vacio tarjeta">
      <Robot tam={120} medio />
      <p>{texto}</p>
      <button className="primario" onClick={onIr}>{boton}</button>
    </div>
  )
}

function Plegable({ icono, titulo, sub, children }: { icono: IconoNombre; titulo: string; sub: string; children: React.ReactNode }) {
  const [abierto, setAbierto] = useState(false)
  return (
    <div className="tarjeta plegable">
      <button className="plegable-c" onClick={() => setAbierto(!abierto)} aria-expanded={abierto}>
        <span className="ico-n"><Icono n={icono} tam={26} /></span>
        <span className="plegable-t"><b>{titulo}</b><small>{sub}</small></span>
        <span className="mas"><Icono n={abierto ? 'menos' : 'mas'} tam={20} /></span>
      </button>
      {abierto && <div className="plegable-d">{children}</div>}
    </div>
  )
}

const etiquetaATS = (p: number): [string, string] => (p >= 80 ? ['Excelente', 'ok'] : p >= 60 ? ['Buena', 'ok'] : ['A mejorar', 'aviso'])

// ---------- aplicación ----------
export default function App() {
  const [vista, setVista] = useState<Vista>('inicio')
  const [mensajes, setMensajes] = useState<Mensaje[]>([])
  const [estado, setEstado] = useState<Estado>('perfilamiento')
  const [analisis, setAnalisis] = useState<Analisis | null>(null)
  const [perfil, setPerfil] = useState<Perfil | null>(null)
  const [sid, setSid] = useState<string | null>(null)
  const [texto, setTexto] = useState('')
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [menu, setMenu] = useState(false)
  const [arrastrando, setArrastrando] = useState(false)
  const [todas, setTodas] = useState(false)
  const [paso, setPaso] = useState<number | null>(null)
  const fin = useRef<HTMLDivElement>(null)
  const archivo = useRef<HTMLInputElement>(null)

  const sincronizar = useCallback(async (id: string) => {
    const s = await cargarSesion(id)
    setMensajes(s.mensajes); setEstado(s.estado); setAnalisis(s.analisis); setPerfil(s.perfil)
  }, [])

  const empezar = useCallback(async () => {
    setCargando(true); setError(''); setMenu(false)
    try {
      const r = await crearSesion()
      guardarSesion(r.session_id!)
      setSid(r.session_id!); setMensajes([{ rol: 'bot', contenido: r.response }]); setEstado(r.estado); setAnalisis(null); setPerfil(null); setVista('inicio')
    } catch (e) { setError((e as Error).message) } finally { setCargando(false) }
  }, [])

  // Al abrir: si hay una sesión guardada se retoma; si no (o venció), se crea una nueva.
  useEffect(() => {
    const previa = getSesion()
    if (!previa) { void empezar(); return }
    sincronizar(previa).then(() => { setSid(previa); setCargando(false) }).catch(() => { olvidarSesion(); void empezar() })
  }, [empezar, sincronizar])

  useEffect(() => { fin.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [mensajes, cargando, vista])

  const aplicar = useCallback(async (r: Respuesta, id: string) => {
    setMensajes(m => [...m, { rol: 'bot', contenido: r.response }])
    setEstado(r.estado)
    if (r.analisis) setAnalisis(r.analisis)
    try { await sincronizar(id) } catch { /* se mantiene lo que ya hay en pantalla */ }
  }, [sincronizar])

  async function enviar(contenido: string) {
    const t = contenido.trim()
    if (!t || !sid || cargando) return
    setVista('inicio'); setTexto(''); setError(''); setCargando(true)
    setMensajes(m => [...m, { rol: 'user', contenido: t }])
    try { await aplicar(await enviarMensaje(sid, t), sid) } catch (e) { setError((e as Error).message) } finally { setCargando(false) }
  }

  async function elegirCV(f: File | undefined) {
    if (!f || !sid) return
    setError(''); setCargando(true)
    setMensajes(m => [...m, { rol: 'user', contenido: '📎 ' + f.name }])
    try {
      await aplicar(await subirCV(sid, f), sid)
      setVista('asesorias')
    } catch (e) {
      // El backend explica qué pasó con el archivo (formato no permitido, vacío, escaneado…) y se vuelve a pedir
      const err = e as Error & { cuerpo?: Respuesta; status?: number }
      if (err.status === 422 && err.cuerpo?.response) { await aplicar(err.cuerpo, sid); setError(err.cuerpo.response) } else setError(err.message)
    } finally { setCargando(false); if (archivo.current) archivo.current.value = '' }
  }

  function soltar(e: DragEvent) { e.preventDefault(); setArrastrando(false); void elegirCV(e.dataTransfer.files?.[0]) }

  async function borrarTodo() {
    setMenu(false)
    if (!sid || !window.confirm('Se borrarán tu conversación, tu CV y tu análisis. ¿Seguro?')) return
    try { await borrarSesion(sid) } catch { /* si ya no existe, igual se reinicia */ }
    olvidarSesion(); setSid(null); void empezar()
  }

  const ir = (v: Vista) => { setVista(v); setMenu(false) }
  const comunes = { onNueva: () => void empezar(), onUsuario: () => setMenu(!menu) }
  const inputArchivo = (
    <input ref={archivo} type="file" hidden accept=".pdf,.docx,.doc,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={e => void elegirCV(e.target.files?.[0])} />
  )
  const puedeAdjuntar = estado !== 'perfilamiento'
  const portada = mensajes.length <= 1 && !analisis

  // ---------- vistas ----------
  const inicio = (
    <section className={'panel inicio' + (portada ? ' portada' : '')}>
      <div className="olas" aria-hidden="true" />
      <div className="inicio-barra">
        <button className="pildora" onClick={() => void empezar()}><Icono n="chat" tam={16} />Nueva conversación</button>
        <button className="avatar-b" onClick={() => setMenu(!menu)} aria-label="Mi cuenta"><Icono n="perfil" tam={20} /></button>
      </div>
      {portada ? (
        <div className="hero">
          <div className="hero-robot"><Robot tam={340} saluda /></div>
          <div className="hero-texto">
            <h1>¡Hola! <span aria-hidden="true">👋</span></h1>
            <p>Soy <b>Laborea IA</b>, tu asistente para impulsar tu desarrollo profesional.</p>
            <div className="burbuja-hero"><Icono n="objetivo" tam={34} /><span>{mensajes[0]?.contenido.split('\n\n').pop() || '¿En qué puedo ayudarte hoy?'}</span></div>
          </div>
        </div>
      ) : (
        <div className="chat" aria-live="polite">
          {mensajes.map((m, i) => (
            <div key={i} className={'fila ' + m.rol}>
              {m.rol === 'bot' && <span className="mini-logo">L</span>}
              <div className={'burbuja ' + m.rol}>{m.contenido}</div>
            </div>
          ))}
          {cargando && <div className="fila bot"><span className="mini-logo">L</span><div className="burbuja bot pensando"><i /><i /><i /></div></div>}
          <div ref={fin} />
        </div>
      )}
      {error && <div className="error" role="alert">{error}</div>}
      <div className="pie">
        {estado === 'analizado' && !portada && <div className="chips">{SUGERENCIAS.map(s => <button key={s} onClick={() => void enviar(s)} disabled={cargando}>{s}</button>)}</div>}
        <form className="barra-msj" onSubmit={e => { e.preventDefault(); void enviar(texto) }}>
          <button type="button" className={'clip' + (estado === 'esperando_cv' ? ' latido' : '')} onClick={() => archivo.current?.click()} disabled={!puedeAdjuntar || cargando}
            aria-label="Adjuntar CV" title={puedeAdjuntar ? 'Adjuntar CV (PDF o Word, hasta 5 MB)' : 'Primero respondé las 3 preguntas'}><Icono n="clip" tam={24} /></button>
          <input className="campo" value={texto} onChange={e => setTexto(e.target.value)} placeholder="Escribí tu mensaje…" maxLength={2000} disabled={cargando || !sid} aria-label="Mensaje" />
          <button type="submit" className="enviar" disabled={cargando || !texto.trim()} aria-label="Enviar"><Icono n="enviar" tam={22} /></button>
        </form>
        <p className="legal">No compartas DNI, tarjetas ni contraseñas. Tu CV se envía a la IA sin email ni teléfono, y podés borrar tus datos cuando quieras.</p>
      </div>
    </section>
  )

  const habilidades = analisis ? [...analisis.hard_skills.map(h => h.nombre), ...analisis.soft_skills.map(s => s.nombre)] : []
  const experiencias = analisis?.experiencias.filter(x => x.resumen || x.rol) ?? []
  const vistaPerfil = (
    <section className="panel">
      <Encabezado icono="perfil" titulo="Mi perfil" sub="Conocé tu perfil y potenciá tus oportunidades." {...comunes} />
      <div className="perfil-cab tarjeta">
        <span className="foto"><Icono n="perfil" tam={46} trazo={2.2} /></span>
        <div><b>{analisis?.puesto.titulo || perfil?.puesto || 'Todavía no me contaste tu objetivo'}</b><small>{analisis ? `Match estimado con el mercado: ${analisis.match_score}%` : 'Completá tu perfil en Inicio y subí tu CV.'}</small></div>
      </div>
      <div className="dos">
        <div className="tarjeta">
          <h2><span className="ico-n"><Icono n="estrella" tam={24} /></span>Habilidades</h2>
          {habilidades.length ? (
            <div className="fichas">{(todas ? habilidades : habilidades.slice(0, 6)).map(h => <span key={h} className="ficha">{h}</span>)}</div>
          ) : <p className="suave">Aparecen cuando analizamos tu CV.</p>}
          {habilidades.length > 6 && <button className="enlace" onClick={() => setTodas(!todas)}>{todas ? 'Ver menos' : 'Ver todas'} <Icono n="flecha" tam={16} /></button>}
        </div>
        <div className="tarjeta objetivo">
          <h2><span className="ico-n"><Icono n="objetivo" tam={24} /></span>Mi objetivo profesional</h2>
          <p>{perfil?.meta || 'Contame tu meta profesional en la conversación de Inicio.'}</p>
          <div className="barritas" aria-hidden="true"><i /><i /><i /><i /></div>
        </div>
      </div>
      <Plegable icono="maletin" titulo="Experiencia" sub="Sumá tu experiencia laboral o proyectos.">
        {experiencias.length ? <ul>{experiencias.map((x, i) => <li key={i}>{[x.rol, x.organizacion, x.periodo].filter(Boolean).join(' · ')} {x.resumen}</li>)}</ul> : <p>{perfil?.proyectos || 'Cuando analicemos tu CV vas a ver acá tu experiencia.'}</p>}
      </Plegable>
      <Plegable icono="birrete" titulo="Formación" sub="Agregá tus estudios y certificaciones.">
        <p>Los estudios y certificaciones los toma el análisis desde tu CV. Si no figuran, sumalos al documento y volvé a subirlo en «Mi CV».</p>
      </Plegable>
    </section>
  )

  const [etq, tono] = analisis ? etiquetaATS(analisis.desglose.ats_pct) : ['', '']
  const vistaCV = (
    <section className="panel">
      <Encabezado icono="cv" titulo="Mi CV" sub="Analizá y optimizá tu currículum." {...comunes}
        extra={<button className="pildora" onClick={() => archivo.current?.click()} disabled={!puedeAdjuntar || cargando}><Icono n="nube" tam={16} />Subir nuevo CV</button>} />
      {estado === 'perfilamiento' ? (
        <Bloqueado texto="Antes de subir tu CV respondé las 3 preguntas de Inicio. Así lo comparo con tu objetivo." boton="Ir a Inicio" onIr={() => ir('inicio')} />
      ) : (
        <>
          <div className={'soltar tarjeta' + (arrastrando ? ' sobre' : '')} onDragOver={e => { e.preventDefault(); setArrastrando(true) }} onDragLeave={() => setArrastrando(false)} onDrop={soltar}
            onClick={() => archivo.current?.click()} role="button" tabIndex={0} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') archivo.current?.click() }}>
            <span className="nube"><Icono n="nube" tam={64} trazo={1.5} /></span>
            <b>{cargando ? 'Analizando tu CV…' : 'Arrastrá tu CV aquí'}</b>
            <span className="link">o seleccioná un archivo</span>
            <small>Formatos aceptados: PDF, Word (DOCX, DOC) · Máx. 5 MB</small>
          </div>
          {error && <div className="error" role="alert">{error}</div>}
          <div className="tarjeta">
            <h2>Estado del análisis</h2>
            {analisis ? (
              <div className="estado-cv">
                <Anillo valor={analisis.desglose.ats_pct} tam={104} />
                <div>
                  <b>Compatibilidad ATS</b>
                  <span className={'sello ' + tono}><Icono n="check" tam={16} trazo={3} />{etq}</span>
                  {analisis.problemas_ats.length > 0 && <button className="enlace" onClick={() => setPaso(paso === 10 ? null : 10)}>Ver detalles <Icono n="flecha" tam={16} /></button>}
                </div>
              </div>
            ) : <p className="suave">Todavía no subiste tu CV. Arrastralo arriba para empezar.</p>}
            {paso === 10 && analisis && <ul className="detalles">{analisis.problemas_ats.map(p => <li key={p}>{p}</li>)}</ul>}
          </div>
          {analisis && (
            <div className="tarjeta resumen-t">
              <h2>Resumen de análisis</h2>
              <div className="tres">
                <div><Icono n="estrella" tam={26} /><b>Fortalezas</b><small>{analisis.compatibles.length} habilidades clave</small></div>
                <div><Icono n="asesorias" tam={26} /><b>Áreas a mejorar</b><small>{analisis.skills_gap.length} puntos a potenciar</small></div>
                <div><Icono n="foco" tam={26} /><b>Recomendaciones</b><small>{analisis.plan_estudio_json.length} sugerencias personalizadas</small></div>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  )

  const vistaAsesorias = (
    <section className="panel">
      <Encabezado icono="asesorias" titulo="Mis asesorías" sub="Recibí un diagnóstico completo y recomendaciones personalizadas." {...comunes} />
      {!analisis ? (
        <Bloqueado texto="Todavía no tengo tu diagnóstico. Subí tu CV y te lo preparo." boton="Ir a Mi CV" onIr={() => ir('cv')} />
      ) : (
        <>
          <div className="tarjeta match">
            <Anillo valor={analisis.match_score} tam={150} grosor={14} />
            <div>
              <h2>Match con el mercado <span className="info" tabIndex={0} title={analisis.aviso}><Icono n="info" tam={18} /></span></h2>
              <p className="suave">Tu perfil frente a «{analisis.puesto.titulo}». {analisis.aviso}</p>
              <small className="modo">{analisis.modo === 'gemini' ? 'Análisis con IA' : 'Análisis por reglas'}</small>
            </div>
          </div>
          <div className="tarjeta">
            <h2>Tu perfil en detalle</h2>
            {([['Hard Skills', analisis.desglose.hard_pct], ['Soft Skills', analisis.desglose.soft_pct], ['Skills Gap', analisis.desglose.gap_pct]] as const).map(([n, v]) => (
              <div className="barra-fila" key={n}><span>{n}</span><div className="pista"><i style={{ width: v + '%' }} /></div><b>{v}%</b></div>
            ))}
          </div>
          <button className="tarjeta clave" onClick={() => ir('plan')}>
            <span className="ico-n"><Icono n="foco" tam={30} /></span>
            <span><b>Recomendaciones clave</b><small>{analisis.resumen || (analisis.skills_gap.length ? `Priorizá ${analisis.skills_gap.slice(0, 3).map(g => g.habilidad).join(', ')} para subir tu match.` : 'Tu perfil está muy alineado: ¡ya podés postularte!')}</small></span>
            <Icono n="flecha" tam={22} />
          </button>
        </>
      )}
    </section>
  )

  const pasos = analisis ? [
    { t: 'Optimización de tu CV', d: 'Mejorá el formato y destacá tus habilidades.', b: 'Ver guía',
      c: analisis.problemas_ats.length ? <ul>{analisis.problemas_ats.map(p => <li key={p}>{p}</li>)}</ul> : <p>Tu CV no tiene problemas de formato importantes.</p> },
    { t: 'Formación recomendada', d: 'Cursos y recursos gratuitos para potenciar tu perfil.', b: 'Explorar',
      c: analisis.plan_estudio_json.length ? (
        <ol>
          {analisis.plan_estudio_json.map(p => {
            const lista = (p.recursos && p.recursos.length > 0) ? p.recursos : (p.recurso ? [p.recurso] : [])
            return (
              <li key={p.orden}>
                <b>{p.habilidad}</b> <small>(~{p.duracion_semanas} semanas)</small>
                <span>{p.accion}</span>
                {lista.length > 0 && (
                  <div className="opciones-cursos">
                    {lista.length > 1 && <small>Opciones de cursos para elegir:</small>}
                    <div className="lista-links">
                      {lista.map((r, ri) => (
                        <a key={ri} href={r.url} target="_blank" rel="noopener noreferrer" title={r.descripcion}>
                          {r.nombre}
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </li>
            )
          })}
        </ol>
      ) : <p>No encontré brechas importantes.</p> },
    { t: 'Preparación para entrevistas', d: 'Consejos y práctica para ganar confianza.', b: 'Practicar', q: '¿Cómo me preparo para la entrevista?' },
    { t: 'Postulación estratégica', d: 'Aplicá a las mejores oportunidades.', b: 'Buscar', q: '¿Cómo me postulo?' },
  ] : []
  const vistaPlan = (
    <section className="panel">
      <Encabezado icono="cohete" titulo="Plan de ataque" sub="Tu hoja de ruta para alcanzar tus objetivos." {...comunes} />
      {!analisis ? (
        <Bloqueado texto="Tu plan se arma con el análisis de tu CV. Subilo y empezamos." boton="Ir a Mi CV" onIr={() => ir('cv')} />
      ) : (
        <>
          <ol className="pasos tarjeta">
            {pasos.map((p, i) => (
              <li key={p.t}>
                <span className="num">{i + 1}</span>
                <div className="paso-c">
                  <div className="paso-f"><span><b>{p.t}</b><small>{p.d}</small></span>
                    <button className="mini" onClick={() => (p.q ? void enviar(p.q) : setPaso(paso === i ? null : i))}>{p.b}</button></div>
                  {paso === i && p.c && <div className="paso-d">{p.c}</div>}
                </div>
              </li>
            ))}
          </ol>
          <div className="animo"><span className="ico-n"><Icono n="trofeo" tam={34} /></span><span><b>¡Vos podés!</b><small>Estamos para acompañarte en cada paso.</small></span><div className="animo-r"><Robot tam={120} medio saluda /></div></div>
        </>
      )}
    </section>
  )

  const contenido = { inicio, perfil: vistaPerfil, cv: vistaCV, asesorias: vistaAsesorias, plan: vistaPlan }[vista]
  return (
    <div className="shell">
      {inputArchivo}
      <nav className="lateral" aria-label="Secciones">
        <div className="logo"><span className="logo-l">L</span><b>LABOREA</b></div>
        <ul>{NAV.map(n => (
          <li key={n.id}><button className={vista === n.id ? 'activo' : ''} onClick={() => ir(n.id)} aria-current={vista === n.id ? 'page' : undefined}><Icono n={n.icono} tam={22} /><span>{n.etiqueta}</span></button></li>
        ))}</ul>
        <button className="avatar-b abajo" onClick={() => setMenu(!menu)} aria-label="Mi cuenta"><Icono n="perfil" tam={22} /></button>
      </nav>
      <main>{contenido}</main>
      {menu && (
        <div className="menu" role="menu">
          <button role="menuitem" onClick={() => void empezar()}>Nueva conversación</button>
          <button role="menuitem" className="peligro" onClick={() => void borrarTodo()}>Borrar mis datos</button>
          <small>Conversación anónima: no hace falta registrarse.</small>
        </div>
      )}
    </div>
  )
}
