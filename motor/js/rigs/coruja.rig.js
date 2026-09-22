/* 🦉 Coruja — Bússola Ética. O Controlador: quem decide a finalidade.
   Adereço: a bússola — a direção que se escolhe antes de andar. */
Estudio.Rig.registrar({
  id: 'coruja', nome: 'Coruja', epiteto: 'Bússola Ética', ator: 'Controlador',
  viewBox: [0, 0, 200, 320], escalaNatural: 0.92,

  paleta:       { base: '#a8752a', claro: '#f6ead0', escuro: '#7d5518',
                  detalhe: '#c1502e', olho: '#ffffff', pupila: '#2a2118' },
  paletaEscura: { base: '#d99a45', claro: '#f7eddb', escuro: '#a06f28',
                  detalhe: '#e2825c', olho: '#ffffff', pupila: '#241d15' },

  markup:
    '<g data-part="perna-l"><rect x="80" y="254" width="11" height="50" rx="5.5" fill="var(--p-escuro)"/>' +
      '<path d="M70 310h32" stroke="var(--p-detalhe)" stroke-width="11" stroke-linecap="round"/></g>' +
    '<g data-part="perna-r"><rect x="109" y="254" width="11" height="50" rx="5.5" fill="var(--p-escuro)"/>' +
      '<path d="M98 310h32" stroke="var(--p-detalhe)" stroke-width="11" stroke-linecap="round"/></g>' +
    '<g data-part="corpo"><ellipse cx="100" cy="206" rx="58" ry="62" fill="var(--p-base)"/>' +
      '<ellipse cx="100" cy="222" rx="33" ry="40" fill="var(--p-claro)"/></g>' +
    '<g data-part="braco-l"><path d="M72 156c-20 6-30 32-30 58 0 19 7 34 16 40 10-18 16-54 14-98z" fill="var(--p-escuro)"/></g>' +
    '<g data-part="braco-r"><path d="M128 156c20 6 30 32 30 58 0 19-7 34-16 40-10-18-16-54-14-98z" fill="var(--p-escuro)"/>' +
      '<g data-part="adereco">' +
        '<circle cx="150" cy="240" r="14" fill="var(--p-claro)" stroke="var(--p-escuro)" stroke-width="4"/>' +
        '<path d="M144 248l6-17 6 17-6-6z" fill="var(--p-detalhe)"/>' +
      '</g></g>' +
    '<g data-part="cabeca">' +
      '<g data-part="orelha-l"><path d="M58 50 44 12 84 40z" fill="var(--p-base)"/></g>' +
      '<g data-part="orelha-r"><path d="M142 50 156 12 116 40z" fill="var(--p-base)"/></g>' +
      '<circle cx="100" cy="88" r="54" fill="var(--p-base)"/>' +
      '<path d="M100 38c30 0 47 22 47 49s-21 49-47 49-47-22-47-49 17-49 47-49z" fill="var(--p-claro)"/>' +
      '<g data-part="olho-l"><circle cx="76" cy="84" r="19" fill="var(--p-olho)"/>' +
        '<g data-part="pupila-l"><circle cx="76" cy="84" r="10" fill="var(--p-pupila)"/></g></g>' +
      '<g data-part="olho-r"><circle cx="124" cy="84" r="19" fill="var(--p-olho)"/>' +
        '<g data-part="pupila-r"><circle cx="124" cy="84" r="10" fill="var(--p-pupila)"/></g></g>' +
      '<g data-part="palpebra-l"><rect x="55" y="40" width="42" height="26" rx="6" fill="var(--p-claro)"/></g>' +
      '<g data-part="palpebra-r"><rect x="103" y="40" width="42" height="26" rx="6" fill="var(--p-claro)"/></g>' +
      '<g data-part="sobrancelha-l"><rect x="60" y="56" width="30" height="5" rx="2.5" fill="var(--p-escuro)"/></g>' +
      '<g data-part="sobrancelha-r"><rect x="110" y="56" width="30" height="5" rx="2.5" fill="var(--p-escuro)"/></g>' +
      '<g data-part="boca"><path d="M100 102 90 122h20z" fill="var(--p-detalhe)"/></g>' +
    '</g>',

  origens: {
    'perna-l': [86, 258], 'perna-r': [114, 258], 'corpo': [100, 206],
    'braco-l': [66, 162], 'braco-r': [134, 162], 'adereco': [150, 240], 'cabeca': [100, 136],
    'orelha-l': [70, 46], 'orelha-r': [130, 46], 'olho-l': [76, 84], 'olho-r': [124, 84],
    'pupila-l': [76, 84], 'pupila-r': [124, 84], 'palpebra-l': [76, 64], 'palpebra-r': [124, 64],
    'sobrancelha-l': [76, 58], 'sobrancelha-r': [124, 58], 'boca': [100, 104]
  },
  ancoras: { 'olhar': [100, 84], 'mao-l': [56, 248], 'mao-r': [144, 248],
             'fala': [154, 46], 'topo': [100, 12] },

  poses: {
    'neutro':     {},
    'apontando':  { 'braco-r': { rot: -46 }, 'cabeca': { rot: -5 } },
    'entregando': { 'braco-r': { rot: -70 }, 'braco-l': { rot: 12 }, 'corpo': { x: 3 },
                    'cabeca': { rot: 4 } },
    'protegendo': { 'braco-l': { rot: -30 }, 'braco-r': { rot: 30 }, 'corpo': { sy: .97 },
                    'cabeca': { y: 3 } },
    'andando':    { 'braco-l': { rot: -22 }, 'braco-r': { rot: 22 }, 'corpo': { y: -4 },
                    'perna-l': { rot: 14 }, 'perna-r': { rot: -14 } }
  },
  expressoes: {
    'neutro':     {},
    'preocupado': { 'sobrancelha-l': { rot: 18, y: 2 }, 'sobrancelha-r': { rot: -18, y: 2 },
                    'palpebra-l': { y: 10 }, 'palpebra-r': { y: 10 }, 'boca': { sy: .7 } },
    'feliz':      { 'palpebra-l': { y: 8 }, 'palpebra-r': { y: 8 }, 'boca': { sx: 1.2, sy: .8 },
                    'orelha-l': { rot: -10 }, 'orelha-r': { rot: 10 } },
    'surpreso':   { 'olho-l': { s: 1.15 }, 'olho-r': { s: 1.15 }, 'palpebra-l': { y: -6 },
                    'palpebra-r': { y: -6 }, 'boca': { s: 1.25 },
                    'orelha-l': { rot: -16 }, 'orelha-r': { rot: 16 } }
  },
  estados: { 'normal': {}, 'apagado': { op: .32 } },

  hitbox: [40, 12, 120, 308]
});
