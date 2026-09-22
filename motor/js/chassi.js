/* Chassi — o que o player monta UMA vez, no boot.
   A separação aqui é por temperatura, não por funcionalidade: player.js fica
   com o laço e o transporte (o que roda a cada quadro), e este arquivo com a
   construção de DOM que acontece uma vez e nunca mais. Separar por
   funcionalidade poria código de caminho quente em dois arquivos. */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio = raiz.Estudio || {};

  E.mmss = function (s) {
    var m = Math.floor(s / 60), r = Math.floor(s % 60);
    return m + ':' + (r < 10 ? '0' : '') + r;
  };

  E.Chassi = {
    /* Um erro de roteiro tem de aparecer na TELA: os analistas editam o
       arquivo sob file:// e não vão abrir o console. */
    fatal: function (filme, msg) {
      var d = document.createElement('div');
      d.className = 'est-erro-fatal';
      d.setAttribute('role', 'alert');
      d.setAttribute('tabindex', '-1');
      d.textContent = 'Estúdio — o roteiro não pôde ser lido:\n\n' + msg +
        '\n\nCorrija estudio/assets/js/filmes/' + filme + '.filme.js e recarregue.';
      (document.querySelector('.est-wrap') || document.body).prepend(d);
      d.focus();
    },

    regua: function (el, filme, aoClicar) {
      if (!el) return;
      filme.planos.forEach(function (P, k) {
        var b = document.createElement('button');
        b.className = 'est-marco';
        b.type = 'button';
        b.textContent = String(k + 1);
        b.title = P.titulo;
        b.setAttribute('aria-label', 'Plano ' + (k + 1) + ': ' + P.titulo);
        if (P.guardiao) b.style.setProperty('--m', 'var(--rig-' + P.guardiao + ')');
        b.addEventListener('click', function () { aoClicar(k); });
        el.appendChild(b);
      });
    },

    /* A transcrição é o artefato acessível principal, não um consolo: acesso
       aleatório a 100% da informação, no ritmo de quem lê. */
    transcricao: function (el, filme, aoClicar) {
      if (!el) return;
      var ol = document.createElement('ol');
      filme.legendas.forEach(function (L) {
        var li = document.createElement('li');
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'est-fala';
        var tc = document.createElement('time');
        tc.textContent = E.mmss(L.t);
        b.appendChild(tc);
        b.appendChild(document.createTextNode(' ' + L.txt.replace(/\n/g, ' ')));
        b.addEventListener('click', function () { aoClicar(L.t); });
        li.appendChild(b);
        ol.appendChild(li);
      });
      el.appendChild(ol);
    }
  };
})(window);
