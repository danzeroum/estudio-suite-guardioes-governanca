/* Jogo — runtime dos jogos do estúdio.
   =====================================================================
   Nasce MÍNIMO, pelo que o primeiro jogo realmente usa. Ficaram de fora,
   por não terem cliente: colide() (nenhuma física aqui), arrastavel()
   (arrastar é enhancement, e este jogo é de teclado) e aoClicarRig() (as
   opções são <button> de verdade em HTML, não formas no palco). Cada um
   nasce com o jogo que precisar — construir um motor de jogo especulativo
   é como se descobre, tarde, que metade não servia.

   O laço vem de relogio.js, o mesmo do filme. O personagem vem de rig.js,
   o mesmo do filme, e é dirigido por ENTRADA em vez de por tempo — que é
   justamente o caminho que o filme nunca exercitou.
   ===================================================================== */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio = raiz.Estudio || {};

  /* Aleatório com semente: um jogo determinístico sob semente é um jogo
     testável, e custa quase nada no dia 1 (mulberry32). */
  function prng(semente) {
    var a = semente >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function embaralhar(lista, rnd) {
    var v = lista.slice();
    for (var i = v.length - 1; i > 0; i--) {
      var j = Math.floor(rnd() * (i + 1));
      var x = v[i]; v[i] = v[j]; v[j] = x;
    }
    return v;
  }

  E.Jogo = function (opc) {
    var d = (raiz.ESTUDIO_JOGOS || {})[opc.jogo];
    if (!d) throw new Error('Estúdio: jogo "' + opc.jogo + '" não foi carregado.');

    var el = {}, palco, dpo, relogio;
    /* 'escolha' e o CURSOR e acompanha o foco do DOM; 'marcada' e o que
       foi de fato respondido (-1 = ninguem, prazo esgotado). Sao coisas
       diferentes, e tratar as duas como uma so era o defeito. */
    var fila, i = 0, resta = 0, escolha = 0, marcada = -1, respondido = false;
    var placar = { acertos: 0, erros: 0, porInciso: {} };
    /* Sob movimento reduzido o jogo roda SEM cronômetro: o prazo é mecânica,
       não decoração, e quem pede movimento reduzido recebe todo o conteúdo
       sem a pressão -- não um jogo pela metade. */
    var comPrazo = !(raiz.matchMedia && raiz.matchMedia('(prefers-reduced-motion: reduce)').matches);

    ['palco', 'pedido', 'opcoes', 'prazo', 'feedback', 'status', 'contador',
     'fim', 'placar'].forEach(function (k) { el[k] = opc[k] ? document.getElementById(opc[k]) : null; });

    function anunciar(t) { if (el.status) el.status.textContent = t; }

    palco = E.Palco.criar(el.palco);
    palco.cenario(opc.cenario || 'balcao').rotulo('A Encarregada atende na sala do titular');
    dpo = E.Rig.criar('raposa', { palco: palco.camadas.atores, nome: 'dpo', paleta: 'alt' });
    dpo.pos(640, E.PALCO.chao).escala(1.35);

    fila = embaralhar(d.situacoes, prng(opc.semente != null ? opc.semente : d.semente));

    /* As opções são <button> reais: teclado, leitor de tela e mouse vêm
       juntos, sem reimplementar foco. Teclado no dia 1, não como retrofit. */
    d.direitos.forEach(function (dir, k) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'est-opcao';
      b.id = 'op' + k;
      b.innerHTML = '';
      var n = document.createElement('kbd');
      n.textContent = String(k + 1);
      b.appendChild(n);
      b.appendChild(document.createTextNode(' ' + dir.rotulo));
      b.addEventListener('click', function () { responder(k); });
      el.opcoes.appendChild(b);
    });

    /* O foco do DOM e a escolha sao a MESMA coisa. Setas que moviam so o
       aria-current deixavam quem usa Tab e quem usa setas olhando para opcoes
       diferentes -- e o Enter respondia a opcao errada, nao a focada. */
    function focar(k) {
      escolha = (k + d.direitos.length) % d.direitos.length;
      var b = el.opcoes.children[escolha];
      if (b) b.focus();
      pintar();
    }
    function escolhida() {
      var k = Array.prototype.indexOf.call(el.opcoes.children, document.activeElement);
      return k < 0 ? escolha : k;
    }

    function pintar() {
      var s = fila[i], dir = d.direitos;
      if (el.pedido) el.pedido.textContent = '“' + s.pedido + '”';
      if (el.contador) el.contador.textContent = (i + 1) + ' de ' + fila.length;
      Array.prototype.forEach.call(el.opcoes.children, function (b, k) {
        b.setAttribute('aria-current', k === escolha ? 'true' : 'false');
        /* aria-disabled, e nao disabled: desabilitar o botao focado DESTROI o
           foco, e quem usa leitor de tela era devolvido ao topo do documento a
           cada resposta. responder() ja recusa a segunda chamada. */
        b.setAttribute('aria-disabled', String(respondido));
        b.classList.remove('certa', 'errada');
        if (respondido) {
          if (dir[k].inciso === s.inciso) b.classList.add('certa');
          else if (k === marcada) b.classList.add('errada');
        }
      });
      if (el.prazo) {
        el.prazo.hidden = !comPrazo;
        if (comPrazo) el.prazo.style.setProperty('--f', Math.max(0, resta / d.prazo));
      }
    }

    /* k fora da faixa e resposta VAZIA: o prazo esgotou e ninguem escolheu.
       A sentinela precisa de um LEITOR, nao de um comentario -- sem este
       ramo, d.direitos[-1] era undefined, a excecao subia de dentro de
       quadro() e a linha que reagenda o rAF nunca rodava: o cronometro
       morria de vez, o placar nao contava e a tela nao dizia nada. */
    function responder(k) {
      if (respondido) return;
      var vazia = !d.direitos[k];
      marcada = vazia ? -1 : k;
      if (!vazia) escolha = k;
      respondido = true;
      var s = fila[i], acertou = !vazia && d.direitos[k].inciso === s.inciso;
      var certo = d.direitos.filter(function (x) { return x.inciso === s.inciso; })[0];
      placar[acertou ? 'acertos' : 'erros']++;
      placar.porInciso[s.inciso] = placar.porInciso[s.inciso] || { certo: 0, errado: 0 };
      placar.porInciso[s.inciso][acertou ? 'certo' : 'errado']++;
      dpo.expressao(acertou ? 'feliz' : 'preocupado');
      dpo.pose(acertou ? 'entregando' : 'protegendo');
      if (el.feedback) {
        el.feedback.textContent = (acertou ? '✓ ' : vazia ? '⏱ Tempo esgotado. ' : '✗ ') +
          'Art. 18, ' + certo.inciso + ' — ' + certo.texto + '.';
        el.feedback.className = 'est-feedback ' + (acertou ? 'certa' : 'errada');
      }
      anunciar((acertou ? 'Certo. ' : vazia ? 'Tempo esgotado. ' : 'Errado. ') +
               'Art. 18, inciso ' + certo.inciso + ': ' + certo.rotulo +
               '. Aperte Enter para o próximo.');
      pintar();
    }

    function proximo() {
      i++;
      if (i >= fila.length) return terminar();
      respondido = false; marcada = -1; escolha = escolhida(); resta = d.prazo;
      dpo.expressao('neutro').pose('neutro');
      if (el.feedback) { el.feedback.textContent = ''; el.feedback.className = 'est-feedback'; }
      pintar();
      anunciar('Pedido ' + (i + 1) + ' de ' + fila.length + ': ' + fila[i].pedido);
    }

    function terminar() {
      relogio.parar();
      if (el.fim) el.fim.hidden = false;
      if (el.placar) {
        el.placar.textContent = placar.acertos + ' de ' + fila.length + ' pedidos roteados '
          + 'para o direito certo.';
      }
      if (el.opcoes) el.opcoes.hidden = true;
      if (el.prazo) el.prazo.hidden = true;
      /* Esconder o container leva junto o foco que estava dentro dele: sem
         isto, terminar o jogo devolvia a pessoa ao topo do documento. */
      if (el.fim && el.fim.focus) el.fim.focus();
      anunciar('Fim. ' + placar.acertos + ' de ' + fila.length + '.');
    }

    relogio = E.Relogio(function (dt) {
      if (!comPrazo || respondido || i >= fila.length) return;
      resta -= dt;
      if (resta <= 0) { resta = 0; responder(-1); }   /* -1 = nenhuma: tempo esgotado */
      else if (el.prazo) el.prazo.style.setProperty('--f', resta / d.prazo);
    });

    document.addEventListener('keydown', function (ev) {
      if (ev.metaKey || ev.ctrlKey || ev.altKey || i >= fila.length) return;
      var k = ev.key, usou = true;
      if (k >= '1' && k <= String(d.direitos.length)) {
        if (!respondido) responder(parseInt(k, 10) - 1);
      } else if (k === 'ArrowDown') { focar(escolhida() + 1); }
      else if (k === 'ArrowUp') { focar(escolhida() - 1); }
      else if (k === 'Enter' || k === ' ') { respondido ? proximo() : responder(escolhida()); }
      else usou = false;
      if (usou) ev.preventDefault();
    });

    resta = d.prazo;
    pintar();
    if (comPrazo) relogio.tocar();
    anunciar('Pedido 1 de ' + fila.length + ': ' + fila[0].pedido);

    return {
      dados: d, palco: palco, dpo: dpo, relogio: relogio,
      responder: responder, proximo: proximo,
      indice: function () { return i; },
      placar: function () { return placar; },
      fila: function () { return fila.map(function (s) { return s.inciso; }); },
      comPrazo: function () { return comPrazo; },
      _raf: relogio._raf, avancar: relogio.avancar
    };
  };
})(window);
