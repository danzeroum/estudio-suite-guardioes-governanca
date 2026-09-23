/* 🦅 Águia — Visão de Fronteira. A ANPD: quem fiscaliza e confere.
   Adereço: a luneta — ver longe antes de deixar passar. */
Estudio.Rig.registrar({
  id: 'aguia', nome: 'Águia', epiteto: 'Visão de Fronteira', ator: 'ANPD',
  viewBox: [0, 0, 200, 320], escalaNatural: 0.96,

  paleta:       { base: '#1f6f8b', claro: '#dde9ee', escuro: '#0e3b47',
                  detalhe: '#e0a544', olho: '#ffffff', pupila: '#12262d' },
  paletaEscura: { base: '#5fa8c9', claro: '#e3eef3', escuro: '#2b6076',
                  detalhe: '#edbc63', olho: '#ffffff', pupila: '#10202a' },

  markup:
    '<g data-part="perna-l"><rect x="81" y="252" width="11" height="52" rx="5.5" fill="var(--p-detalhe)"/>' +
      '<path d="M70 310h32" stroke="var(--p-detalhe)" stroke-width="11" stroke-linecap="round"/></g>' +
    '<g data-part="perna-r"><rect x="108" y="252" width="11" height="52" rx="5.5" fill="var(--p-detalhe)"/>' +
      '<path d="M98 310h32" stroke="var(--p-detalhe)" stroke-width="11" stroke-linecap="round"/></g>' +
    '<g data-part="corpo"><ellipse cx="100" cy="202" rx="54" ry="62" fill="var(--p-base)"/>' +
      '</g>' +
    '<g data-part="braco-l"><path d="M72 150c-26 12-42 46-46 86-1 10 2 18 7 20 17-18 34-60 39-106z" fill="var(--p-escuro)"/></g>' +
    '<g data-part="braco-r"><path d="M128 150c26 12 42 46 46 86 1 10-2 18-7 20-17-18-34-60-39-106z" fill="var(--p-escuro)"/>' +
      '<g data-part="adereco">' +
        '<rect x="130" y="226" width="48" height="17" rx="8" transform="rotate(-20 154 234)" fill="var(--p-claro)"/>' +
        '<rect x="168" y="216" width="14" height="22" rx="5" transform="rotate(-20 175 227)" fill="var(--p-detalhe)"/>' +
      '</g></g>' +
    '<g data-part="cabeca">' +
      '<circle cx="100" cy="86" r="50" fill="var(--p-claro)"/>' +
      '' +
      '<g data-part="olho-l"><ellipse cx="78" cy="86" rx="14" ry="15" fill="var(--p-olho)"/>' +
        '<g data-part="pupila-l"><circle cx="78" cy="86" r="7" fill="var(--p-pupila)"/></g></g>' +
      '<g data-part="olho-r"><ellipse cx="122" cy="86" rx="14" ry="15" fill="var(--p-olho)"/>' +
        '<g data-part="pupila-r"><circle cx="122" cy="86" r="7" fill="var(--p-pupila)"/></g></g>' +
      '<g data-part="palpebra-l"><rect x="64" y="54" width="28" height="20" rx="5" fill="var(--p-claro)"/></g>' +
      '<g data-part="palpebra-r"><rect x="108" y="54" width="28" height="20" rx="5" fill="var(--p-claro)"/></g>' +
      /* Sobrancelha em cunha: e ela que da o olhar severo da ave de rapina. */
      '<g data-part="sobrancelha-l"><path d="M62 64 92 58v8l-30 7z" fill="var(--p-escuro)"/></g>' +
      '<g data-part="sobrancelha-r"><path d="M138 64 108 58v8l30 7z" fill="var(--p-escuro)"/></g>' +
      '<g data-part="boca"><path d="M84 102h32l-6 32c-2 10-6 16-10 16s-8-6-10-16z" fill="var(--p-detalhe)"/></g>' +
    '</g>',

  origens: {
    'perna-l': [86, 254], 'perna-r': [114, 254], 'corpo': [100, 202],
    'braco-l': [70, 156], 'braco-r': [130, 156], 'adereco': [156, 234], 'cabeca': [100, 132],
    'olho-l': [78, 86], 'olho-r': [122, 86], 'pupila-l': [78, 86], 'pupila-r': [122, 86],
    'palpebra-l': [78, 72], 'palpebra-r': [122, 72],
    'sobrancelha-l': [92, 62], 'sobrancelha-r': [108, 62], 'boca': [100, 104]
  },
  ancoras: { 'olhar': [100, 86], 'mao-l': [50, 250], 'mao-r': [150, 250],
             'fala': [152, 44], 'topo': [100, 36] },

  poses: {
    'neutro':     {},
    'apontando':  { 'braco-r': { rot: -44 }, 'cabeca': { rot: -6 } },
    'entregando': { 'braco-r': { rot: -68 }, 'braco-l': { rot: 14 }, 'corpo': { x: 3 } },
    'protegendo': { 'braco-l': { rot: -28 }, 'braco-r': { rot: 28 }, 'corpo': { sy: .97 } },
    /* Na Águia, 'andando' é o voo: as asas abrem e o corpo sobe. */
    'andando':    { 'braco-l': { rot: 54 }, 'braco-r': { rot: -54 }, 'corpo': { y: -10 },
                    'perna-l': { rot: 16 }, 'perna-r': { rot: -16 }, 'cabeca': { y: -4 } }
  },
  expressoes: {
    'neutro':     {},
    'preocupado': { 'sobrancelha-l': { rot: -14 }, 'sobrancelha-r': { rot: 14 },
                    'palpebra-l': { y: 8 }, 'palpebra-r': { y: 8 }, 'boca': { sy: .8 } },
    'feliz':      { 'palpebra-l': { y: 7 }, 'palpebra-r': { y: 7 }, 'sobrancelha-l': { rot: 10 },
                    'sobrancelha-r': { rot: -10 }, 'boca': { sx: 1.15 } },
    'surpreso':   { 'olho-l': { s: 1.2 }, 'olho-r': { s: 1.2 }, 'palpebra-l': { y: -6 },
                    'palpebra-r': { y: -6 }, 'sobrancelha-l': { y: -5 }, 'sobrancelha-r': { y: -5 },
                    'boca': { s: 1.2 } }
  },
  estados: { 'normal': {}, 'apagado': { op: .32 } },

  hitbox: [24, 30, 152, 290],

  /* Voz — atributo do personagem, como a paleta (CP-004). Parâmetros de
     partida do Apêndice A; `dublar` traduz ritmo em length_scale do Piper.
     Pitch é dado declarado: deslocá-lo exigiria reamostrar, e reamostrar é
     proibido. Sem cliente no motor — quem lê é o estudo_suite. */
  voz: {
    registro: 'autoritativa, torre de controle',
    pitch: 'medio-grave', ritmo: 0, variacao: 'pouca',
    timbre: { portadora: 'aguia-guincho', mistura: 0.35, bandas: 16 }
  }
});
