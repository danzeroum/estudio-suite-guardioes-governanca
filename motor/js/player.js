/* Player — o relógio e o transporte.
   =====================================================================
   O tempo tem UM lugar: filme.t, escrito só por renderizar(). O player
   não guarda um t próprio — é assim que o relógio do transporte nunca
   diverge da imagem na tela.

   Dois modos, um caminho: ambos chamam renderizar(t). A diferença é quem
   escolhe t — o laço, continuamente, ou a pessoa, de plano em plano.

   A legenda NÃO é uma região ao vivo. aria-live="polite" enfileira em vez
   de substituir: 30 legendas em 124 s virariam uma fila dessincronizada da
   imagem. Quem usa leitor de tela recebe a transcrição, que é o artefato
   acessível principal, mais um role="status" que anuncia só ação do
   usuário — nunca o laço.
   ===================================================================== */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio;
  var mmss = E.mmss;  /* a construcao de DOM de boot mora em chassi.js */

  E.Player = function (opc) {
    var el = {}, filme, palco, modo = 'movimento';
    /* A camada de som (CP-004): escrava do tempo, nunca dona dele. Nasce
       desligada e só existe quando o filme DECLARA ter trilha — o campo
       audio: true no dado, o mesmo que o portão de sonorizacao lê. */
    var som = null;
    /* O selo leva a pagina do guardiao, que NAO e desta suite: a lei e de
       quem a publica. O prefixo entra por opcao, e a pagina o declara a
       partir de lei.lock -- fixar '../docs/' aqui amarrava o motor ao
       layout de um consumidor so. */
    var baseGuardiao = opc.baseGuardiao || '';
    var legAtual, planoAtual, citAtual, segAtual = -1, legendasVisiveis = true;

    function id(k) { return opc[k] ? document.getElementById(opc[k]) : null; }

    function fatal(msg) { E.Chassi.fatal(opc.filme, msg); }

    function anunciar(txt) { if (el.status) el.status.textContent = txt; }

    /* ---- o tempo ---------------------------------------------------- */
    function agora() { return filme.t; }

    function irPara(x) { filme.renderizar(x); cromo(); }

    /* O laço mora em relogio.js: o jogo precisa do mesmo, e um segundo
       laço escrito à mão seria a mesma lógica sutil duplicada. O player só
       diz o que fazer com o dt. */
    var relogio = E.Relogio(function (dt) {
      irPara(agora() + dt);
      if (agora() >= filme.duracao) parar();
    });
    /* A costura de teste: o mesmo avanço do laço, sem rAF e sem relógio de
       parede. Todo caso de tempo do teste passa por aqui. */
    function avancar(dt) { relogio.avancar(dt); }

    function tocar() {
      if (relogio.tocando() || modo === 'quadrinhos') return;
      if (agora() >= filme.duracao) irPara(0);
      relogio.tocar();
      if (som) som.tocar();
      cromo(); anunciar('Tocando');
    }
    function parar(quieto) {
      relogio.parar();
      if (som) som.pausar();
      cromo(); if (!quieto) anunciar('Pausado');
    }
    function alternar() { relogio.tocando() ? parar() : tocar(); }

    /* ---- modos ------------------------------------------------------ */
    function trocarModo(m) {
      if (m === modo) return;
      parar(true);
      modo = m;
      if (el.scrub) {
        var q = modo === 'quadrinhos';
        el.scrub.min = 0;
        el.scrub.max = q ? filme.planos.length - 1 : filme.duracao;
        el.scrub.step = q ? 1 : 0.05;
      }
      if (el.btPlay) {
        el.btPlay.textContent = modo === 'quadrinhos' ? '▶ Reproduzir com movimento' : '▶ Tocar';
      }
      if (el.btModo) el.btModo.setAttribute('aria-pressed', String(modo === 'quadrinhos'));
      planoAtual = legAtual = citAtual = null; segAtual = -1;
      irPara(modo === 'quadrinhos' ? filme.planos[filme.planoIndice(agora())].poster : agora());
      anunciar(modo === 'quadrinhos' ? 'Modo quadrinhos' : 'Modo movimento');
    }

    function irPlano(i) {
      i = Math.max(0, Math.min(filme.planos.length - 1, i));
      var P = filme.planos[i];
      irPara(modo === 'quadrinhos' ? P.poster : P.inicio);
      anunciar('Plano ' + (i + 1) + ' de ' + filme.planos.length + ': ' + P.titulo);
    }

    /* ---- a cromagem: só escreve o que mudou -------------------------- */
    function cromo() {
      var t = agora(), i = filme.planoIndice(t), P = filme.planos[i];
      var q = modo === 'quadrinhos';
      if (som) som.porQuadro(t, relogio.tocando(), q);

      if (P !== planoAtual) {
        planoAtual = P;
        if (el.titulo) {
          el.titulo.textContent = (i + 1) + '/' + filme.planos.length + ' · ' + P.titulo;
          el.titulo.style.color = P.guardiao ? 'var(--rig-' + P.guardiao + '-ink)'
                                             : 'var(--est-ink-soft)';
        }
        if (el.regua) Array.prototype.forEach.call(el.regua.children, function (b, k) {
          b.setAttribute('aria-current', k === i ? 'true' : 'false');
        });
      }

      /* Em quadrinhos a legenda do plano vem INTEIRA: quem pede movimento
         reduzido não pode receber menos filme, e aqui a legenda é tudo. */
      var L = q ? null : filme.legendaEm(t);
      if (q) {
        if (planoAtual !== legAtual) {
          legAtual = planoAtual;
          if (el.legenda) {
            el.legenda.textContent = filme.legendas.filter(function (x) {
              return x.plano === P.id;
            }).map(function (x) { return x.txt; }).join('\n');
          }
        }
      } else if (L !== legAtual) {
        legAtual = L;
        if (el.legenda) el.legenda.textContent = L ? L.txt : '';
      }

      /* Em quadrinhos o selo e o do PLANO, nao o do instante do poster: a
         citacao costuma cair depois dele, e quem le em quadrinhos ficaria
         sem a referencia. Mesma completude que vale para a legenda. */
      var C = q ? (filme.citacoes.filter(function (c) { return c.plano === P.id; })[0] || null)
                : filme.citacaoEm(t);
      if (C !== citAtual) {
        citAtual = C;
        if (el.selo) {
          /* Mostrar e esconder sao simetricos, e os atributos entram sempre
             na mesma ordem. Sem isso o outerHTML do selo dependia do CAMINHO
             ate t -- href antes de style vindo de um lado, depois vindo do
             outro -- e o teste de pureza acusava diferenca sem que nada
             mudasse na tela. Zerar a propriedade nao basta: o atributo
             'style' sobrevive e guarda a posicao. */
          if (C) {
            var g = Estudio.Rig.definicao(C.guardiao);
            el.selo.hidden = false;
            /* Ordinal ate o 9o, cardinal do 10 em diante -- convencao de
               citacao legal, a mesma que o roteiro em prosa usa. */
            el.selo.textContent = 'Art. ' + C.artigo + (C.artigo < 10 ? 'º' : '') +
                                  ' · ' + (g ? g.nome : C.guardiao);
            if (baseGuardiao) el.selo.setAttribute('href', baseGuardiao + C.guardiao + '.html');
            else el.selo.removeAttribute('href');
            el.selo.setAttribute('style', 'color:var(--rig-' + C.guardiao +
                                 '-ink);border-color:var(--rig-' + C.guardiao + ')');
          } else {
            el.selo.hidden = true;
            el.selo.textContent = '';
            el.selo.removeAttribute('href');
            el.selo.removeAttribute('style');
          }
        }
      }

      if (el.scrub && document.activeElement !== el.scrub) {
        el.scrub.value = q ? i : t;
      }
      if (el.scrub) {
        el.scrub.setAttribute('aria-valuetext', q
          ? 'Plano ' + (i + 1) + ' de ' + filme.planos.length + ': ' + P.titulo
          : mmss(t) + ' de ' + mmss(filme.duracao));
      }
      var seg = q ? -2 : Math.floor(t);
      if (seg !== segAtual) {
        segAtual = seg;
        if (el.tempo) {
          el.tempo.textContent = q
            ? 'Plano ' + (i + 1) + '/' + filme.planos.length + ' · ' +
              mmss(P.inicio) + '–' + mmss(P.fim)
            : mmss(t) + ' / ' + mmss(filme.duracao);
        }
      }
      if (el.btPlay && !q) el.btPlay.textContent = relogio.tocando() ? '❚❚ Pausar' : '▶ Tocar';
    }

    /* ---- construção -------------------------------------------------- */
    try {
      ['palco', 'legenda', 'status', 'regua', 'titulo', 'selo', 'transcricao',
       'scrub', 'tempo', 'btPlay', 'btLegendas', 'btModo', 'btSom'].forEach(function (k) { el[k] = id(k); });
      palco = E.Palco.criar(el.palco);
      filme = E.Filme.carregar(opc.filme, { palco: palco, tema: opc.tema || 'claro' });
      if (el.btSom && filme.dados.audio && E.Som) {
        som = E.Som.criar({ bt: el.btSom, filme: filme,
                            base: opc.baseAudio || '../', anunciar: anunciar });
        el.btSom.addEventListener('click', function () {
          /* silencioso quando o filme nao esta tocando: armar sem tocar.
             O audio nunca avança sem o filme (CP-004, escravo do tempo). */
          som.alternar(modo === 'quadrinhos' || !relogio.tocando());
        });
      }

      E.Chassi.regua(el.regua, filme, irPlano);
      E.Chassi.transcricao(el.transcricao, filme, function (t) {
        irPara(t); anunciar('Foi para ' + mmss(t));
      });

      if (el.scrub) {
        el.scrub.addEventListener('pointerdown', function () { parar(true); });
        el.scrub.addEventListener('input', function () {
          var v = parseFloat(el.scrub.value);
          irPara(modo === 'quadrinhos' ? filme.planos[v].poster : v);
        });
      }
      if (el.btPlay) el.btPlay.addEventListener('click', function () {
        if (modo === 'quadrinhos') { trocarModo('movimento'); tocar(); } else alternar();
      });
      if (el.btModo) el.btModo.addEventListener('click', function () {
        trocarModo(modo === 'quadrinhos' ? 'movimento' : 'quadrinhos');
      });
      if (el.btLegendas) el.btLegendas.addEventListener('click', function () {
        legendasVisiveis = !legendasVisiveis;
        el.legenda.hidden = !legendasVisiveis;
        el.btLegendas.setAttribute('aria-pressed', String(!legendasVisiveis));
        anunciar(legendasVisiveis ? 'Legendas visíveis' : 'Legendas ocultas');
      });

      document.addEventListener('keydown', function (ev) {
        if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
        var alvo = ev.target, botao = alvo && /^(BUTTON|SUMMARY|A)$/.test(alvo.tagName);
        var k = ev.key, usou = true;
        if (k === ' ' || k === 'k' || k === 'K') { if (botao) return; alternar(); }
        else if (k === 'ArrowRight') irPara(agora() + 5);
        else if (k === 'ArrowLeft') irPara(agora() - 5);
        else if (k === 'l' || k === 'L') irPara(agora() + 10);
        else if (k === 'j' || k === 'J') irPara(agora() - 10);
        else if (k === ']') irPlano(filme.planoIndice(agora()) + 1);
        else if (k === '[') {
          var i = filme.planoIndice(agora());
          irPlano(agora() > filme.planos[i].inicio + 0.35 ? i : i - 1);
        }
        else if (k === 'Home') irPara(0);
        else if (k === 'End') irPara(filme.duracao);
        else if (k >= '0' && k <= '9') irPara(parseInt(k, 10) / 10 * filme.duracao);
        else if (k === 'c' || k === 'C') { if (el.btLegendas) el.btLegendas.click(); }
        else if (k === 's' || k === 'S') { if (el.btModo) el.btModo.click(); }
        else usou = false;
        if (usou) ev.preventDefault();
      });

      /* Nasce em quadrinhos se o sistema pede movimento reduzido. A
         preferência do sistema É a persistência: nada de localStorage, que
         sob file:// é origem nula e pode nem existir. */
      var mq = raiz.matchMedia && raiz.matchMedia('(prefers-reduced-motion: reduce)');
      var escolheu = false;
      if (mq && mq.matches) modo = 'quadrinhos';
      if (mq && mq.addEventListener) mq.addEventListener('change', function (e) {
        if (!escolheu) trocarModo(e.matches ? 'quadrinhos' : 'movimento');
      });
      if (el.btModo) el.btModo.addEventListener('click', function () { escolheu = true; });

      var inicial = modo;
      modo = inicial === 'quadrinhos' ? 'movimento' : 'quadrinhos';
      trocarModo(inicial);          /* força a montagem completa da cromagem */
      irPara(0);
    } catch (e) {
      fatal(e.message);
      throw e;
    }

    raiz.addEventListener('error', function (ev) { fatal(String(ev.message)); });

    return {
      filme: filme, palco: palco,
      tocar: tocar, pausar: parar, alternar: alternar,
      irPara: irPara, avancar: avancar, irPlano: irPlano,
      t: agora,
      tocando: relogio.tocando,
      modo: function () { return modo; },
      indice: function () { return filme.planoIndice(agora()); },
      _som: som,                /* o hook de teste, como _raf e _quadro */
      _raf: relogio._raf,
      _quadro: relogio._quadro
    };
  };
})(window);
