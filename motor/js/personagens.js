/* Folha de personagens — monta a página a partir dos rigs registrados.
   Nada aqui é específico de um personagem: acrescentar um sexto guardião é
   acrescentar um <script src> no HTML. */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var ORDEM = ['dado', 'raposa', 'coruja', 'aguia', 'tartaruga', 'elefante'];
  var ids = ORDEM.filter(function (i) { return Estudio.Rig.definicao(i); });
  var vivos = [];   /* todo rig montado, para o tema e o raio-X alcançarem todos */

  function fatal(msg) {
    var d = document.createElement('div');
    d.className = 'est-erro-fatal';
    d.textContent = 'Estúdio — erro ao montar a folha:\n' + msg;
    document.querySelector('.est-wrap').prepend(d);
  }

  function palco(w, h) {
    var s = document.createElementNS(NS, 'svg');
    s.setAttribute('viewBox', '0 0 200 320');
    if (w) s.setAttribute('width', w);
    if (h) s.setAttribute('height', h);
    s.setAttribute('role', 'img');
    return s;
  }

  /* Uma figura = um palco + um rig + legenda. */
  function figura(id, rotulo, opc) {
    opc = opc || {};
    var f = document.createElement('figure');
    f.className = 'verba';
    var s = palco(opc.w || 150, opc.h || 240);
    f.appendChild(s);
    var c = document.createElement('figcaption');
    c.textContent = rotulo;
    f.appendChild(c);
    var r = Estudio.Rig.criar(id, { palco: s, tema: temaAtual() });
    r.pos(100, 320);
    if (opc.pose) r.pose(opc.pose);
    if (opc.expr) r.expressao(opc.expr);
    s.setAttribute('aria-label', Estudio.Rig.definicao(id).nome + ' — ' + rotulo);
    vivos.push(r);
    return { fig: f, rig: r };
  }

  function temaAtual() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'escuro' : 'claro';
  }

  /* ---- teste de silhueta (R14): pequeno, preto, sem nome ---------- */
  var gs = document.getElementById('gradeSilhueta');
  ids.forEach(function (id) {
    gs.appendChild(figura(id, Estudio.Rig.definicao(id).nome, { w: 110, h: 176 }).fig);
  });

  /* ---- uma ficha por personagem ---------------------------------- */
  var alvo = document.getElementById('fichas');
  ids.forEach(function (id) {
    var def = Estudio.Rig.definicao(id);
    var sec = document.createElement('section');
    sec.className = 'est-card';
    var box = document.createElement('div');
    box.className = 'ficha';

    var esq = document.createElement('div');
    var sp = palco(); sp.setAttribute('class', 'retrato');
    esq.appendChild(sp);
    var rp = Estudio.Rig.criar(id, { palco: sp, tema: temaAtual() });
    rp.pos(100, 320);
    sp.setAttribute('aria-label', def.nome + ', de corpo inteiro, em pose neutra');
    vivos.push(rp);

    var dir = document.createElement('div');
    var poses = Object.keys(def.poses || {});
    var exprs = Object.keys(def.expressoes || {});
    var partes = (def.markup.match(/data-part=/g) || []).length;
    var h = document.createElement('h2');
    h.textContent = def.nome;
    h.style.color = id === 'dado' ? 'var(--est-accent)' : 'var(--rig-' + id + '-ink)';
    dir.appendChild(h);
    var sub = document.createElement('p');
    sub.className = 'selo est-nota';
    sub.textContent = def.epiteto + ' · ' + def.ator;
    dir.appendChild(sub);
    var ul = document.createElement('ul');
    ul.className = 'meta';
    ul.innerHTML = '<li><b>' + partes + '</b> partes · <b>' + poses.length + '</b> poses · <b>' +
                   exprs.length + '</b> expressões</li>' +
                   '<li><b>' + def.markup.length + '</b> bytes de desenho · escala ' +
                   (def.escalaNatural || 1) + '</li>';
    dir.appendChild(ul);

    var g1 = document.createElement('div'); g1.className = 'grade';
    poses.forEach(function (p) { g1.appendChild(figura(id, p, { pose: p, w: 120, h: 192 }).fig); });
    dir.appendChild(g1);
    if (exprs.length > 1) {
      var g2 = document.createElement('div'); g2.className = 'grade';
      g2.style.marginTop = '14px';
      exprs.forEach(function (e) { g2.appendChild(figura(id, e, { expr: e, w: 120, h: 192 }).fig); });
      dir.appendChild(g2);
    }

    box.appendChild(esq); box.appendChild(dir); sec.appendChild(box); alvo.appendChild(sec);
  });

  /* ---- mistura de poses ------------------------------------------ */
  var gm = document.getElementById('gradeMistura');
  var selP = document.getElementById('selPose'), selE = document.getElementById('selExpr');
  var rgP = document.getElementById('rgPose'), rgE = document.getElementById('rgExpr');
  var mistos = ids.filter(function (i) { return i !== 'dado'; }).map(function (id) {
    var o = figura(id, Estudio.Rig.definicao(id).nome, { w: 130, h: 208 });
    gm.appendChild(o.fig); return o.rig;
  });
  /* Vocabulário comum: só entram no seletor as poses que TODOS têm. */
  function comuns(campo) {
    return Object.keys(Estudio.Rig.definicao('raposa')[campo]).filter(function (k) {
      return mistos.every(function (r) { return r.def[campo][k]; });
    });
  }
  comuns('poses').forEach(function (p) { selP.add(new Option(p, p)); });
  comuns('expressoes').forEach(function (e) { selE.add(new Option(e, e)); });
  selP.value = 'apontando'; selE.value = 'feliz';
  function repintar() {
    mistos.forEach(function (r) {
      r.pose('neutro'); r.pose(selP.value, parseFloat(rgP.value));
      r.expressao('neutro'); r.expressao(selE.value, parseFloat(rgE.value));
    });
  }
  [selP, selE, rgP, rgE].forEach(function (el) { el.addEventListener('input', repintar); });
  repintar();

  /* ---- controles do topo ----------------------------------------- */
  function alterna(bt, fn) {
    bt.addEventListener('click', function () {
      var lig = bt.getAttribute('aria-pressed') !== 'true';
      bt.setAttribute('aria-pressed', String(lig));
      fn(lig, bt);
    });
  }
  alterna(document.getElementById('btTema'), function (lig, bt) {
    document.documentElement.setAttribute('data-theme', lig ? 'dark' : 'light');
    bt.textContent = lig ? '☀️ Tema claro' : '🌙 Tema escuro';
    vivos.forEach(function (r) { r.tema(lig ? 'escuro' : 'claro'); });
  });
  alterna(document.getElementById('btXray'), function (lig) {
    document.body.classList.toggle('debug-rig', lig);
    vivos.forEach(function (r) { r.xray(lig); });
  });
  alterna(document.getElementById('btSilhueta'), function (lig, bt) {
    gs.classList.toggle('revelar', lig);
    bt.textContent = lig ? '👤 Esconder nomes' : '👤 Revelar nomes';
  });

  window.ESTUDIO_VIVOS = vivos;   /* usado pelo teste de idempotência */
  window.addEventListener('error', function (e) { fatal(e.message); });
})();
