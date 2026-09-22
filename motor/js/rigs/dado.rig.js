/* ● O Dado — o protagonista mudo. Não é um guardião: é o que eles guardam.
   Nasce no plano 2, atravessa o filme e se apaga no plano 12, sempre por
   vontade de quem sempre foi seu dono.

   Ele usa o MESMO contrato dos guardiões (mesma viewBox, mesma âncora no
   pé, mesmo aplicar/instantaneo) de propósito: uma só convenção deixa o
   roteiro trocar quem está em cena sem mexer no plano. Enquanto um prop
   couber aqui, não existe props.js — abstração só nasce na segunda
   repetição. */
Estudio.Rig.registrar({
  id: 'dado', nome: 'o Dado', epiteto: 'o que eles guardam', ator: 'Dado pessoal',
  viewBox: [0, 0, 200, 320], escalaNatural: 1,

  paleta:       { base: '#8a5a9e', claro: '#f0e3f6', escuro: '#5d3a6c',
                  detalhe: '#efe3f4', olho: '#ffffff', pupila: '#2a1c31' },
  paletaEscura: { base: '#c79bdb', claro: '#f2e6f7', escuro: '#8a5a9e',
                  detalhe: '#f6eff9', olho: '#ffffff', pupila: '#1d1423' },

  markup:
    '<g data-part="halo"><circle cx="100" cy="286" r="46" fill="var(--p-base)" opacity=".16"/></g>' +
    '<g data-part="corpo">' +
      '<path d="M100 254l28 16v32l-28 16-28-16v-32z" fill="var(--p-base)"/>' +
      '<path d="M100 254l28 16-28 16-28-16z" fill="var(--p-escuro)" opacity=".35"/>' +
    '</g>' +
    '<g data-part="nucleo"><circle cx="100" cy="286" r="11" fill="var(--p-claro)"/></g>',

  origens: { 'halo': [100, 286], 'corpo': [100, 286], 'nucleo': [100, 286] },
  ancoras: { 'olhar': [100, 286], 'topo': [100, 254], 'centro': [100, 286] },

  poses: {
    'neutro':  {},
    /* 'aceso' é o instante em que o dado passa a existir para a lei. */
    'aceso':   { 'halo': { s: 1.35, op: 1.8 }, 'nucleo': { s: 1.45 } },
    /* 'retraido' é o susto do plano 10: composição de escala, não pose nova. */
    'retraido': { 'corpo': { s: .82 }, 'halo': { s: .6, op: .4 }, 'nucleo': { s: .5 } }
  },
  expressoes: { 'neutro': {} },
  estados: { 'normal': {}, 'apagado': { op: .25 } },

  hitbox: [64, 250, 72, 72]
});
