/* O som — camada aditiva e derivada, escrava do tempo (CP-004).
   Este arquivo é o INVERSO do resto do motor: nunca escreve o tempo. Existe
   UM t, e ele é do filme (filme.t, por renderizar). O som lê e obedece —
   ao tocar, ao buscar, e a cada quadro. Nasce DESLIGADO: o filme mudo é o
   produto completo; sem trilha, o botão não aparece (fallback natural).
   O modo quadrinhos permanece silencioso nesta CP. A doutrina toda está na
   CP-004; aqui só o que o código precisa dizer de si. */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio = raiz.Estudio || {};

  /* O drift que se OUVE como eco: acima disso, ressincroniza. */
  var DRIFT_MAX = 0.080;

  E.Som = {
    criar: function (opc) {
      /* opc: { bt, filme, base, anunciar }. */
      var bt = opc.bt, filme = opc.filme;
      var anunciar = opc.anunciar || function () {};
      var el = document.createElement('audio');
      var ligado = false, pronto = false;

      el.preload = 'auto';
      el.src = (opc.base || '../') + 'filmes/' + filme.id + '/audio/' + filme.id + '.opus';
      /* Fora do documento, midia nao carrega: so no insert/play/load.
         No head carrega cedo, sem UI — o truque do carregador. */
      document.head.appendChild(el);
      el.addEventListener('canplay', function () { pronto = true; bt.hidden = false; });
      el.addEventListener('error', function () { bt.hidden = true; });

      function sincronizar(t) {
        if (Math.abs(el.currentTime - t) > DRIFT_MAX) el.currentTime = t;
      }

      return {
        ligado: function () { return ligado; },
        pronto: function () { return pronto; },
        alternar: function (silencioso) {
          /* silencioso = quadrinhos ou filme parado: armar sem tocar. */
          ligado = !ligado;
          bt.setAttribute('aria-pressed', String(ligado));
          if (ligado && !silencioso) { sincronizar(filme.t); el.play().catch(function () {}); }
          else el.pause();
          anunciar(ligado ? 'Som ligado' : 'Som desligado');
        },
        tocar: function () {
          if (!ligado || !pronto) return;
          sincronizar(filme.t);
          el.play().catch(function () {});
        },
        pausar: function () { el.pause(); },
        /* A cromagem chama por quadro: o único lugar onde o tempo do
           audio é corrigido. Busca em pausa também passa por aqui. */
        porQuadro: function (t, tocando, quadrinhos) {
          if (quadrinhos || !ligado) { if (!el.paused) el.pause(); return; }
          if (!pronto) return;
          if (!tocando) { if (!el.paused) el.pause(); sincronizar(t); return; }
          sincronizar(t);
          if (el.paused) el.play().catch(function () {});
        },
        _el: el
      };
    }
  };
})(window);
