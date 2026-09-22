/* Estúdio dos Guardiões — props.
   Um prop É um rig: monta, tem partes com origem, recebe aplicar(snapshot) e
   devolve instantaneo(). Não ganha um contrato próprio porque não precisa de
   nada que o contrato dos personagens já não dê — inventar um segundo seria
   abstrair antes da necessidade. Este arquivo existe para separar o elenco
   dos objetos, não para separar dois mecanismos.

   Convenção: como todo rig, o prop é posicionado pela base (y local 320), e
   o desenho fica entre y=140 e y=318.

   Cuidado que custou um render: a opacidade de um <g> MULTIPLICA com a do
   elemento dentro dele. Um opacity="0" no desenho nunca mais volta, por mais
   que a pose peça op:1. Por isso a opacidade de repouso mora sempre na pose
   'neutro', nunca no markup — e tools/test-estudio.py recusa opacity="0"
   dentro de uma parte animada. */
(function (raiz) {
  'use strict';
  var PALETA = { base: '#8a7f6a', claro: '#faf7ef', escuro: '#5d5546',
                 detalhe: '#8a5a9e', olho: '#ffffff', pupila: '#2e2a22' };
  var PALETA_ESC = { base: '#9a9080', claro: '#2b2e28', escuro: '#6d6659',
                     detalhe: '#c79bdb', olho: '#ffffff', pupila: '#d8d4c8' };

  function prop(def) {
    def.viewBox = [0, 0, 200, 320];
    def.escalaNatural = def.escalaNatural || 1;
    def.paleta = def.paleta || PALETA;
    def.paletaEscura = def.paletaEscura || PALETA_ESC;
    def.expressoes = { neutro: {} };
    def.estados = { normal: {}, apagado: { op: .3 } };
    def.ancoras = def.ancoras || { olhar: [100, 240], centro: [100, 240] };
    Estudio.Rig.registrar(def);
  }

  /* p02 — o formulário de onde o Dado nasce. */
  prop({
    id: 'form', nome: 'o formulário', epiteto: 'a coleta', ator: 'objeto',
    markup:
      '<g data-part="corpo"><rect x="44" y="164" width="112" height="154" rx="8" fill="var(--p-claro)"/>' +
        '<rect x="44" y="164" width="112" height="154" rx="8" fill="none" stroke="var(--p-base)" stroke-width="5"/>' +
        '<path d="M64 196h72M64 220h72M64 244h48" stroke="var(--p-base)" stroke-width="7" stroke-linecap="round"/></g>' +
      '<g data-part="marca"><path d="M62 276l16 16 34-38" stroke="var(--p-detalhe)" stroke-width="9"' +
        ' fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>',
    origens: { 'corpo': [100, 240], 'marca': [86, 276] },
    poses: { 'neutro': { 'marca': { op: 0 } }, 'preenchido': { 'marca': { op: 1 } } },
    hitbox: [44, 164, 112, 154]
  });

  /* p03 — o aviso: o que precisa ser contado ao titular, antes. */
  prop({
    id: 'aviso', nome: 'o aviso', epiteto: 'a transparência', ator: 'objeto',
    markup:
      '<g data-part="corpo"><rect x="16" y="150" width="168" height="168" rx="10" fill="var(--p-claro)"/>' +
        '<rect x="16" y="150" width="168" height="168" rx="10" fill="none" stroke="var(--p-base)" stroke-width="5"/>' +
        '<rect x="38" y="174" width="80" height="12" rx="6" fill="var(--p-detalhe)"/></g>' +
      '<g data-part="itens"><path d="M38 212h124M38 240h124M38 268h84" stroke="var(--p-base)"' +
        ' stroke-width="8" stroke-linecap="round"/></g>',
    origens: { 'corpo': [100, 234], 'itens': [100, 240] },
    poses: { 'neutro': { 'itens': { op: .25 } }, 'aberto': { 'itens': { op: 1 } } },
    hitbox: [16, 150, 168, 168]
  });

  /* p04 — o consentimento: destacado do resto, e revogável. */
  prop({
    id: 'cartao', nome: 'o consentimento', epiteto: 'destacado e revogável', ator: 'objeto',
    markup:
      '<g data-part="corpo"><rect x="24" y="196" width="152" height="112" rx="12" fill="var(--p-claro)"/>' +
        '<rect x="24" y="196" width="152" height="112" rx="12" fill="none" stroke="var(--p-detalhe)" stroke-width="6"/>' +
        '<path d="M52 236h96M52 262h64" stroke="var(--p-base)" stroke-width="8" stroke-linecap="round"/></g>' +
      '<g data-part="marca"><path d="M120 258l14 14 30-34" stroke="var(--p-detalhe)" stroke-width="10"' +
        ' fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>' +
      '<g data-part="volta"><path d="M150 210a34 34 0 1 0 12 26" stroke="var(--p-detalhe)"' +
        ' stroke-width="8" fill="none" stroke-linecap="round"/>' +
        '<path d="M142 196l10 18-20 2z" fill="var(--p-detalhe)"/></g>',
    origens: { 'corpo': [100, 252], 'marca': [134, 258], 'volta': [140, 226] },
    poses: {
      'neutro': { 'marca': { op: 0 }, 'volta': { op: 0 } },
      'aceito': { 'marca': { op: 1 }, 'volta': { op: 0 } },
      'revogado': { 'marca': { op: 0 }, 'volta': { op: 1 }, 'corpo': { op: .55 } }
    },
    hitbox: [24, 196, 152, 112]
  });

  /* p05 e p09 — o carimbo: a rota escolhida, a fronteira conferida. */
  prop({
    id: 'selo', nome: 'o carimbo', epiteto: 'a conferência', ator: 'objeto',
    markup:
      '<g data-part="corpo"><circle cx="100" cy="258" r="56" fill="none" stroke="var(--p-detalhe)"' +
        ' stroke-width="10"/>' +
        '<circle cx="100" cy="258" r="40" fill="var(--p-detalhe)" opacity=".18"/>' +
        '<path d="M74 258l18 20 36-42" stroke="var(--p-detalhe)" stroke-width="12" fill="none"' +
        ' stroke-linecap="round" stroke-linejoin="round"/></g>',
    origens: { 'corpo': [100, 258] },
    poses: { 'neutro': { 'corpo': { s: 1.6, op: 0 } }, 'carimbado': { 'corpo': { s: 1 } } },
    hitbox: [38, 196, 124, 124]
  });

  /* p08 — a ficha: sem registro, não há como provar nada. */
  prop({
    id: 'ficha', nome: 'a ficha', epiteto: 'o registro', ator: 'objeto',
    markup:
      '<g data-part="corpo"><rect x="30" y="186" width="140" height="122" rx="8" fill="var(--p-claro)"/>' +
        '<rect x="30" y="186" width="140" height="122" rx="8" fill="none" stroke="var(--p-base)" stroke-width="5"/>' +
        '<rect x="30" y="186" width="140" height="26" rx="8" fill="var(--p-base)"/>' +
        '<path d="M52 240h96M52 264h96M52 288h60" stroke="var(--p-base)" stroke-width="7" stroke-linecap="round"/></g>',
    origens: { 'corpo': [100, 248] },
    poses: { 'neutro': {}, 'arquivada': { 'corpo': { rot: -6, y: -12 } } },
    hitbox: [30, 186, 140, 122]
  });

  /* p10 — a porta do cofre. A folha que gira; a moldura e o vão ficam no
     cenário. Três poses dão os DOIS tempos da legenda do plano: o susto
     ("uma porta fica destrancada") e o recuo ("ela nasce com o produto").
     Desenhada em torno de (100,240) com r=68: no plano, escala 2.2 e y=556
     põem o centro exatamente em (980,380), casando com a moldura. */
  prop({
    id: 'porta', nome: 'a porta do cofre', epiteto: 'a segurança', ator: 'objeto',
    markup:
      '<g data-part="folha">' +
        '<circle cx="100" cy="240" r="68" fill="var(--p-base)"/>' +
        '<circle cx="100" cy="240" r="68" fill="none" stroke="var(--p-escuro)" stroke-width="5"/>' +
        '<circle cx="100" cy="240" r="18" fill="var(--p-escuro)"/>' +
        '<path d="M100 204v-30M100 276v30M64 240H34M136 240h30" stroke="var(--p-escuro)"' +
        ' stroke-width="9" stroke-linecap="round"/>' +
      '</g>' +
      '<g data-part="planta">' +
        '<circle cx="100" cy="240" r="68" fill="none" stroke="var(--p-detalhe)" stroke-width="4"' +
        ' stroke-dasharray="10 8"/>' +
        '<circle cx="100" cy="240" r="18" fill="none" stroke="var(--p-detalhe)" stroke-width="3"/>' +
        '<path d="M100 150v180M10 240h180" stroke="var(--p-detalhe)" stroke-width="2"' +
        ' stroke-dasharray="5 6"/>' +
      '</g>',
    origens: { 'folha': [34, 240], 'planta': [100, 240] },
    poses: {
      /* A dobradiça é a borda esquerda da folha, não o centro: porta gira no
         batente. Daí a origem em x=34. */
      'neutro':      { 'planta': { op: 0 } },
      'fechada':     { 'planta': { op: 0 } },
      'entreaberta': { 'folha': { rot: -24 }, 'planta': { op: 0 } },
      'projeto':     { 'folha': { op: .12 }, 'planta': { op: 1 } }
    },
    hitbox: [32, 172, 136, 136]
  });

  /* p10 e p11 — o alarme: incidente relevante não se esconde. */
  prop({
    id: 'alarme', nome: 'o alarme', epiteto: 'a comunicação', ator: 'objeto',
    markup:
      '<g data-part="raios"><path d="M100 150v-34M52 176l-26-22M148 176l26-22" stroke="var(--p-detalhe)"' +
        ' stroke-width="11" stroke-linecap="round"/></g>' +
      '<g data-part="corpo"><path d="M100 178a54 54 0 0 1 54 54v28H46v-28a54 54 0 0 1 54-54z"' +
        ' fill="var(--p-base)"/>' +
        '<rect x="34" y="258" width="132" height="24" rx="8" fill="var(--p-escuro)"/></g>' +
      '<g data-part="luz"><circle cx="100" cy="226" r="30" fill="var(--p-detalhe)"/></g>',
    origens: { 'raios': [100, 176], 'corpo': [100, 232], 'luz': [100, 226] },
    poses: {
      'neutro': { 'raios': { op: 0 }, 'luz': { op: .22 } },
      'tocando': { 'raios': { op: 1 }, 'luz': { s: 1.3, op: .9 }, 'corpo': { y: -4 } }
    },
    hitbox: [34, 116, 132, 166]
  });
})(window);
