/* Relógio — o laço de quadro, compartilhado.
   =====================================================================
   O player já tinha este laço; o jogo precisa do mesmo. Escrever um
   segundo à mão, com a mesma lógica sutil de pausa e delta preso, é a
   fábrica de bug que as regras do projeto existem para evitar — e esta é,
   por definição, a segunda repetição, que é quando a abstração nasce.

   O relógio não sabe o que fazer com o tempo: ele entrega `dt` e quem o
   usa decide. O player faz `t += dt` e renderiza um instante; o
   jogo desconta `dt` de um prazo. Um relógio, dois donos.
   ===================================================================== */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio = raiz.Estudio || {};

  /* O mesmo passo que o teste da Fase 2 provou equivalente a um salto. */
  var MAXDT = 0.25;

  E.Relogio = function (aoQuadro) {
    var tocando = false, raf = null, ultimo = null, retomar = false;

    /* A costura de teste: o mesmo avanço do laço, sem rAF e sem relógio de
       parede. Todo caso de tempo do teste passa por aqui. */
    function avancar(dt) { aoQuadro(dt); }

    /* Sem 'if (!tocando) return' no topo: é o que deixa um relógio parado
       ser bombeado quadro a quadro por um teste sem nunca reagendar. */
    function quadro(ts) {
      if (ultimo === null) ultimo = ts;   /* 1º quadro após tocar(): delta zero */
      var dt = (ts - ultimo) / 1000;
      ultimo = ts;
      avancar(dt > MAXDT ? MAXDT : (dt > 0 ? dt : 0));
      if (tocando) raf = raiz.requestAnimationFrame(quadro);
    }

    function tocar() {
      if (tocando) return;
      tocando = true;
      ultimo = null;        /* nenhum valor de relógio sobrevive à pausa */
      raf = raiz.requestAnimationFrame(quadro);
    }
    function parar() {
      if (raf) raiz.cancelAnimationFrame(raf);
      raf = null; ultimo = null; tocando = false;
    }

    /* Aba escondida não avança: o delta preso só limitaria o salto, e num
       material silencioso passar despercebido é pior do que pausar. */
    document.addEventListener('visibilitychange', function () {
      if (document.hidden && tocando) { retomar = true; parar(); }
      else if (!document.hidden && retomar) { retomar = false; tocar(); }
    });

    return {
      tocar: tocar, parar: parar, avancar: avancar,
      tocando: function () { return tocando; },
      _quadro: quadro, _raf: function () { return raf; }, MAXDT: MAXDT
    };
  };
})(window);
