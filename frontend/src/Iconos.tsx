// Íconos de línea (trazo redondeado). Se dibujan en línea para no depender de librerías externas.
const D = {
  inicio: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  perfil: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0',
  cv: 'M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z M14 3v5h5 M9 13h6 M9 17h6',
  asesorias: 'M4 20V11 M10 20V4 M16 20v-6 M22 20H2',
  plan: 'M9 4h6v3H9z M7 5.5H5V21h14V5.5h-2 M9 14l2 2 4-4',
  clip: 'm21 11-8.6 8.6a5 5 0 0 1-7.1-7.1l8.6-8.6a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.6a1.7 1.7 0 0 1-2.4-2.4l7.9-7.9',
  enviar: 'M21 3 10 14 M21 3l-7 18-4-8-8-4z',
  objetivo: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z',
  estrella: 'm12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z',
  maletin: 'M4 8h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z M9 8V5h6v3 M3 13h18',
  birrete: 'm2 9 10-5 10 5-10 5z M6 11.5V16c0 1.5 3 3 6 3s6-1.5 6-3v-4.5 M22 9v6',
  nube: 'M7 18a4 4 0 0 1-.6-8A6 6 0 0 1 18 9.5 4.3 4.3 0 0 1 17.5 18 M12 12v7 M9 15l3-3 3 3',
  check: 'M5 12.5 10 17.5 19 7.5',
  mas: 'M12 5v14 M5 12h14',
  menos: 'M5 12h14',
  flecha: 'M5 12h14 M13 6l6 6-6 6',
  cohete: 'M14 4c3-1 6-1 6-1s0 3-1 6l-6 6-5-5z M9 14l-4 1-2 4 4-2 1-4 M15 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2z',
  trofeo: 'M8 4h8v6a4 4 0 0 1-8 0z M8 6H4v1a4 4 0 0 0 4 4 M16 6h4v1a4 4 0 0 1-4 4 M12 14v4 M8 21h8 M10 18h4',
  foco: 'M9 18h6 M10 21h4 M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z',
  chat: 'M4 5h16v11H10l-5 4v-4H4z',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 11v5 M12 8h.01',
  lapiz: 'm4 20 1-4L16.5 4.5a2.1 2.1 0 0 1 3 3L8 19z',
} as const

export type IconoNombre = keyof typeof D

export default function Icono({ n, tam = 22, trazo = 1.9 }: { n: IconoNombre; tam?: number; trazo?: number }) {
  return (
    <svg width={tam} height={tam} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={trazo} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={D[n]} />
    </svg>
  )
}
