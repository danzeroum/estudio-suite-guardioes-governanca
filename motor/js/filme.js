/* Estúdio dos Guardiões — o interpretador do roteiro.
   =====================================================================
   O roteiro é DADO. Este arquivo é o único que sabe lê-lo, e ele não sabe
   nada sobre "a jornada de um dado pessoal": trocar de filme é trocar de
   arquivo de dados, nunca de código.

   No carregamento, todo o roteiro é ACHATADO em trilhas absolutas
   (alvo|propriedade -> keyframes ordenados), com os 'de' já resolvidos.
   Depois disso, renderizar(t) é busca binária + interpolação: O(log n),
   idêntico para frente, para trás ou em salto. É daí que vem a busca
   determinística — e não de um cache, que precisaria ser invalidado.

   O relógio NÃO mora aqui. Este arquivo responde "como está o filme no
   instante t"; player.js responde "que instante é agora". Existe um t só, e
   ele é do player — nenhum subsistema guarda a própria noção de tempo.
   ===================================================================== */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio = raiz.Estudio || {};
  var n = E.n, lerp = E.lerp, trava = E.trava;

  /* Vocabulário fechado. Ação fora desta lista é erro de roteiro, não uma
     extensão silenciosa: ampliar o vocabulário é decisão explícita. */
  var NUMERICAS = ['x', 'y', 'escala', 'op', 'zoom'];
  var ACOES = ['para', 'pose', 'expressao', 'estado', 'evento'];
  var EVENTOS = ['citar', 'destacar', 'marco'];

  function erro(msg) { throw new Error('Roteiro: ' + msg); }

  /* ---- trilhas numéricas ------------------------------------------ */
  function indice(kfs, t) {          /* último i com kfs[i].t <= t */
    var lo = 0, hi = kfs.length - 1, r = -1;
    while (lo <= hi) {
      var m = (lo + hi) >> 1;
      if (kfs[m].t <= t) { r = m; lo = m + 1; } else { hi = m - 1; }
    }
    return r;
  }
  function valorNum(kfs, t) {
    if (!kfs || !kfs.length) return undefined;
    var i = indice(kfs, t);
    if (i < 0) return kfs[0].v;
    if (i >= kfs.length - 1) return kfs[i].v;
    var a = kfs[i], b = kfs[i + 1];
    /* Inalcançável enquanto a trilha estiver ordenada: indice() devolve
       sempre o ÚLTIMO empate, então b.t > a.t. Fica como rede para quem
       montar uma trilha à mão; a ordenação de que ele depende é afirmada
       por teste, que é onde a garantia de verdade mora. */
    if (b.t <= a.t) return b.v;
    var u = trava((t - a.t) / (b.t - a.t), 0, 1);
    return lerp(a.v, b.v, E.ease(b.ease || 'linear')(u));
  }
  /* pose/expressão: nome + mistura, pelo mesmo princípio de busca. */
  function valorNome(kfs, t, padrao) {
    if (!kfs || !kfs.length) return { nome: padrao, mistura: 1, anterior: padrao };
    var i = indice(kfs, t);
    if (i < 0) { var p = kfs[0].anterior || padrao; return { nome: p, mistura: 1, anterior: p }; }
    var k = kfs[i];
    var m = k.dur > 0 ? E.ease(k.ease || 'suave')(trava((t - k.t) / k.dur, 0, 1)) : 1;
    return { nome: k.nome, mistura: m, anterior: k.anterior };
  }

  /* ---- Filme ------------------------------------------------------ */
  function Filme(dados, opc) {
    opc = opc || {};
    this.dados = dados;
    this.id = dados.id;
    this.titulo = dados.titulo;
    this.palco = opc.palco || null;
    this._tema = opc.tema || 'claro';
    this.trilhas = {};     /* 'alvo|prop' -> keyframes */
    this.poses = {};       /* 'alvo' -> keyframes de pose */
    this.exprs = {};
    this.estados = {};
    this.citacoes = [];
    this.legendas = [];
    this.planos = [];
    this.t = 0;
    this.rigs = {};
    this._achatar();
    if (this.palco) this._montar();
    this._ultimoPlano = null;
  }

  Filme.prototype._tr = function (alvo, prop) {
    var k = alvo + '|' + prop;
    return this.trilhas[k] || (this.trilhas[k] = []);
  };
  Filme.prototype._passo = function (alvo, prop, t, v) {
    this._tr(alvo, prop).push({ t: t, v: v, ease: 'degrau' });
  };

  Filme.prototype._achatar = function () {
    var d = this.dados, self = this;
    var alvos = {};
    Object.keys(d.elenco || {}).forEach(function (k) { alvos[k] = d.elenco[k]; });
    Object.keys(d.props || {}).forEach(function (k) { alvos[k] = d.props[k]; });
    this.alvos = alvos;

    /* Fora de cena é o estado inicial de todo mundo: quem não entrou num
       plano não aparece, sem o roteiro precisar dizer isso. */
    Object.keys(alvos).forEach(function (a) {
      self._passo(a, 'op', 0, 0);
      self._passo(a, 'x', 0, 640);
      self._passo(a, 'y', 0, E.PALCO.chao);
      self._passo(a, 'escala', 0, 1);
    });
    self._passo('camera', 'x', 0, E.PALCO.w / 2);
    self._passo('camera', 'y', 0, E.PALCO.h / 2);
    self._passo('camera', 'zoom', 0, 1);

    var cursor = {}, cPose = {}, cExpr = {};
    function cur(a, p, v) { if (v !== undefined) cursor[a + '|' + p] = v; return cursor[a + '|' + p]; }

    var inicio = 0;
    (d.planos || []).forEach(function (P, idx) {
      if (!P.id || !P.dur) erro('plano ' + idx + ' sem id ou dur');
      if (!(raiz.ESTUDIO_CENARIOS || {})[P.cenario]) erro(P.id + ': cenário "' + P.cenario + '" não existe');
      self.planos.push({ id: P.id, titulo: P.titulo, inicio: inicio, dur: P.dur,
                         fim: inicio + P.dur, guardiao: P.guardiao, cenario: P.cenario,
                         poster: inicio + (P.poster != null ? P.poster : P.dur / 2),
                         arts: P.arts || [] });

      /* 'entra' é o ELENCO DO PLANO, não um acréscimo ao plano anterior:
         quem não está aqui não está em cena. Sem esta linha, o primeiro
         alvo a aparecer ficava visível até o fim do filme, e a folha de
         contato mostrava os treze de uma vez em todos os doze planos. */
      Object.keys(alvos).forEach(function (a) {
        if (!(P.entra || {})[a]) { self._passo(a, 'op', inicio, 0); cur(a, 'op', 0); }
      });

      /* A câmera volta ao neutro em todo corte, pelo mesmo princípio: um
         plano começa do zero, não de onde o anterior parou. Sem isto, um
         zoom vazava para a frente e não voltava mais -- o filme 01 tocava
         ampliado de p03 até o fim, e nenhum teste pegou, porque todos
         comparam o filme com ele mesmo. */
      self._passo('camera', 'x', inicio, E.PALCO.w / 2); cur('camera', 'x', E.PALCO.w / 2);
      self._passo('camera', 'y', inicio, E.PALCO.h / 2); cur('camera', 'y', E.PALCO.h / 2);
      self._passo('camera', 'zoom', inicio, 1);          cur('camera', 'zoom', 1);

      Object.keys(P.entra || {}).forEach(function (a) {
        if (!alvos[a]) erro(P.id + ': "' + a + '" não está no elenco nem nos props');
        var e = P.entra[a];
        Object.keys(e).forEach(function (p) {
          if (NUMERICAS.indexOf(p) >= 0) { self._passo(a, p, inicio, e[p]); cur(a, p, e[p]); }
          else if (p === 'pose') { (self.poses[a] = self.poses[a] || []).push({ t: inicio, nome: e[p], dur: 0, anterior: e[p] }); cPose[a] = e[p]; }
          else if (p === 'expressao') { (self.exprs[a] = self.exprs[a] || []).push({ t: inicio, nome: e[p], dur: 0, anterior: e[p] }); cExpr[a] = e[p]; }
          else if (p === 'espelho') { self._passo(a, 'espelho', inicio, e[p] ? 1 : 0); }
          else erro(P.id + '/entra/' + a + ': propriedade "' + p + '" desconhecida');
        });
        if (e.op === undefined) { self._passo(a, 'op', inicio, 1); cur(a, 'op', 1); }
      });

      (P.acoes || []).slice().sort(function (a, b) { return a.em - b.em; }).forEach(function (A) {
        var a = A.alvo;
        if (a !== 'camera' && !alvos[a]) erro(P.id + ': ação com alvo "' + a + '" fora do elenco');
        if (A.em == null) erro(P.id + '/' + a + ': ação sem "em"');
        var dur = A.dur || 0;
        /* O ease e conferido no CARREGAMENTO, nao no primeiro quadro que o
           usa: assim o analista que edita sob file:// ve a mensagem na tela,
           e nao um filme que quebra aos 90s. */
        if (A.ease && E.EASES.indexOf(A.ease) < 0) erro(P.id + '/' + a + ': ease "' + A.ease + '" fora da tabela (' + E.EASES.join(', ') + ')');
        if (A.em + dur > P.dur + 1e-6) erro(P.id + '/' + a + ': ação em ' + A.em + '+' + dur + ' passa da duração do plano (' + P.dur + ')');
        var t0 = inicio + A.em, t1 = t0 + dur;
        var usou = ACOES.filter(function (k) { return A[k] !== undefined; });
        if (!usou.length) erro(P.id + '/' + a + ': ação sem verbo (use ' + ACOES.join(', ') + ')');

        if (A.para) {
          Object.keys(A.para).forEach(function (p) {
            if (NUMERICAS.indexOf(p) < 0) erro(P.id + '/' + a + ': propriedade "' + p + '" não é animável');
            var de = A.de && A.de[p] !== undefined ? A.de[p] : cur(a, p);
            if (de === undefined) de = A.para[p];
            self._tr(a, p).push({ t: t0, v: de, ease: 'degrau' });
            self._tr(a, p).push({ t: t1, v: A.para[p], ease: dur ? (A.ease || 'suave') : 'degrau' });
            cur(a, p, A.para[p]);
          });
        }
        if (A.pose) {
          (self.poses[a] = self.poses[a] || []).push({ t: t0, nome: A.pose, dur: dur, ease: A.ease, anterior: cPose[a] || 'neutro' });
          cPose[a] = A.pose;
        }
        if (A.expressao) {
          (self.exprs[a] = self.exprs[a] || []).push({ t: t0, nome: A.expressao, dur: dur, ease: A.ease, anterior: cExpr[a] || 'neutro' });
          cExpr[a] = A.expressao;
        }
        if (A.estado) (self.estados[a] = self.estados[a] || []).push({ t: t0, nome: A.estado });
        /* Um selo de artigo e ESTADO VISIVEL: ou esta na tela em t, ou nao
           esta. Estado visivel que depende de t pertence a uma trilha, como
           posicao e opacidade -- e ai a busca para tras o apaga sozinha, sem
           o motor guardar nada. Por isso o roteiro diz "evento" e o motor
           guarda uma JANELA, nao um disparo. */
        if (A.evento) {
          if (EVENTOS.indexOf(A.evento) < 0) {
            erro(P.id + ': evento "' + A.evento + '" fora dos três permitidos');
          }
          var dd = A.dados || {};
          if (!dd.artigo || !dd.guardiao) {
            erro(P.id + ': evento "' + A.evento + '" precisa de dados.artigo e dados.guardiao');
          }
          self.citacoes.push({ t: t0, ate: inicio + P.dur, artigo: dd.artigo,
                               guardiao: dd.guardiao, plano: P.id });
        }
      });

      (P.legendas || []).forEach(function (L) {
        if (L.em == null || L.ate == null) erro(P.id + ': legenda sem em/ate');
        self.legendas.push({ t: inicio + L.em, ate: inicio + L.ate, txt: L.txt,
                             ref: L.ref, plano: P.id });
      });
      inicio += P.dur;
    });

    this.duracao = inicio;
    if (d.duracao != null && Math.abs(d.duracao - inicio) > 1e-6) {
      erro('duração declarada ' + d.duracao + 's, soma dos planos ' + inicio + 's');
    }
    Object.keys(this.trilhas).forEach(function (k) {
      self.trilhas[k].sort(function (a, b) { return a.t - b.t; });
    });
    this.legendas.sort(function (a, b) { return a.t - b.t; });
    this.citacoes.sort(function (a, b) { return a.t - b.t; });
    /* Duas citacoes no mesmo plano (p08 cita os Arts. 37 e 38) nao podem se
       sobrepor: a primeira termina onde a segunda comeca. */
    this.citacoes.forEach(function (c, i) {
      var prox = self.citacoes[i + 1];
      if (prox && prox.t < c.ate) c.ate = prox.t;
    });
  };

  Filme.prototype._montar = function () {
    var self = this;
    Object.keys(this.alvos).forEach(function (a) {
      var meta = self.alvos[a];
      var id = meta.rig || meta.tipo || a;
      if (!Estudio.Rig.definicao(id)) erro('alvo "' + a + '" usa rig "' + id + '" que não existe');
      var camada = meta.camada ||
                   (self.dados.elenco && self.dados.elenco[a] ? 'atores' : 'props');
      if (!self.palco.camadas[camada]) erro('alvo "' + a + '": camada "' + camada + '" não existe');
      self.rigs[a] = Estudio.Rig.criar(id, {
        palco: self.palco.camadas[camada], nome: a,
        paleta: meta.paleta, tema: self._tema
      });
    });
    /* Toda pose e expressão citada existe no rig que vai recebê-la. */
    ['poses', 'exprs'].forEach(function (campo) {
      Object.keys(self[campo]).forEach(function (a) {
        var d = self.rigs[a] && self.rigs[a].def;
        if (!d) return;
        var tabela = campo === 'poses' ? d.poses : d.expressoes;
        self[campo][a].forEach(function (k) {
          if (!tabela[k.nome]) {
            erro('"' + a + '" (' + d.id + ') não tem ' +
                 (campo === 'poses' ? 'a pose' : 'a expressão') + ' "' + k.nome + '"');
          }
        });
      });
    });
  };

  /* ---- O NÚCLEO: puro em t ---------------------------------------- */
  Filme.prototype.renderizar = function (t) {
    t = trava(t, 0, this.duracao);
    var self = this, P = this.planoEm(t);
    if (this.palco && P !== this._ultimoPlano) {
      this.palco.cenario(P.cenario).rotulo(P.titulo);
      this._ultimoPlano = P;
    }
    Object.keys(this.alvos).forEach(function (a) {
      var snap = self.snapshotDe(a, t);
      if (self.rigs[a]) self.rigs[a].aplicar(snap);
    });
    if (this.palco) {
      this.palco.camera(valorNum(this.trilhas['camera|x'], t),
                        valorNum(this.trilhas['camera|y'], t),
                        valorNum(this.trilhas['camera|zoom'], t));
    }
    this.t = t;
    return this;
  };

  Filme.prototype.snapshotDe = function (a, t) {
    var tr = this.trilhas;
    return {
      x: valorNum(tr[a + '|x'], t), y: valorNum(tr[a + '|y'], t),
      escala: valorNum(tr[a + '|escala'], t), op: valorNum(tr[a + '|op'], t),
      espelho: valorNum(tr[a + '|espelho'], t) === 1,
      pose: valorNome(this.poses[a], t, 'neutro'),
      expressao: valorNome(this.exprs[a], t, 'neutro'),
      estado: (function (kfs) {
        if (!kfs || !kfs.length) return 'normal';
        var i = indice(kfs, t);
        return i < 0 ? 'normal' : kfs[i].nome;
      })(this.estados[a])
    };
  };

  Filme.prototype.planoIndice = function (t) {
    var ps = this.planos;
    for (var i = 0; i < ps.length; i++) if (t < ps[i].fim || i === ps.length - 1) return i;
    return 0;
  };
  Filme.prototype.planoEm = function (t) { return this.planos[this.planoIndice(t)]; };
  Filme.prototype.legendaEm = function (t) {
    for (var i = 0; i < this.legendas.length; i++) {
      var L = this.legendas[i];
      if (t >= L.t && t < L.ate) return L;
    }
    return null;
  };
  Filme.prototype.citacaoEm = function (t) {
    for (var i = 0; i < this.citacoes.length; i++) {
      var c = this.citacoes[i];
      if (t >= c.t && t < c.ate) return c;
    }
    return null;
  };
  Filme.prototype.instantaneo = function () {
    var self = this, r = { t: this.t, rigs: {} };
    Object.keys(this.rigs).forEach(function (a) { r.rigs[a] = self.rigs[a].instantaneo(); });
    return r;
  };
  Filme.prototype.tema = function (x) {
    this._tema = x;
    Object.keys(this.rigs).forEach(function (a) { this.rigs[a].tema(x); }, this);
    return this;
  };

  E.Filme = {
    carregar: function (id, opc) {
      var d = (raiz.ESTUDIO_FILMES || {})[id];
      if (!d) throw new Error('Estúdio: filme "' + id + '" não foi carregado.');
      return new Filme(d, opc);
    },
    NUMERICAS: NUMERICAS, ACOES: ACOES
  };
})(window);
