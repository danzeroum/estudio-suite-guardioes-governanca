/* O som — camada aditiva e derivada, escrava do tempo (CP-004/CP-006).
   Nunca escreve o tempo: existe UM t, o do filme, lido e obedecido.
   Nasce DESLIGADO; sem trilha, o botão some (fallback natural).
   Em quadrinhos (CP-006) o MESMO botão vira "Ouvir este plano": o media
   fragment não segura o fim no Chromium file:// (medido), então cada
   plano com fala tem clipe próprio derivado da mesma trilha pelo dublar.
   Um módulo, um botão: nenhum segundo motor. */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio = raiz.Estudio || {};
  var DRIFT_MAX = 0.080;             /* o drift que se OUVE como eco */

  E.Som = {
    criar: function (opc) {
      var bt = opc.bt, filme = opc.filme;
      var anunciar = opc.anunciar || function () {};
      var base = opc.base || '../';
      var id = filme.id;             /* contrato CP-004: filme real ou mínimo de teste */
      var el = document.createElement('audio');
      var ligado = false, pronto = false, quad = false;
      var planoEl = null, planoTocando = false, planoPronto = false;

      /* No head carrega cedo, sem UI — o truque do carregador. */
      el.preload = 'auto';
      el.src = base + 'filmes/' + id + '/audio/' + id + '.opus';
      document.head.appendChild(el);
      el.addEventListener('canplay', function () { pronto = true; if (!quad) bt.hidden = false; });
      el.addEventListener('error', function () { bt.hidden = true; });

      function sincronizar(t) {
        if (Math.abs(el.currentTime - t) > DRIFT_MAX) el.currentTime = t;
      }

      function planoComFala(t) {
        var P = filme.planos[filme.planoIndice(t)];
        return P && filme.legendas.some(function (x) { return x.plano === P.id; }) ? P : null;
      }

      function cromoPlano(t) {
        var P = planoComFala(t);
        if (!P || !(pronto || planoPronto)) { bt.hidden = true; return; }
        bt.hidden = false;
        bt.removeAttribute('aria-pressed');    /* ação, não toggle */
        bt.setAttribute('aria-label', planoTocando
          ? 'Parar de ouvir o plano' : 'Ouvir o plano: ' + P.titulo);
        bt.textContent = planoTocando ? '■ Parar o plano' : '▶ Ouvir este plano';
      }

      function cromoSom() {
        bt.hidden = !pronto;
        bt.removeAttribute('aria-label');
        bt.setAttribute('aria-pressed', String(ligado));
        bt.textContent = '🔊 Som';
      }

      function ouvirPlano() {
        if (planoTocando) { planoEl.pause(); return; }
        var P = planoComFala(filme.t);
        if (!P) return;
        if (!planoEl) {
          planoEl = document.createElement('audio');
          document.head.appendChild(planoEl);
          planoEl.addEventListener('canplay', function () { planoPronto = true; cromoPlano(filme.t); });
          planoEl.addEventListener('error', function () { planoPronto = false; cromoPlano(filme.t); });
          planoEl.addEventListener('ended', function () { planoTocando = false; cromoPlano(filme.t); });
          planoEl.addEventListener('pause', function () { planoTocando = false; cromoPlano(filme.t); });
        }
        planoEl.src = base + 'filmes/' + id + '/audio/' + id + '-' + P.id + '.opus';
        planoEl.play().catch(function () {});
        planoTocando = true;
        anunciar('Ouvindo o plano: ' + P.titulo);
        cromoPlano(filme.t);
      }

      return {
        ligado: function () { return ligado; },
        pronto: function () { return pronto; },
        alternar: function (silencioso) {
          /* silencioso = filme parado: armar sem tocar. Em quadrinhos o
             clique é OUVIR O PLANO — e clique sempre soa (CP-006). */
          if (quad) { ouvirPlano(); return; }
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
          if (quadrinhos !== quad) {
            quad = quadrinhos;
            if (!quad) {
              if (planoEl && !planoEl.paused) planoEl.pause();
              planoTocando = false;
              cromoSom();
            }
          }
          if (quad) {
            if (!el.paused) el.pause();   /* a trilha inteira não vaza */
            cromoPlano(t);
            return;
          }
          if (!ligado) { if (!el.paused) el.pause(); return; }
          if (!pronto) return;
          if (!tocando) { if (!el.paused) el.pause(); sincronizar(t); return; }
          sincronizar(t);
          if (el.paused) el.play().catch(function () {});
        },
        _el: el,
        _planoEl: function () { return planoEl; }
      };
    }
  };
})(window);
