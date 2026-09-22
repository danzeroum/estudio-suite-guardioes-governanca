/* Estúdio dos Guardiões — interpolação.
   Script clássico, sem módulo: módulo ES é requisição CORS e morre sob file://.
   Tabela de easing FECHADA: um roteiro só pode usar estes seis nomes. */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio = raiz.Estudio || {};

  var EASE = {
    linear:   function (t) { return t; },
    suave:    function (t) { return t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; },
    entrada:  function (t) { return t * t; },
    saida:    function (t) { return 1 - (1 - t) * (1 - t); },
    elastico: function (t) {
      if (t === 0 || t === 1) return t;
      return Math.pow(2, -9 * t) * Math.sin((t * 10 - .75) * (2 * Math.PI / 3)) + 1;
    },
    degrau:   function (t) { return t < 1 ? 0 : 1; }
  };

  E.EASES = Object.keys(EASE);
  /* A tabela e FECHADA, e agora o codigo cumpre o que o comentario dizia:
     cair em 'linear' calado transformava um nome errado num filme que toca
     com o ritmo errado -- plausivel, e por isso pior que um erro. */
  E.ease = function (nome) {
    var f = EASE[nome];
    if (!f) throw new Error('Estúdio: easing "' + nome + '" não existe (use ' + E.EASES.join(', ') + ').');
    return f;
  };
  E.lerp = function (a, b, t) { return a + (b - a) * t; };
  E.trava = function (v, min, max) { return v < min ? min : v > max ? max : v; };
  /* Arredonda para 3 casas: o transform escrito no DOM precisa ser
     byte-a-byte estável, senão a asserção de idempotência (R1) acusa
     diferença só por ruído de ponto flutuante. */
  E.n = function (v) { return Math.round(v * 1000) / 1000; };
})(window);
