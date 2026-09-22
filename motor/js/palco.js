/* Estúdio dos Guardiões — o palco.
   Um <svg> de 1280x720 com camadas em ordem fixa dentro de <g data-camera>.
   A legenda fica FORA do svg: texto de verdade, selecionável, traduzível e
   que não sofre o zoom da câmera. */
(function (raiz) {
  'use strict';
  var E = raiz.Estudio = raiz.Estudio || {};
  var NS = 'http://www.w3.org/2000/svg';
  /* 'cena' e cenografia que se move (a porta do cofre): fica ATRAS de quem
     atua. 'props' e objeto em uso, na frente. */
  var CAMADAS = ['fundo', 'cenario', 'cena', 'atores', 'props', 'efeitos'];
  E.PALCO = { w: 1280, h: 720, chao: 620 };

  function Palco(host) {
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + E.PALCO.w + ' ' + E.PALCO.h);
    svg.setAttribute('class', 'est-palco');
    /* O significado do filme mora na legenda; o palco é uma imagem só. */
    svg.setAttribute('role', 'img');
    var cam = document.createElementNS(NS, 'g');
    cam.setAttribute('data-camera', '');
    svg.appendChild(cam);
    this.svg = svg;
    this._cam = cam;
    this.camadas = {};
    var self = this;
    CAMADAS.forEach(function (n) {
      var g = document.createElementNS(NS, 'g');
      g.setAttribute('data-camada', n);
      cam.appendChild(g);
      self.camadas[n] = g;
    });
    this._cenario = null;
    this._camTxt = null;
    if (host) host.appendChild(svg);
  }

  /* Trocar de cenário é escrita de markup — acontece 12 vezes num filme,
     nunca por quadro. Depois disso, só transform. */
  Palco.prototype.cenario = function (id) {
    if (id === this._cenario) return this;
    var def = (raiz.ESTUDIO_CENARIOS || {})[id];
    if (!def) throw new Error('Estúdio: cenário "' + id + '" não existe.');
    this.camadas.cenario.innerHTML = def.markup;
    this._cenario = id;
    return this;
  };

  Palco.prototype.camera = function (cx, cy, zoom) {
    /* zoom 0 virava 1 em silencio, e um plano declarado com zoom zero
       tocava enquadrado como se estivesse certo. */
    var z = zoom == null ? 1 : zoom, n = E.n;
    if (!(z > 0)) throw new Error('Estúdio: zoom de câmera tem de ser positivo (veio ' + zoom + ').');
    var t = 'translate(' + n(E.PALCO.w / 2) + ' ' + n(E.PALCO.h / 2) + ') scale(' + n(z) +
            ') translate(' + n(-cx) + ' ' + n(-cy) + ')';
    if (t !== this._camTxt) { this._cam.setAttribute('transform', t); this._camTxt = t; }
    return this;
  };

  Palco.prototype.rotulo = function (txt) {
    this.svg.setAttribute('aria-label', txt || '');
    return this;
  };

  E.Palco = { criar: function (host) { return new Palco(host); }, CAMADAS: CAMADAS };
})(window);
