/* Estúdio dos Guardiões — runtime de personagem (rig).
   =====================================================================
   O PRINCÍPIO: o personagem expõe um setter puro, aplicar(snapshot).
   O filme calcula o snapshot a partir do tempo; o jogo, a partir da
   entrada do usuário. O rig nunca anima sozinho, nunca tem temporizador
   e nunca guarda tempo. Daí saem de graça o seek instantâneo, o modo
   quadrinhos, os testes determinísticos e o reuso em jogo.

   aplicar() é a ÚNICA função que escreve no DOM do personagem. Todo o
   resto é açúcar que monta um snapshot e chama aplicar.
   ===================================================================== */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio = raiz.Estudio || {};
  var REG = raiz.ESTUDIO_RIGS = raiz.ESTUDIO_RIGS || {};
  var NS = 'http://www.w3.org/2000/svg';
  var n = E.n, lerp = E.lerp, trava = E.trava;

  /* ---- deltas ---------------------------------------------------- */
  /* Um delta é {x,y,rot,sx,sy,op}. 's' é atalho para sx e sy juntos. */
  function norm(d) {
    d = d || {};
    var s = d.s != null ? d.s : 1;
    return { x: d.x || 0, y: d.y || 0, rot: d.rot || 0,
             sx: d.sx != null ? d.sx : s, sy: d.sy != null ? d.sy : s,
             op: d.op != null ? d.op : 1 };
  }
  var IDENT = norm({});
  function mistura(a, b, t) {
    a = norm(a); b = norm(b);
    return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t), rot: lerp(a.rot, b.rot, t),
             sx: lerp(a.sx, b.sx, t), sy: lerp(a.sy, b.sy, t), op: lerp(a.op, b.op, t) };
  }
  function soma(a, b) {
    return { x: a.x + b.x, y: a.y + b.y, rot: a.rot + b.rot,
             sx: a.sx * b.sx, sy: a.sy * b.sy, op: a.op * b.op };
  }
  /* Transform com pivô na origem declarada da parte. */
  function matriz(d, ox, oy) {
    if (!d.x && !d.y && !d.rot && d.sx === 1 && d.sy === 1) return '';
    return 'translate(' + n(ox + d.x) + ' ' + n(oy + d.y) + ')' +
           (d.rot ? ' rotate(' + n(d.rot) + ')' : '') +
           (d.sx !== 1 || d.sy !== 1 ? ' scale(' + n(d.sx) + ' ' + n(d.sy) + ')' : '') +
           ' translate(' + n(-ox) + ' ' + n(-oy) + ')';
  }

  /* ---- snapshot --------------------------------------------------- */
  E.snapshotVazio = function () {
    return { x: 0, y: 0, escala: 1, espelho: false, op: 1,
             pose: { nome: 'neutro', mistura: 1, anterior: 'neutro' },
             expressao: { nome: 'neutro', mistura: 1, anterior: 'neutro' },
             estado: 'normal' };
  };

  /* ---- Rig -------------------------------------------------------- */
  function Rig(id, opc) {
    var def = REG[id];
    if (!def) throw new Error('Estúdio: personagem "' + id + '" não registrado.');
    opc = opc || {};
    this.id = id;
    this.def = def;
    this.nome = opc.nome || id;
    this._alt = opc.paleta === 'alt';
    this._tema = opc.tema || 'claro';
    this._snap = E.snapshotVazio();
    this._snap.escala = opc.escala != null ? opc.escala : 1;
    this._cache = {};        /* último transform escrito por parte */
    this._partes = {};
    this._escritas = 0;      /* contador instrumentado, lido pelo teste de perf */
    this._montar(opc.palco);
    this.aplicar(this._snap);
  }

  Rig.prototype._montar = function (palco) {
    var g = document.createElementNS(NS, 'g');
    g.setAttribute('class', 'est-rig est-rig--' + this.id);
    g.setAttribute('data-rig', this.nome);
    /* O significado mora na legenda, não no desenho: o palco inteiro tem
       role="img" e um rótulo por plano; os personagens somem do leitor. */
    g.setAttribute('aria-hidden', 'true');
    /* innerHTML UMA vez, na montagem. Depois disto, só setAttribute. */
    g.innerHTML = this.def.markup;
    this.raiz = g;
    var self = this;
    Array.prototype.forEach.call(g.querySelectorAll('[data-part]'), function (el) {
      self._partes[el.getAttribute('data-part')] = el;
    });
    this._pintar();
    if (palco) palco.appendChild(g);
  };

  /* A arte não muda de cor com o tema por capricho: uma raposa é laranja no
     escuro também. O que muda é o tom, para o personagem não sumir no fundo.
     'alt' é um tingimento por cima (a Raposa-Encarregado do roteiro), e não
     uma quarta paleta — senão cada personagem viraria uma matriz de paletas. */
  Rig.prototype._pintar = function () {
    var def = this.def;
    var base = (this._tema === 'escuro' && def.paletaEscura) ? def.paletaEscura : def.paleta;
    var p = {}, k;
    for (k in base) if (base.hasOwnProperty(k)) p[k] = base[k];
    if (this._alt && def.alt) for (k in def.alt) if (def.alt.hasOwnProperty(k)) p[k] = def.alt[k];
    for (k in p) if (p.hasOwnProperty(k)) this.raiz.style.setProperty('--p-' + k, p[k]);
    this._paleta = p;
  };
  Rig.prototype.tema = function (t) {
    if (t !== this._tema) { this._tema = t; this._pintar(); }
    return this;
  };

  /* ---- O NÚCLEO: puro, idempotente, único escritor do DOM ---------- */
  Rig.prototype.aplicar = function (snap) {
    var def = this.def, poses = def.poses || {}, exprs = def.expressoes || {};
    var po = snap.pose || {}, ex = snap.expressao || {};
    var mp = po.mistura != null ? po.mistura : 1;
    var me = ex.mistura != null ? ex.mistura : 1;
    var pa = this._tab(poses, po.anterior, 'pose'), pb = this._tab(poses, po.nome, 'pose');
    var ea = this._tab(exprs, ex.anterior, 'expressão'), eb = this._tab(exprs, ex.nome, 'expressão');
    var est = this._tab(def.estados || {}, snap.estado, 'estado');

    for (var parte in this._partes) {
      if (!this._partes.hasOwnProperty(parte)) continue;
      var d = soma(mistura(pa[parte], pb[parte], mp), mistura(ea[parte], eb[parte], me));
      var org = (def.origens || {})[parte] || [100, 160];
      this._escrever(parte, matriz(d, org[0], org[1]), d.op);
    }

    /* Raiz: posiciona pelos PÉS (y local 320) e pelo centro (x local 100),
       para que trocar de personagem não mexa no plano. */
    var esc = snap.escala * (def.escalaNatural || 1);
    var sx = snap.espelho ? -esc : esc;
    var t = 'translate(' + n(snap.x) + ' ' + n(snap.y) + ') scale(' + n(sx) + ' ' + n(esc) +
            ') translate(-100 -320)';
    if (this._cache.__raiz !== t) { this.raiz.setAttribute('transform', t); this._cache.__raiz = t; this._escritas++; }
    var op = String(n(snap.op * (est.op != null ? est.op : 1)));
    if (this._cache.__op !== op) { this.raiz.setAttribute('opacity', op); this._cache.__op = op; this._escritas++; }

    if (snap !== this._snap) this._snap = snap;
    if (this._xray) this._desenharXray();
    return this;
  };

  /* Nome que a tabela nao tem e ERRO, nao identidade. Rig.pose() ja
     lancava; aplicar() era a porta que faltava, e e por ela que o filme e o
     jogo entram -- uma pose com erro de digitacao rendia o personagem em
     repouso, que e exatamente o tipo de resultado plausivel que ninguem nota. */
  Rig.prototype._tab = function (tabela, nome, tipo) {
    if (nome == null) return {};
    var d = tabela[nome];
    if (!d) throw new Error('Estúdio: ' + tipo + ' "' + nome + '" não existe em ' + this.id);
    return d;
  };

  /* Escreve só o que mudou. Determinístico: a mesma entrada leva ao mesmo
     DOM, esteja o valor em cache ou não. */
  Rig.prototype._escrever = function (parte, t, op) {
    var el = this._partes[parte], c = this._cache;
    if (c[parte] !== t) {
      if (t) el.setAttribute('transform', t); else el.removeAttribute('transform');
      c[parte] = t; this._escritas++;
    }
    var o = op === 1 ? null : String(n(op)), ck = parte + '#op';
    if (c[ck] !== o) {
      if (o) el.setAttribute('opacity', o); else el.removeAttribute('opacity');
      c[ck] = o; this._escritas++;
    }
  };

  /* ---- açúcar: monta snapshot e chama aplicar --------------------- */
  function muta(rig, fn) { fn(rig._snap); return rig.aplicar(rig._snap); }

  Rig.prototype.pos = function (x, y) { return muta(this, function (s) { s.x = x; s.y = y; }); };
  Rig.prototype.escala = function (v) { return muta(this, function (s) { s.escala = v; }); };
  Rig.prototype.espelhar = function (b) { return muta(this, function (s) { s.espelho = !!b; }); };
  Rig.prototype.opacidade = function (v) { return muta(this, function (s) { s.op = v; }); };
  Rig.prototype.estado = function (nome) { return muta(this, function (s) { s.estado = nome; }); };
  Rig.prototype.pose = function (nome, m) {
    if (!(this.def.poses || {})[nome]) throw new Error('Estúdio: pose "' + nome + '" não existe em ' + this.id);
    return muta(this, function (s) {
      if (m == null) { s.pose = { nome: nome, mistura: 1, anterior: nome }; }
      else { s.pose = { nome: nome, mistura: m, anterior: s.pose.nome }; }
    });
  };
  Rig.prototype.expressao = function (nome, m) {
    if (!(this.def.expressoes || {})[nome]) throw new Error('Estúdio: expressão "' + nome + '" não existe em ' + this.id);
    return muta(this, function (s) {
      if (m == null) { s.expressao = { nome: nome, mistura: 1, anterior: nome }; }
      else { s.expressao = { nome: nome, mistura: m, anterior: s.expressao.nome }; }
    });
  };

  /* ---- consulta: o que o jogo precisa e o filme não --------------- */
  Rig.prototype.instantaneo = function () { return JSON.parse(JSON.stringify(this._snap)); };
  Rig.prototype.parte = function (nome) { return this._partes[nome] || null; };

  /* AABB puro, sem tocar no DOM: física de jogo nunca consulta layout. */
  Rig.prototype.caixa = function () {
    var h = this.def.hitbox;
    if (!h) return null;
    var s = this._snap, esc = s.escala * (this.def.escalaNatural || 1);
    var x0 = s.espelho ? 200 - (h[0] + h[2]) : h[0];
    return { x: n(s.x + (x0 - 100) * esc), y: n(s.y + (h[1] - 320) * esc),
             w: n(h[2] * esc), h: n(h[3] * esc) };
  };
  Rig.prototype.contem = function (x, y) {
    var c = this.caixa();
    return !!c && x >= c.x && x <= c.x + c.w && y >= c.y && y <= c.y + c.h;
  };
  Rig.prototype.destruir = function () {
    if (this.raiz && this.raiz.parentNode) this.raiz.parentNode.removeChild(this.raiz);
    this._partes = {}; this._cache = {};
  };

  /* ---- modo raio-X: contorno, origem de transform, hitbox, âncoras -- */
  Rig.prototype.xray = function (lig) {
    this._xray = !!lig;
    if (!lig && this._gx) { this._gx.parentNode.removeChild(this._gx); this._gx = null; return this; }
    if (lig) this._desenharXray();
    return this;
  };
  Rig.prototype._desenharXray = function () {
    if (this._gx) this._gx.parentNode.removeChild(this._gx);
    var g = this._gx = document.createElementNS(NS, 'g');
    g.setAttribute('class', 'est-xray');
    var def = this.def, self = this;
    function add(tag, attrs, cls) {
      var e = document.createElementNS(NS, tag);
      for (var k in attrs) e.setAttribute(k, attrs[k]);
      e.setAttribute('class', cls); g.appendChild(e);
    }
    var h = def.hitbox;
    if (h) add('rect', { x: h[0], y: h[1], width: h[2], height: h[3] }, 'est-xray-hit');
    Object.keys(this._partes).forEach(function (p) {
      var o = (def.origens || {})[p]; if (!o) return;
      add('circle', { cx: o[0], cy: o[1], r: 3 }, 'est-xray-origem');
    });
    Object.keys(def.ancoras || {}).forEach(function (a) {
      var p = def.ancoras[a];
      add('circle', { cx: p[0], cy: p[1], r: 2.5 }, 'est-xray-ancora');
    });
    this.raiz.appendChild(g);
  };

  /* ---- fábrica ---------------------------------------------------- */
  E.Rig = {
    registrar: function (def) { REG[def.id] = def; },
    definicao: function (id) { return REG[id]; },
    ids: function () { return Object.keys(REG); },
    criar: function (id, opc) { return new Rig(id, opc); }
  };
})(window);
