/* 🐘 Elefante — Memória e Segurança. O registro que prova o que foi feito.
   Adereço: o livro de registro — Arts. 37 e 38.
   A tromba não é uma parte animada: ela acompanha a cabeça e, para este
   roteiro, nunca precisa se mover sozinha. Parte que não justifica
   movimento vira desenho estático. */
Estudio.Rig.registrar({
  id: 'elefante', nome: 'Elefante', epiteto: 'Memória e Segurança', ator: 'Registro e Segurança',
  viewBox: [0, 0, 200, 320], escalaNatural: 1,

  paleta:       { base: '#7d8695', claro: '#eceef1', escuro: '#4a515c',
                  detalhe: '#c9a227', olho: '#ffffff', pupila: '#20242b' },
  paletaEscura: { base: '#9aa3b0', claro: '#eef0f3', escuro: '#616a78',
                  detalhe: '#ddb948', olho: '#ffffff', pupila: '#1a1d23' },

  markup:
    '<g data-part="perna-l"><rect x="66" y="240" width="30" height="66" rx="13" fill="var(--p-base)"/>' +
      '<ellipse cx="81" cy="309" rx="21" ry="11" fill="var(--p-escuro)"/></g>' +
    '<g data-part="perna-r"><rect x="104" y="240" width="30" height="66" rx="13" fill="var(--p-base)"/>' +
      '<ellipse cx="119" cy="309" rx="21" ry="11" fill="var(--p-escuro)"/></g>' +
    '<g data-part="braco-l"><rect x="28" y="168" width="26" height="80" rx="13" fill="var(--p-base)"/>' +
      '<ellipse cx="41" cy="250" rx="16" ry="11" fill="var(--p-escuro)"/></g>' +
    '<g data-part="corpo"><ellipse cx="100" cy="200" rx="58" ry="60" fill="var(--p-base)"/>' +
      '<ellipse cx="100" cy="216" rx="36" ry="40" fill="var(--p-claro)"/></g>' +
    '<g data-part="braco-r"><rect x="146" y="168" width="26" height="80" rx="13" fill="var(--p-base)"/>' +
      '<ellipse cx="159" cy="250" rx="16" ry="11" fill="var(--p-escuro)"/>' +
      '<g data-part="adereco">' +
        '<rect x="150" y="208" width="46" height="38" rx="4" fill="var(--p-detalhe)"/>' +
        '<rect x="156" y="214" width="34" height="26" rx="2" fill="var(--p-claro)"/>' +
        '<path d="M162 221h22M162 228h22M162 235h14" stroke="var(--p-escuro)" stroke-width="3"' +
          ' stroke-linecap="round"/>' +
      '</g></g>' +
    '<g data-part="cabeca">' +
      '<g data-part="orelha-l"><ellipse cx="42" cy="92" rx="30" ry="36" fill="var(--p-base)"/>' +
        '<ellipse cx="46" cy="92" rx="19" ry="24" fill="var(--p-escuro)" opacity=".35"/></g>' +
      '<g data-part="orelha-r"><ellipse cx="158" cy="92" rx="30" ry="36" fill="var(--p-base)"/>' +
        '<ellipse cx="154" cy="92" rx="19" ry="24" fill="var(--p-escuro)" opacity=".35"/></g>' +
      '<ellipse cx="100" cy="88" rx="52" ry="50" fill="var(--p-base)"/>' +
      /* Tromba: desce da testa e encosta no peito. Estática, por escolha. */
      '<path d="M92 108c-2 22 0 38 8 48 7 8 18 6 20-4" stroke="var(--p-base)" stroke-width="22"' +
        ' fill="none" stroke-linecap="round"/>' +
      '<g data-part="olho-l"><ellipse cx="76" cy="80" rx="12" ry="13" fill="var(--p-olho)"/>' +
        '<g data-part="pupila-l"><circle cx="76" cy="80" r="6" fill="var(--p-pupila)"/></g></g>' +
      '<g data-part="olho-r"><ellipse cx="124" cy="80" rx="12" ry="13" fill="var(--p-olho)"/>' +
        '<g data-part="pupila-r"><circle cx="124" cy="80" r="6" fill="var(--p-pupila)"/></g></g>' +
      '<g data-part="palpebra-l"><rect x="62" y="50" width="28" height="20" rx="5" fill="var(--p-base)"/></g>' +
      '<g data-part="palpebra-r"><rect x="110" y="50" width="28" height="20" rx="5" fill="var(--p-base)"/></g>' +
      '<g data-part="sobrancelha-l"><rect x="64" y="56" width="24" height="5" rx="2.5" fill="var(--p-escuro)"/></g>' +
      '<g data-part="sobrancelha-r"><rect x="112" y="56" width="24" height="5" rx="2.5" fill="var(--p-escuro)"/></g>' +
      '<g data-part="boca"><path d="M78 118q8 7 16 2" stroke="var(--p-escuro)" stroke-width="3"' +
        ' fill="none" stroke-linecap="round"/></g>' +
    '</g>',

  origens: {
    'perna-l': [81, 244], 'perna-r': [119, 244], 'corpo': [100, 200],
    'braco-l': [41, 174], 'braco-r': [159, 174], 'adereco': [173, 227], 'cabeca': [100, 134],
    'orelha-l': [66, 92], 'orelha-r': [134, 92], 'olho-l': [76, 80], 'olho-r': [124, 80],
    'pupila-l': [76, 80], 'pupila-r': [124, 80], 'palpebra-l': [76, 68], 'palpebra-r': [124, 68],
    'sobrancelha-l': [76, 58], 'sobrancelha-r': [124, 58], 'boca': [86, 119]
  },
  ancoras: { 'olhar': [100, 80], 'mao-l': [41, 250], 'mao-r': [159, 250],
             'fala': [158, 44], 'topo': [100, 38] },

  poses: {
    'neutro':     {},
    'apontando':  { 'braco-r': { rot: -44 }, 'cabeca': { rot: -4 } },
    /* A pose que define o Elefante: o livro aberto, oferecido como prova. */
    'entregando': { 'braco-r': { rot: -62, y: -10 }, 'braco-l': { rot: 14 }, 'cabeca': { rot: 4 } },
    'protegendo': { 'braco-l': { rot: -26 }, 'braco-r': { rot: 26, y: -18 }, 'corpo': { sy: .98 } },
    'andando':    { 'perna-l': { rot: 14 }, 'perna-r': { rot: -14 }, 'corpo': { y: -3 },
                    'orelha-l': { rot: -6 }, 'orelha-r': { rot: 6 } }
  },
  expressoes: {
    'neutro':     {},
    'preocupado': { 'sobrancelha-l': { rot: 16 }, 'sobrancelha-r': { rot: -16 },
                    'palpebra-l': { y: 9 }, 'palpebra-r': { y: 9 },
                    'orelha-l': { rot: 10 }, 'orelha-r': { rot: -10 }, 'boca': { sy: -.9, y: 3 } },
    'feliz':      { 'boca': { sx: 1.3, sy: 1.3 }, 'palpebra-l': { y: 6 }, 'palpebra-r': { y: 6 },
                    'orelha-l': { rot: -8 }, 'orelha-r': { rot: 8 } },
    'surpreso':   { 'olho-l': { s: 1.2 }, 'olho-r': { s: 1.2 }, 'palpebra-l': { y: -6 },
                    'palpebra-r': { y: -6 }, 'orelha-l': { rot: -14 }, 'orelha-r': { rot: 14 } }
  },
  estados: { 'normal': {}, 'apagado': { op: .32 } },

  hitbox: [12, 38, 176, 282]
});
