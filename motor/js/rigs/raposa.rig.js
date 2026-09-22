/* 🦊 Raposa — Elo de Confiança. Titular e Encarregado (DPO).
   Adereço: a chave — o direito que se exerce, a porta que se abre.
   Zero hex no markup: toda cor é var(--p-*), escrita por rig.js na raiz. */
Estudio.Rig.registrar({
  id: 'raposa', nome: 'Raposa', epiteto: 'Elo de Confiança', ator: 'Titular / Encarregado',
  viewBox: [0, 0, 200, 320], escalaNatural: 0.88,

  paleta:       { base: '#c1502e', claro: '#fbe8d6', escuro: '#8f3a1f',
                  detalhe: '#e6b34a', olho: '#ffffff', pupila: '#2a1810' },
  paletaEscura: { base: '#e2825c', claro: '#f7e3d5', escuro: '#a85736',
                  detalhe: '#efc76a', olho: '#ffffff', pupila: '#241610' },
  /* Tingimento do Encarregado: a mesma raposa, em tom institucional. */
  alt:          { base: '#a8703f', escuro: '#7a4e29', detalhe: '#8a5a9e' },

  markup:
    /* Ordem de desenho = ordem de z. Cauda atras de tudo; os DOIS bracos
       depois do corpo, senao um deles some dentro da elipse. */
    '<g data-part="cauda">' +
      '<path d="M142 240c34 6 56-20 52-52-3-22-22-30-36-20-12 9-16 34-16 72z" fill="var(--p-base)"/>' +
      '<ellipse cx="176" cy="172" rx="15" ry="12" transform="rotate(-40 176 172)" fill="var(--p-claro)"/>' +
    '</g>' +
    '<g data-part="perna-l"><rect x="75" y="242" width="19" height="66" rx="9" fill="var(--p-escuro)"/>' +
      '<ellipse cx="84" cy="311" rx="15" ry="9" fill="var(--p-pupila)"/></g>' +
    '<g data-part="perna-r"><rect x="106" y="242" width="19" height="66" rx="9" fill="var(--p-escuro)"/>' +
      '<ellipse cx="116" cy="311" rx="15" ry="9" fill="var(--p-pupila)"/></g>' +
    '<g data-part="corpo"><ellipse cx="100" cy="206" rx="54" ry="62" fill="var(--p-base)"/>' +
      '<ellipse cx="100" cy="220" rx="34" ry="44" fill="var(--p-claro)"/></g>' +
    '<g data-part="braco-l"><rect x="32" y="156" width="19" height="92" rx="9.5" fill="var(--p-escuro)"/>' +
      '<ellipse cx="41.5" cy="250" rx="13" ry="9" fill="var(--p-pupila)"/>' +
      '<g data-part="adereco">' +
        '<circle cx="30" cy="236" r="10" fill="none" stroke="var(--p-detalhe)" stroke-width="5.5"/>' +
        '<path d="M30 246v22" stroke="var(--p-detalhe)" stroke-width="5.5" stroke-linecap="round"/>' +
        '<path d="M30 261h10" stroke="var(--p-detalhe)" stroke-width="4.5" stroke-linecap="round"/>' +
      '</g></g>' +
    '<g data-part="braco-r"><rect x="149" y="156" width="19" height="92" rx="9.5" fill="var(--p-escuro)"/>' +
      '<ellipse cx="158.5" cy="250" rx="13" ry="9" fill="var(--p-pupila)"/></g>' +
    '<g data-part="cabeca">' +
      '<g data-part="orelha-l"><path d="M52 64 40 16 82 46z" fill="var(--p-base)"/>' +
        '<path d="M56 58 50 30 72 48z" fill="var(--p-escuro)"/></g>' +
      '<g data-part="orelha-r"><path d="M148 64 160 16 118 46z" fill="var(--p-base)"/>' +
        '<path d="M144 58 150 30 128 48z" fill="var(--p-escuro)"/></g>' +
      '<path d="M100 40c38 0 52 26 52 52 0 28-24 50-52 50S48 120 48 92c0-26 14-52 52-52z" fill="var(--p-base)"/>' +
      '<path d="M100 96c16 0 24 12 24 24 0 14-12 24-24 24s-24-10-24-24c0-12 8-24 24-24z" fill="var(--p-claro)"/>' +
      '<g data-part="olho-l"><ellipse cx="78" cy="88" rx="13" ry="14" fill="var(--p-olho)"/>' +
        '<g data-part="pupila-l"><circle cx="78" cy="88" r="6.5" fill="var(--p-pupila)"/></g></g>' +
      '<g data-part="olho-r"><ellipse cx="122" cy="88" rx="13" ry="14" fill="var(--p-olho)"/>' +
        '<g data-part="pupila-r"><circle cx="122" cy="88" r="6.5" fill="var(--p-pupila)"/></g></g>' +
      '<g data-part="palpebra-l"><rect x="63" y="54" width="30" height="22" rx="5" fill="var(--p-base)"/></g>' +
      '<g data-part="palpebra-r"><rect x="107" y="54" width="30" height="22" rx="5" fill="var(--p-base)"/></g>' +
      '<g data-part="sobrancelha-l"><rect x="67" y="60" width="22" height="4" rx="2" fill="var(--p-escuro)"/></g>' +
      '<g data-part="sobrancelha-r"><rect x="111" y="60" width="22" height="4" rx="2" fill="var(--p-escuro)"/></g>' +
      '<ellipse cx="100" cy="116" rx="8" ry="6" fill="var(--p-pupila)"/>' +
      '<g data-part="boca"><path d="M90 128q10 8 20 0" stroke="var(--p-pupila)" stroke-width="3"' +
        ' fill="none" stroke-linecap="round"/></g>' +
    '</g>',

  origens: {
    'cauda': [146, 236], 'perna-l': [84, 246], 'perna-r': [116, 246], 'corpo': [100, 206],
    'braco-l': [41.5, 164], 'braco-r': [158.5, 164], 'adereco': [30, 236], 'cabeca': [100, 132],
    'orelha-l': [66, 58], 'orelha-r': [134, 58], 'olho-l': [78, 88], 'olho-r': [122, 88],
    'pupila-l': [78, 88], 'pupila-r': [122, 88], 'palpebra-l': [78, 74], 'palpebra-r': [122, 74],
    'sobrancelha-l': [78, 62], 'sobrancelha-r': [122, 62], 'boca': [100, 129]
  },
  ancoras: { 'olhar': [100, 88], 'mao-l': [41.5, 250], 'mao-r': [158.5, 250],
             'fala': [152, 48], 'topo': [100, 16] },

  poses: {
    'neutro':     {},
    'apontando':  { 'braco-r': { rot: -48 }, 'cabeca': { rot: -5 }, 'cauda': { rot: -8 } },
    'entregando': { 'braco-r': { rot: -74 }, 'braco-l': { rot: -14 }, 'corpo': { x: 4 },
                    'cabeca': { rot: 4 } },
    'protegendo': { 'braco-l': { rot: -34 }, 'braco-r': { rot: 34 }, 'corpo': { sy: .97 },
                    'cabeca': { y: 3 }, 'cauda': { rot: 12 } },
    'andando':    { 'perna-l': { rot: 18 }, 'perna-r': { rot: -18 }, 'corpo': { y: -3 },
                    'cauda': { rot: 6 } }
  },
  expressoes: {
    'neutro':     {},
    'preocupado': { 'sobrancelha-l': { rot: 17 }, 'sobrancelha-r': { rot: -17 },
                    'orelha-l': { rot: 24 }, 'orelha-r': { rot: -24 },
                    'palpebra-l': { y: 8 }, 'palpebra-r': { y: 8 }, 'boca': { sy: -.9, y: 3 } },
    'feliz':      { 'boca': { sy: 1.4 }, 'palpebra-l': { y: 6 }, 'palpebra-r': { y: 6 },
                    'orelha-l': { rot: -8 }, 'orelha-r': { rot: 8 } },
    'surpreso':   { 'olho-l': { s: 1.2 }, 'olho-r': { s: 1.2 }, 'boca': { s: 1.3 },
                    'palpebra-l': { y: -5 }, 'palpebra-r': { y: -5 },
                    'orelha-l': { rot: -14 }, 'orelha-r': { rot: 14 } }
  },
  estados: { 'normal': {}, 'apagado': { op: .32 } },

  hitbox: [30, 14, 140, 306],

  /* Voz — atributo do personagem, como a paleta (CP-004). Parâmetros de
     partida do Apêndice A; `dublar` traduz ritmo em length_scale do Piper.
     Pitch é dado declarado: deslocá-lo exigiria reamostrar, e reamostrar é
     proibido. Sem cliente no motor — quem lê é o estudio_suite.
     A Raposa tem DOIS registros: o mesmo corpo, dois papéis — como o
     tingimento `alt` marca o Encarregado na arte, `registros` o marca na
     voz. O registro entra por papel do elenco do filme. */
  voz: {
    registro: 'ágil, calorosa, curiosa',
    pitch: 'mais-agudo', ritmo: 0.05,
    registros: {
      titular:     { pitch: 'mais-agudo', ritmo: 0.05 },
      encarregado: { pitch: 'medio', ritmo: 0, variacao: 'pouca' }
    }
  }
});
