/* Carregador — traz um filme ou jogo pelo id, sob file:// inclusive.
   =====================================================================
   Ate a Fase 5 os dois filmes entravam como <script src> estaticos, e a
   regra do projeto dizia, com razao, que carregador dinamico antes da
   terceira repeticao era abstracao prematura. Uma SUITE e a terceira
   repeticao: o numero de filmes e aberto, e uma tag por filme seria uma
   lista escrita a mao que envelhece a cada filme novo.

   <script src> criado por DOM carrega sob file://; fetch nao. A diferenca
   nao e detalhe: e a razao de este arquivo existir em vez de um fetch de
   tres linhas. Esta provado por teste, nos dois protocolos.

   Ordem e sequencial de proposito. Paralelo seria mais rapido e traria de
   volta a pergunta "quem registrou primeiro?", que e a classe de bug que
   um estudio deterministico nao pode ter.
   ===================================================================== */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio = raiz.Estudio || {};

  function um(url) {
    return new Promise(function (ok, nao) {
      var s = document.createElement('script');
      s.src = url;
      s.onload = function () { ok(url); };
      s.onerror = function () {
        nao(new Error('Estúdio: não consegui carregar "' + url + '".'));
      };
      document.head.appendChild(s);
    });
  }

  E.carregarScripts = function (urls) {
    return urls.reduce(function (antes, url) {
      return antes.then(function () { return um(url); });
    }, Promise.resolve());
  };

  /* Um filme e o arquivo de dados MAIS os adereços que so ele usa. O que e
     local vem declarado no proprio filme (campo "local"), e nao de uma
     listagem de diretorio -- sob file:// nao ha como listar diretorio, e
     um indice separado seria uma segunda descricao do filme. */
  E.carregarFilme = function (id, raizRel) {
    var base = (raizRel || '../') + 'filmes/' + id + '/';
    return E.carregarScripts([base + id + '.filme.js']).then(function () {
      var d = (raiz.ESTUDIO_FILMES || {})[id];
      if (!d) throw new Error('Estúdio: "' + id + '" carregou sem registrar o filme.');
      return E.carregarScripts((d.local || []).map(function (f) { return base + 'local/' + f; }));
    });
  };

  E.carregarJogo = function (id, raizRel) {
    var base = (raizRel || '../') + 'jogos/' + id + '/';
    return E.carregarScripts([base + id + '.jogo.js']).then(function () {
      var d = (raiz.ESTUDIO_JOGOS || {})[id];
      if (!d) throw new Error('Estúdio: "' + id + '" carregou sem registrar o jogo.');
      return E.carregarScripts((d.local || []).map(function (f) { return base + 'local/' + f; }));
    });
  };
})(window);
