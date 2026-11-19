import { useId } from 'react'

// Mascota de Laborea IA: robot blanco con auriculares naranja y ojos azules.
export default function Robot({ tam = 220, saluda = false, medio = false }: { tam?: number; saluda?: boolean; medio?: boolean }) {
  const id = useId().replace(/:/g, '')
  return (
    <svg width={tam} height={tam * (medio ? 0.62 : 1.15)} viewBox={medio ? '0 20 200 124' : '0 0 200 230'} role="img" aria-label="Laborea IA, el asistente">
      <defs>
        <linearGradient id={`b${id}`} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ffffff" /><stop offset="1" stopColor="#e9edf5" /></linearGradient>
        <linearGradient id={`o${id}`} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ffa04a" /><stop offset="1" stopColor="#f26a00" /></linearGradient>
        <linearGradient id={`v${id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1b2a44" /><stop offset="1" stopColor="#0c1424" /></linearGradient>
        <filter id={`g${id}`} x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="d" /><feMerge><feMergeNode in="d" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        <filter id={`s${id}`} x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="6" stdDeviation="6" floodColor="#b45a14" floodOpacity=".22" /></filter>
      </defs>
      {!medio && (
        <g filter={`url(#s${id})`}>
          {/* cuerpo */}
          <rect x="58" y="146" width="84" height="72" rx="36" fill={`url(#b${id})`} />
          <rect x="82" y="168" width="36" height="36" rx="10" fill={`url(#o${id})`} />
          <text x="100" y="196" textAnchor="middle" fontFamily="Arial, sans-serif" fontWeight="800" fontSize="26" fill="#fff">L</text>
          {/* brazos */}
          <ellipse cx="52" cy="186" rx="13" ry="24" fill={`url(#b${id})`} transform="rotate(14 52 186)" />
          {saluda ? (
            <g transform="rotate(34 142 188)"><rect x="130" y="128" width="24" height="62" rx="12" fill={`url(#b${id})`} /><circle cx="142" cy="128" r="15" fill={`url(#b${id})`} /></g>
          ) : (
            <ellipse cx="148" cy="186" rx="13" ry="24" fill={`url(#b${id})`} transform="rotate(-14 148 186)" />
          )}
          <rect x="88" y="136" width="24" height="16" rx="6" fill="#cfd6e4" />
        </g>
      )}
      <g filter={`url(#s${id})`}>
        {/* diadema y auriculares */}
        <path d="M32 84C32 24 168 24 168 84" fill="none" stroke={`url(#o${id})`} strokeWidth="9" strokeLinecap="round" />
        <rect x="16" y="70" width="28" height="52" rx="14" fill={`url(#o${id})`} />
        <rect x="156" y="70" width="28" height="52" rx="14" fill={`url(#o${id})`} />
        {/* cabeza */}
        <rect x="34" y="42" width="132" height="104" rx="50" fill={`url(#b${id})`} />
        <rect x="52" y="62" width="96" height="62" rx="30" fill={`url(#v${id})`} />
        {/* ojos felices */}
        <g filter={`url(#g${id})`} fill="none" stroke="#3aa8ff" strokeWidth="7" strokeLinecap="round">
          <path d="M70 100Q79 84 88 100" /><path d="M112 100Q121 84 130 100" />
        </g>
        {/* micrófono */}
        <path d="M24 118Q30 146 66 140" fill="none" stroke="#2a3240" strokeWidth="3.5" strokeLinecap="round" />
        <circle cx="68" cy="140" r="4.5" fill="#2a3240" />
      </g>
    </svg>
  )
}
