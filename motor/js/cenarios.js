/* Estúdio dos Guardiões — cenários.
   Um cenário é o fundo de um plano, em coordenadas do palco (1280x720), com
   o chão em y=620. Toda cor vem de var(--cen-*), definidos em estudio.css
   nos dois temas: o cenário não sabe se é dia ou noite.

   Ao contrário dos personagens, um cenário não tem partes nem poses — ele
   não se move. Por isso não é um rig: seria dar um contrato grande a quem
   precisa de um pequeno. */
(function (raiz) {
  'use strict';
  var C = raiz.ESTUDIO_CENARIOS = raiz.ESTUDIO_CENARIOS || {};

  /* Base comum: parede e chão. Repetir isso em oito strings seria pedir para
     uma delas ficar diferente das outras por engano. */
  function base(extra) {
    return '<rect x="0" y="0" width="1280" height="620" fill="var(--cen-parede)"/>' +
           '<rect x="0" y="620" width="1280" height="100" fill="var(--cen-chao)"/>' +
           '<rect x="0" y="618" width="1280" height="3" fill="var(--cen-linha)" opacity=".5"/>' +
           (extra || '');
  }
  function repete(n, fn) {
    var s = '';
    for (var i = 0; i < n; i++) s += fn(i);
    return s;
  }
  function reg(id, nome, markup) { C[id] = { id: id, nome: nome, markup: markup }; }

  reg('vazio', 'Fundo neutro', base(
    '<circle cx="640" cy="330" r="210" fill="var(--cen-movel)" opacity=".16"/>'));

  reg('balcao', 'O balcão de atendimento', base(
    /* janela ao fundo, à esquerda */
    '<rect x="96" y="120" width="300" height="200" rx="10" fill="var(--cen-vidro)"/>' +
    '<rect x="96" y="120" width="300" height="200" rx="10" fill="none" stroke="var(--cen-linha)" stroke-width="5"/>' +
    '<path d="M246 120v200M96 220h300" stroke="var(--cen-linha)" stroke-width="5"/>' +
    /* balcão à direita */
    '<rect x="700" y="470" width="470" height="30" rx="8" fill="var(--cen-movel)"/>' +
    '<rect x="736" y="500" width="400" height="120" fill="var(--cen-movel)" opacity=".62"/>' +
    /* plantinha */
    '<rect x="1178" y="556" width="56" height="64" rx="6" fill="var(--cen-movel)"/>' +
    '<circle cx="1206" cy="530" r="34" fill="var(--cen-linha)" opacity=".55"/>'));

  reg('painel', 'O painel das dez rotas', base(
    '<rect x="150" y="110" width="700" height="420" rx="14" fill="var(--cen-movel)" opacity=".5"/>' +
    '<rect x="150" y="110" width="700" height="420" rx="14" fill="none" stroke="var(--cen-linha)" stroke-width="5"/>' +
    /* as dez rotas: dez trilhos partindo da mesma origem */
    repete(10, function (i) {
      var y = 160 + i * 38;
      return '<rect x="196" y="' + y + '" width="' + (300 + (i % 3) * 90) + '" height="12" rx="6"' +
             ' fill="var(--cen-linha)" opacity="' + (i === 4 ? '.95' : '.38') + '"/>';
    })));

  reg('principios', 'Os dez princípios', base(
    /* dez lâminas em leque: o casco da Tartaruga aberto */
    repete(10, function (i) {
      var a = (-52 + i * 11.5), x = 640 + i * 0;
      return '<g transform="rotate(' + a + ' ' + x + ' 620)">' +
             '<rect x="' + (x - 13) + '" y="250" width="26" height="380" rx="13"' +
             ' fill="var(--cen-linha)" opacity=".34"/></g>';
    }) +
    '<circle cx="640" cy="620" r="46" fill="var(--cen-movel)"/>'));

  reg('estacoes', 'Controlador e Operador', base(
    '<rect x="150" y="480" width="330" height="26" rx="8" fill="var(--cen-movel)"/>' +
    '<rect x="180" y="506" width="270" height="114" fill="var(--cen-movel)" opacity=".6"/>' +
    '<rect x="800" y="480" width="330" height="26" rx="8" fill="var(--cen-movel)"/>' +
    '<rect x="830" y="506" width="270" height="114" fill="var(--cen-movel)" opacity=".6"/>' +
    /* a linha que liga os dois: a instrução */
    '<path d="M490 440h300" stroke="var(--cen-linha)" stroke-width="7" stroke-linecap="round"' +
    ' stroke-dasharray="20 16"/>' +
    '<path d="M772 424l24 16-24 16z" fill="var(--cen-linha)"/>'));

  reg('arquivo', 'O arquivo', base(
    repete(4, function (l) {
      return '<rect x="130" y="' + (150 + l * 118) + '" width="1020" height="14" rx="4"' +
             ' fill="var(--cen-movel)"/>' +
             repete(11, function (i) {
               var x = 150 + i * 92, h = 74 + ((i + l) % 3) * 12;
               return '<rect x="' + x + '" y="' + (164 + l * 118 - h + 74) + '" width="62" height="' + h +
                      '" rx="4" fill="var(--cen-linha)" opacity="' + (0.28 + ((i + l) % 3) * 0.12) + '"/>';
             });
    })));

  reg('fronteira', 'A fronteira', base(
    '<rect x="0" y="0" width="640" height="620" fill="var(--cen-vidro)" opacity=".55"/>' +
    '<rect x="636" y="0" width="8" height="620" fill="var(--cen-linha)"/>' +
    repete(9, function (i) {
      return '<rect x="628" y="' + (30 + i * 68) + '" width="24" height="36" rx="4"' +
             ' fill="var(--cen-destaque)" opacity=".45"/>';
    }) +
    '<rect x="380" y="430" width="200" height="190" rx="8" fill="var(--cen-movel)" opacity=".5"/>' +
    '<rect x="700" y="430" width="200" height="190" rx="8" fill="var(--cen-movel)" opacity=".5"/>'));

  reg('cofre', 'O cofre', base(
    /* racks ao fundo */
    repete(5, function (i) {
      return '<rect x="' + (80 + i * 120) + '" y="180" width="92" height="440" rx="8"' +
             ' fill="var(--cen-movel)" opacity=".55"/>' +
             repete(6, function (j) {
               return '<rect x="' + (92 + i * 120) + '" y="' + (200 + j * 68) + '" width="68" height="46"' +
                      ' rx="4" fill="var(--cen-linha)" opacity=".4"/>';
             });
    }) +
    /* A porta do cofre: aqui ficam so a moldura, o VAO escuro e o aro. A
       folha que gira e o prop 'porta' -- cenario nao se move, e o plano 10
       precisa que ela abra. */
    '<rect x="760" y="150" width="440" height="470" rx="12" fill="var(--cen-movel)"/>' +
    '<circle cx="980" cy="380" r="150" fill="var(--cen-vao)"/>' +
    '<circle cx="980" cy="380" r="150" fill="none" stroke="var(--cen-linha)" stroke-width="10"/>'));

  raiz.ESTUDIO_CENARIOS = C;
})(window);
