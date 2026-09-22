/* 🐢 Tartaruga — Escudo dos Princípios. O Operador: quem executa a instrução.
   Adereço: o escudo — os dez princípios que valem para todo tratamento.
   Sem orelhas: partes ausentes são simplesmente ignoradas pelo runtime. */
Estudio.Rig.registrar({
  id: 'tartaruga', nome: 'Tartaruga', epiteto: 'Escudo dos Princípios', ator: 'Operador',
  viewBox: [0, 0, 200, 320], escalaNatural: 0.84,

  paleta:       { base: '#5aa07d', claro: '#dff0e6', escuro: '#1f5c42',
                  detalhe: '#2f7d5c', olho: '#ffffff', pupila: '#12261d' },
  paletaEscura: { base: '#7cc6a0', claro: '#e4f2ea', escuro: '#2e7d5c',
                  detalhe: '#63b78d', olho: '#ffffff', pupila: '#10201a' },

  markup:
    '<g data-part="perna-l"><rect x="60" y="248" width="26" height="56" rx="13" fill="var(--p-base)"/>' +
      '<ellipse cx="73" cy="308" rx="18" ry="10" fill="var(--p-base)"/></g>' +
    '<g data-part="perna-r"><rect x="114" y="248" width="26" height="56" rx="13" fill="var(--p-base)"/>' +
      '<ellipse cx="127" cy="308" rx="18" ry="10" fill="var(--p-base)"/></g>' +
    '<g data-part="braco-l"><rect x="30" y="180" width="24" height="70" rx="12" fill="var(--p-base)"/>' +
      '<ellipse cx="42" cy="252" rx="15" ry="11" fill="var(--p-base)"/></g>' +
    /* O casco É o corpo. As placas em --p-escuro são a marca do personagem. */
    '<g data-part="corpo">' +
      '<ellipse cx="100" cy="206" rx="64" ry="58" fill="var(--p-escuro)"/>' +
      '<ellipse cx="100" cy="206" rx="52" ry="46" fill="var(--p-detalhe)"/>' +
      '<path d="M100 166 76 182v30l24 16 24-16v-30z" fill="var(--p-escuro)"/>' +
      '<ellipse cx="100" cy="242" rx="34" ry="18" fill="var(--p-claro)"/>' +
    '</g>' +
    '<g data-part="braco-r"><rect x="146" y="180" width="24" height="70" rx="12" fill="var(--p-base)"/>' +
      '<ellipse cx="158" cy="252" rx="15" ry="11" fill="var(--p-base)"/>' +
      '<g data-part="adereco">' +
        '<path d="M158 186l26 9v24c0 15-12 24-26 30-14-6-26-15-26-30v-24z" fill="var(--p-claro)"' +
          ' stroke="var(--p-escuro)" stroke-width="4"/>' +
        '<path d="M158 202v34M144 214h28" stroke="var(--p-detalhe)" stroke-width="4" stroke-linecap="round"/>' +
      '</g></g>' +
    '<g data-part="cabeca">' +
      '<rect x="86" y="126" width="28" height="30" rx="12" fill="var(--p-base)"/>' +
      '<ellipse cx="100" cy="100" rx="44" ry="42" fill="var(--p-base)"/>' +
      '<g data-part="olho-l"><ellipse cx="82" cy="96" rx="13" ry="14" fill="var(--p-olho)"/>' +
        '<g data-part="pupila-l"><circle cx="82" cy="96" r="6.5" fill="var(--p-pupila)"/></g></g>' +
      '<g data-part="olho-r"><ellipse cx="118" cy="96" rx="13" ry="14" fill="var(--p-olho)"/>' +
        '<g data-part="pupila-r"><circle cx="118" cy="96" r="6.5" fill="var(--p-pupila)"/></g></g>' +
      '<g data-part="palpebra-l"><rect x="67" y="64" width="30" height="20" rx="5" fill="var(--p-base)"/></g>' +
      '<g data-part="palpebra-r"><rect x="103" y="64" width="30" height="20" rx="5" fill="var(--p-base)"/></g>' +
      '<g data-part="sobrancelha-l"><rect x="70" y="70" width="24" height="5" rx="2.5" fill="var(--p-escuro)"/></g>' +
      '<g data-part="sobrancelha-r"><rect x="106" y="70" width="24" height="5" rx="2.5" fill="var(--p-escuro)"/></g>' +
      '<g data-part="boca"><path d="M89 124q11 9 22 0" stroke="var(--p-escuro)" stroke-width="3.5"' +
        ' fill="none" stroke-linecap="round"/></g>' +
    '</g>',

  origens: {
    'perna-l': [73, 252], 'perna-r': [127, 252], 'corpo': [100, 206],
    'braco-l': [42, 186], 'braco-r': [158, 186], 'adereco': [158, 216], 'cabeca': [100, 150],
    'olho-l': [82, 96], 'olho-r': [118, 96], 'pupila-l': [82, 96], 'pupila-r': [118, 96],
    'palpebra-l': [82, 82], 'palpebra-r': [118, 82],
    'sobrancelha-l': [82, 72], 'sobrancelha-r': [118, 72], 'boca': [100, 125]
  },
  ancoras: { 'olhar': [100, 96], 'mao-l': [42, 252], 'mao-r': [158, 252],
             'fala': [150, 58], 'topo': [100, 58] },

  poses: {
    'neutro':     {},
    'apontando':  { 'braco-r': { rot: -50 }, 'cabeca': { rot: -5 } },
    'entregando': { 'braco-r': { rot: -74 }, 'braco-l': { rot: 16 }, 'cabeca': { rot: 4 } },
    /* A pose que define a Tartaruga: o escudo sobe na frente do corpo. */
    'protegendo': { 'braco-r': { rot: 28, x: -16, y: -26 }, 'braco-l': { rot: -30 }, 'cabeca': { y: 6 },
                    'corpo': { sy: .98 } },
    'andando':    { 'perna-l': { rot: 16 }, 'perna-r': { rot: -16 }, 'corpo': { y: -3 },
                    'braco-l': { rot: -12 }, 'braco-r': { rot: 12 } }
  },
  expressoes: {
    'neutro':     {},
    'preocupado': { 'sobrancelha-l': { rot: 16 }, 'sobrancelha-r': { rot: -16 },
                    'palpebra-l': { y: 9 }, 'palpebra-r': { y: 9 }, 'boca': { sy: -.9, y: 3 } },
    'feliz':      { 'boca': { sy: 1.4, sx: 1.1 }, 'palpebra-l': { y: 7 }, 'palpebra-r': { y: 7 } },
    'surpreso':   { 'olho-l': { s: 1.2 }, 'olho-r': { s: 1.2 }, 'palpebra-l': { y: -6 },
                    'palpebra-r': { y: -6 }, 'boca': { s: 1.3 }, 'cabeca': { y: -4 } }
  },
  estados: { 'normal': {}, 'apagado': { op: .32 } },

  hitbox: [30, 58, 140, 262]
});
