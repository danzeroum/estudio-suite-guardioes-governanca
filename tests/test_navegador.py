#!/usr/bin/env python3
"""Testes do Estudio dos Guardioes, em Chromium.

Fase 1 (o que existe hoje): os rigs, a folha de personagens e as regras que
sustentam o motor do filme. Os casos do filme (busca determinista, legendas,
modo quadrinhos) entram aqui na Fase 3, quando houver filme.

As duas regras que mais valem estao no topo, de proposito:

R1 — identidade do estado. aplicar(instantaneo()) tem de produzir o MESMO
DOM, em qualquer instante. A maioria dos bugs de busca vem de snapshot
incompleto (um campo esquecido, um ciclo ligado fora do estado); uma
assercao de idempotencia pega a classe inteira de uma vez, e pega agora, e
nao depois que existirem 12 planos para depurar.

Fumaca em file:// — o estudio inteiro depende de nao haver fetch nem
type="module". Sob http isso nunca falha, entao a regra so e de verdade se
alguem abrir a pagina por file://. E barato e protege a restricao que mais
volta a morder quem so testa por HTTP.

Sobe o proprio servidor e usa o Chromium ja instalado no ambiente.
"""
import functools
import json
import http.server
import re
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
PORTA = 8778
B = f"http://localhost:{PORTA}/"
RIGS = ["dado", "raposa", "coruja", "aguia", "tartaruga", "elefante"]

# Mesma convencao de tools/test-regressao.py: None deixa o Playwright usar a
# instalacao dele, e um launch que falha morre com instrucao, nunca em silencio.
EXE = next((str(p) for p in Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome")), None)


GRAVAR = "--gravar" in sys.argv
BASE_RIGS = RAIZ / "motor" / "baseline"
gravados = []


def referencia(rel, conteudo, rotulo):
    """Compara um instantaneo de TEXTO contra uma referencia em disco.

    Pixel-a-pixel nao roda em CI aqui: as fontes mudam por ambiente e o desvio
    vai a 6-34%, como o cabecalho de tools/test-visual.py explica. Mas o
    defeito da Fase 5 -- a camera errada em 10 dos 12 planos -- nunca foi de
    pixel: foi de transform. Texto pega essa classe inteira, e roda em CI.

    Regravar e um comando separado (--gravar), de proposito: referencia que se
    atualiza sozinha nao e referencia, e um registro do ultimo acidente."""
    # rigs/ e do motor; baseline de plano mora junto do filme a que pertence.
    alvo = (BASE_RIGS / rel) if rel.startswith("rigs/") else (RAIZ / rel)
    if GRAVAR:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")
        gravados.append(rel)
        return
    if not alvo.exists():
        chk(False, f"{rotulo} -- referencia ausente em {alvo.relative_to(RAIZ)}; "
                   f"rode: python3 tests/test_navegador.py --gravar")
        return
    lido = alvo.read_text(encoding="utf-8")
    if lido == conteudo:
        chk(True, rotulo)
        return
    a, b = lido.split("\n"), conteudo.split("\n")
    linha = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    chk(False, f"{rotulo} -- difere da referencia na linha {linha + 1}: "
               f"{(a[linha] if linha < len(a) else '(fim)')[:60]!r} -> "
               f"{(b[linha] if linha < len(b) else '(fim)')[:60]!r}")


def instantaneo_do_palco(pg, t_seg):
    """Camera, cenario e o transform/opacidade de cada peca -- e nada mais.
    O markup estatico do cenario ja e coberto pela arte dos rigs; repeti-lo
    aqui so faria a referencia pesar e o diff ficar ilegivel."""
    # String CRUA: sem o r, o \n deste JS vira quebra de linha real antes
    # de chegar ao navegador, e o literal de string fecha no lugar errado.
    return pg.evaluate(r"""(t) => {
      var p = ESTUDIO_PLAYER;
      p.irPara(t);
      var svg = p.palco.svg, L = [];
      L.push('cenario: ' + p.palco._cenario);
      L.push('rotulo: ' + (svg.getAttribute('aria-label') || ''));
      L.push('camera: ' + (p.palco._cam.getAttribute('transform') || ''));
      Array.prototype.forEach.call(svg.querySelectorAll('[data-rig]'), function (g) {
        L.push('rig ' + g.getAttribute('data-rig') +
               ' | t=' + (g.getAttribute('transform') || '-') +
               ' | op=' + (g.getAttribute('opacity') || '-'));
        Array.prototype.forEach.call(g.querySelectorAll('[data-part]'), function (e) {
          var tr = e.getAttribute('transform'), op = e.getAttribute('opacity');
          if (tr || op) L.push('    ' + e.getAttribute('data-part') +
                               ' | t=' + (tr || '-') + ' | op=' + (op || '-'));
        });
      });
      return L.join('\n') + '\n';
    }""", t_seg)


def abrir(pw):
    try:
        return pw.chromium.launch(**({"executable_path": EXE} if EXE else {}))
    except Exception as erro:
        raise SystemExit(
            "  ERRO: nao foi possivel abrir o Chromium.\n"
            "  Instale com:  python3 -m playwright install chromium\n"
            f"  (detalhe: {erro})")


ok, bad = [], []
POR_ALVO = {}
ALVOS_CONHECIDOS = sorted(
    [d.name for d in (RAIZ / "filmes").iterdir() if d.is_dir()]
    + [d.name for d in (RAIZ / "jogos").iterdir() if d.is_dir()])


def chk(c, msg):
    (ok if c else bad).append(msg)
    # A evidencia por filme e o que o modulo de automelhorias le depois. Sem
    # isto o unico registro de uma execucao seria "passou" ou "falhou", e um
    # portao que reprova sempre no mesmo filme ficaria indistinguivel de um
    # que reprovou uma vez.
    for alvo in ALVOS_CONHECIDOS:
        if alvo in msg:
            POR_ALVO.setdefault(alvo, {"ok": 0, "achados": []})
            if c:
                POR_ALVO[alvo]["ok"] += 1
            else:
                POR_ALVO[alvo]["achados"].append(msg)


def servidor():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(RAIZ))
    socketserver.TCPServer.allow_reuse_address = True
    s = socketserver.TCPServer(("", PORTA), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def estaticos():
    """R16 — cor so por token. Zero hex dentro do markup de um rig: a cor
    canonica mora no bloco paleta/paletaEscura/alt e e rig.js quem a escreve
    como --p-*. Sem isso o tema escuro precisaria de um segundo desenho e o
    teste de contraste teria de varrer SVG em vez de uma tabela."""
    for f in sorted((RAIZ / "motor/js/rigs").glob("*.rig.js")):
        txt = f.read_text(encoding="utf-8")
        ini = txt.index("\n  markup:")
        fim = txt.index("\n  origens:")
        achados = re.findall(r"#[0-9a-fA-F]{3,8}\b", txt[ini:fim])
        chk(not achados, f"R16: {f.name} nao tem hex no markup (achados: {achados[:3]})")
        chk("type=\"module\"" not in txt and "fetch(" not in txt,
            f"{f.name} nao usa fetch nem modulo ES (file:// depende disso)")


def arte_dos_rigs(pg):
    """A arte de nenhum personagem pode mudar sem que alguem veja.

    Ate aqui esta guarda comparava os BYTES de *.rig.js contra o main, o que
    diz mais do que ela queria dizer: tirar de um rig um campo que ninguem le
    -- raioOlhar, hitboxes por parte -- nao e mudanca de arte, e mesmo assim
    reprovava. E dizia menos, tambem: um campo trocado de lugar passaria.

    Agora compara as TABELAS que o motor interpreta -- poses, expressoes,
    origens, ancoras, paletas, escala. O markup fica de fora de proposito: um
    desenho alterado salta aos olhos no diff do proprio *.rig.js, e duplica-lo
    aqui so faria a referencia pesar. Ja uma origem empurrada dois pixels
    passa despercebida na revisao e muda todo quadro em que a parte gira --
    e disso ninguem estava olhando."""
    for rid in RIGS:
        d = pg.evaluate("""(id) => {
          var d = Estudio.Rig.definicao(id), r = {};
          ['poses', 'expressoes', 'origens', 'ancoras', 'estados',
           'paleta', 'paletaEscura', 'alt', 'escalaNatural', 'viewBox', 'hitbox']
            .forEach(function (k) { if (d[k] !== undefined) r[k] = d[k]; });
          return r;
        }""", rid)
        # A ordenacao estavel e do Python. JSON.stringify(r, chaves, 1)
        # PARECIA ordenar e na verdade FILTRAVA: o segundo argumento em forma
        # de lista e allowlist de chaves, aplicada em TODOS os niveis -- entao
        # poses, expressoes, origens e paletas saiam como {} e a referencia
        # nao afirmava nada sobre justamente o que dizia proteger.
        referencia(f"rigs/{rid}.json",
                   json.dumps(d, sort_keys=True, ensure_ascii=False, indent=1) + "\n",
                   f"a arte da/do {rid} nao mudou")


def opacidade_de_repouso():
    """A opacidade de um <g> MULTIPLICA com a do elemento dentro dele. Um
    opacity="0" no desenho nunca volta, por mais que a pose peca op:1 -- foi
    assim que a marca do formulario ficou invisivel. A opacidade de repouso
    mora na pose 'neutro'."""
    alvos = list((RAIZ / "motor/js/rigs").glob("*.rig.js"))
    alvos.append(RAIZ / "motor/js/props.js")
    for f in alvos:
        txt = f.read_text(encoding="utf-8")
        ini = txt.find("markup:")
        fim = txt.find("origens:", ini)
        zerados = re.findall(r'opacity="0(?:\.0+)?"', txt[ini:fim] if fim > ini else txt)
        chk(not zerados, f'{f.name} nao usa opacity="0" no markup (use a pose neutro)')


def links_do_estudio():
    """Todo caminho relativo que as paginas do estudio escrevem resolve para
    arquivo que existe.

    tools/test-links.py cobre so a pagina-ponte, entao nada olhava para ca. O
    caso que mais importa nao esta no HTML: player.js monta o href do selo de
    citacao como '../docs/<guardiao>.html', em codigo. Esse caminho e relativo
    a pasta da PAGINA, entao o dia em que o player mudar de pasta ele quebra em
    silencio -- o selo continua na tela, clicavel, levando a lugar nenhum."""
    paginas = sorted(RAIZ.glob("paginas/*.html"))
    assert paginas, "nenhuma pagina de estudio encontrada"
    quebrados = []
    for pag in paginas:
        alvos = re.findall(r'(?:href|src)="([^"]+)"', pag.read_text(encoding="utf-8"))
        for a in alvos:
            if a.startswith(("http:", "https:", "data:", "#", "mailto:")):
                continue
            destino = (pag.parent / a.split("?")[0].split("#")[0]).resolve()
            if not destino.exists():
                quebrados.append(f"{pag.relative_to(RAIZ)} -> {a}")
    chk(not quebrados, f"todo link das paginas do estudio existe ({quebrados[:3]})")

    # O selo de citacao leva a pagina do guardiao, que NAO e desta suite: a lei
    # e de quem a publica. O prefixo virou opcao da pagina, entao o que vale
    # conferir mudou junto -- nao ha mais caminho relativo fixo para resolver.
    conf = json_de_js_local(RAIZ / "suite.conf.js")
    base = conf.get("baseGuardiao", "")
    chk(bool(base), "suite.conf.js declara de onde vem a pagina de cada guardiao")
    chk(base.endswith("/"),
        f"o prefixo do selo termina em barra, senao concatena errado ({base!r})")
    js = (RAIZ / "motor/js/player.js").read_text(encoding="utf-8")
    chk("opc.baseGuardiao" in js,
        "player.js le o prefixo por opcao, em vez de fixar o layout de um consumidor")
    chk("else el.selo.removeAttribute('href')" in js,
        "sem prefixo declarado, o selo fica SEM link -- nunca com link quebrado")


def json_de_js_local(caminho):
    """O teste le suite.conf.js pelo mesmo truque do navegador, sem importar o
    pacote: fiscal que depende do codigo fiscalizado fiscaliza a si mesmo."""
    txt = caminho.read_text(encoding="utf-8")
    i = txt.index("=\n", txt.index("window.ESTUDIO_"))
    return json.loads(txt[i + 2:].rstrip().rstrip(";").strip())


def personagens_e_rigs(nav):
    """A folha de personagens: os seis rigs montados, R1, o nucleo minimo de
    poses, o AABB, as duas paletas e o raio-X. E a pagina onde a arte e
    revisada, entao e aqui que a referencia de arte tambem e conferida."""
    pg = nav.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    pg.goto(B + "paginas/personagens.html")
    pg.wait_for_timeout(400)

    chk(not erros, f"folha de personagens carrega sem erro de console (veio {erros[:2]})")

    montados = pg.evaluate("window.ESTUDIO_VIVOS ? ESTUDIO_VIVOS.length : 0")
    chk(montados > 0, f"a folha monta rigs de verdade ({montados} montados)")
    chk(set(pg.evaluate("Estudio.Rig.ids()")) == set(RIGS),
        "os seis rigs do roteiro estao registrados")

    arte_dos_rigs(pg)

    # ---- R1: identidade do estado -------------------------------------
    # Varia o snapshot, volta, e compara o DOM byte a byte. Se um campo
    # do estado nao estiver em instantaneo(), o segundo aplicar diverge.
    r1 = pg.evaluate("""() => {
      var falhas = [];
      Estudio.Rig.ids().forEach(function (id) {
        var svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
        document.body.appendChild(svg);
        var r = Estudio.Rig.criar(id, {palco: svg});
        var d = Estudio.Rig.definicao(id);
        var poses = Object.keys(d.poses), exprs = Object.keys(d.expressoes);
        r.pos(300, 500).escala(1.3).espelhar(true)
         .pose(poses[poses.length-1], 0.42)
         .expressao(exprs[exprs.length-1], 0.7);
        var snap = r.instantaneo(), alvo = r.raiz.outerHTML;
        r.pos(0,0).escala(1).espelhar(false).pose(poses[0]).expressao(exprs[0]);
        r.aplicar(snap);
        if (r.raiz.outerHTML !== alvo) falhas.push(id);
        r.destruir(); svg.remove();
      });
      return falhas;
    }""")
    chk(r1 == [], f"R1: aplicar(instantaneo()) reproduz o DOM em todos os rigs (falhou: {r1})")

    # ---- vocabulario e nucleo minimo ----------------------------------
    nucleo = pg.evaluate("""() => {
      var exigidas = ['neutro','apontando','entregando','protegendo','andando'];
      var exprs = ['neutro','preocupado','feliz','surpreso'];
      var f = [];
      ['raposa','coruja','aguia','tartaruga','elefante'].forEach(function (id) {
        var d = Estudio.Rig.definicao(id);
        exigidas.forEach(function (p) { if (!d.poses[p]) f.push(id+'/pose:'+p); });
        exprs.forEach(function (e) { if (!d.expressoes[e]) f.push(id+'/expr:'+e); });
        if (!d.hitbox) f.push(id+'/sem hitbox');
        if (!d.ancoras || !d.ancoras.olhar) f.push(id+'/sem ancora olhar');
      });
      return f;
    }""")
    chk(nucleo == [], f"os cinco guardioes tem o nucleo minimo de poses e expressoes ({nucleo})")

    # Toda pose/expressao so pode citar parte que existe no markup daquele
    # rig: um nome errado seria uma pose que nao faz nada, em silencio.
    orfas = pg.evaluate("""() => {
      var f = [];
      Estudio.Rig.ids().forEach(function (id) {
        var d = Estudio.Rig.definicao(id);
        var tem = {}; (d.markup.match(/data-part="[^"]+"/g)||[]).forEach(function (m) {
          tem[m.slice(11,-1)] = 1; });
        [['poses',d.poses],['expressoes',d.expressoes]].forEach(function (par) {
          Object.keys(par[1]).forEach(function (k) {
            Object.keys(par[1][k]).forEach(function (parte) {
              if (!tem[parte]) f.push(id+'/'+par[0]+'/'+k+'/'+parte);
            });
          });
        });
        Object.keys(d.origens||{}).forEach(function (p) { if (!tem[p]) f.push(id+'/origens/'+p); });
      });
      return f;
    }""")
    chk(orfas == [], f"nenhuma pose, expressao ou origem cita parte inexistente ({orfas[:4]})")

    # ---- AABB puro: a fisica dos jogos nao consulta layout -------------
    cx = pg.evaluate("""() => {
      var svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
      document.body.appendChild(svg);
      var r = Estudio.Rig.criar('raposa', {palco: svg});
      r.pos(400, 600).escala(2);
      var c = r.caixa();
      var dentro = r.contem(c.x + c.w/2, c.y + c.h/2);
      var fora = r.contem(c.x - 40, c.y - 40);
      r.destruir(); svg.remove();
      return {dentro: dentro, fora: fora, w: c.w};
    }""")
    chk(cx["dentro"] and not cx["fora"], "contem() responde pelo AABB escalado")
    chk(abs(cx["w"] - 140 * 0.88 * 2) < 0.01, f"caixa() acompanha escala e escalaNatural (w={cx['w']})")

    # ---- tema: o personagem existe nos dois ----------------------------
    pg.click("#btTema")
    pg.wait_for_timeout(300)
    chk(pg.evaluate("document.documentElement.getAttribute('data-theme')") == "dark",
        "botao de tema troca o tema da pagina")
    trocou = pg.evaluate("""() => ESTUDIO_VIVOS.every(function (r) {
        return r.raiz.style.getPropertyValue('--p-base') !== ''; })""")
    chk(trocou, "todo rig montado recebe paleta no tema escuro")

    # ---- raio-X (R18) --------------------------------------------------
    pg.click("#btXray")
    pg.wait_for_timeout(300)
    chk(pg.eval_on_selector_all(".est-xray-origem", "e=>e.length") > 0,
        "raio-X desenha o ponto de origem de cada parte")
    chk(pg.eval_on_selector_all(".est-xray-hit", "e=>e.length") > 0,
        "raio-X desenha a hitbox")


def filme_e_transporte(nav):
    """O interpretador e o player: pureza de renderizar(t), elenco por plano,
    legendas, as referencias de palco dos 12 posters, o laco, o teclado, a
    acessibilidade e o modo quadrinhos.

    Devolve a pagina do filme 01 porque a checagem de camera neutra da
    Fase 5 compara os DOIS filmes lado a lado -- a unica costura entre
    grupos, e explicita por isso."""
    # ---- Fase 2: o interpretador do roteiro ----------------------------
    pgf = nav.new_page()
    ef = []
    pgf.on("pageerror", lambda e: ef.append(str(e)))
    pgf.on("console", lambda m: ef.append(m.text) if m.type == "error" else None)
    pgf.goto(B + "paginas/player.html?filme=jornada-dado")
    pgf.wait_for_timeout(500)
    chk(not ef, f"player carrega sem erro de console (veio {ef[:2]})")
    chk(pgf.evaluate("ESTUDIO_PLAYER.filme.duracao") == 124, "o filme dura 124s")
    chk(pgf.evaluate("ESTUDIO_PLAYER.filme.planos.length") == 12, "o filme tem 12 planos")

    # Pureza de renderizar(t): mesma propriedade que a busca da Fase 3 assume.
    puro = pgf.evaluate("""() => {
      var f = ESTUDIO_PLAYER.filme, falhas = [];
      [8.4, 37.0, 61.5, 92.2, 118.0].forEach(function (t) {
        f.renderizar(t);
        var alvo = f.palco.svg.outerHTML;
        f.renderizar(0); f.renderizar(124); f.renderizar(t);
        if (f.palco.svg.outerHTML !== alvo) falhas.push(t);
      });
      return falhas;
    }""")
    chk(puro == [], f"renderizar(t) e puro: saltar da o mesmo DOM que percorrer ({puro})")

    # Avancar em passos pequenos e saltar direto tem de coincidir.
    igual = pgf.evaluate("""() => {
      var f = ESTUDIO_PLAYER.filme;
      f.renderizar(70); var direto = f.palco.svg.outerHTML;
      f.renderizar(0);
      for (var t = 0; t <= 70; t += 0.25) f.renderizar(t);
      f.renderizar(70);
      return f.palco.svg.outerHTML === direto;
    }""")
    chk(igual, "percorrer ate t e saltar para t produzem o mesmo DOM")

    # 'entra' e o elenco DO PLANO: quem nao entrou nao aparece.
    vazam = pgf.evaluate("""() => {
      var f = ESTUDIO_PLAYER.filme, fora = [];
      f.planos.forEach(function (P, k) {
        var dados = f.dados.planos[k], elenco = Object.keys(dados.entra || {});
        Object.keys(f.alvos).forEach(function (a) {
          var s = f.snapshotDe(a, P.poster);
          if (elenco.indexOf(a) < 0 && s.op > 0.001) fora.push(P.id + '/' + a);
        });
      });
      return fora;
    }""")
    chk(vazam == [], f"nenhum alvo aparece num plano em que nao entrou ({vazam[:4]})")

    # A legenda ativa em t e a que o roteiro declara, e so uma.
    leg = pgf.evaluate("""() => {
      var f = ESTUDIO_PLAYER.filme, ruins = [];
      f.legendas.forEach(function (L) {
        var meio = (L.t + L.ate) / 2;
        if (f.legendaEm(meio) !== L) ruins.push(L.plano + '@' + meio.toFixed(1));
        var n = f.legendas.filter(function (x) { return meio >= x.t && meio < x.ate; }).length;
        if (n !== 1) ruins.push('sobreposicao em ' + meio.toFixed(1));
      });
      return ruins;
    }""")
    chk(leg == [], f"cada instante tem no maximo uma legenda, e e a declarada ({leg[:3]})")

    # ---- G4: instantaneo de DOM do palco, plano a plano -----------------
    # O estudio nao tinha cobertura nenhuma de aparencia. O defeito da
    # Fase 5 -- a camera vazando de um plano para o seguinte, deixando 10
    # dos 12 enquadrados errado -- passou por TODOS os testes porque todos
    # comparam o filme com ele mesmo. Uma referencia externa e o unico
    # jeito de uma regressao assim ter onde bater.
    for P in pgf.evaluate("ESTUDIO_PLAYER.filme.planos.map(p=>({id:p.id,poster:p.poster}))"):
        referencia(f"filmes/jornada-dado/baseline/jornada-dado-{P['id']}.txt",
                   instantaneo_do_palco(pgf, P["poster"]),
                   f"jornada-dado/{P['id']}: o palco no poster bate com a referencia")
    # A pureza, agora contra uma referencia EXTERNA: chegar ao poster
    # voltando do fim tem de dar o mesmo palco que ir direto.
    pgf.evaluate("ESTUDIO_PLAYER.irPara(ESTUDIO_PLAYER.filme.duracao)")
    pos = pgf.evaluate("ESTUDIO_PLAYER.filme.planos[3].poster")
    referencia("filmes/jornada-dado/baseline/jornada-dado-p04.txt", instantaneo_do_palco(pgf, pos),
               "jornada-dado/p04: chegar de tras da o mesmo palco")


    chk(pgf.eval_on_selector_all("#transcricao li", "e=>e.length") == 30,
        "a transcricao mostra as 30 falas do roteiro")

    # ---- Fase 3: o relogio e o transporte ------------------------------
    # Nenhum caso de tempo usa relogio de parede: avancar(dt) e _quadro(ts)
    # conduzem o tempo com floats exatos. Teste de animacao que espera o
    # relogio real e teste que falha por acaso -- e teste que falha por
    # acaso acaba ignorado.
    deriva = pgf.evaluate("""() => {
      var p = ESTUDIO_PLAYER; p.irPara(0);
      for (var i = 0; i < 400; i++) p.avancar(0.1);
      return p.t();
    }""")
    chk(abs(deriva - 40) < 1e-6, f"400 avancos de 0,1s chegam a 40s sem deriva ({deriva})")

    travado = pgf.evaluate("""() => {
      var p = ESTUDIO_PLAYER; p.irPara(0);
      p._quadro(1000); var a = p.t(); p._quadro(400000);  /* aba escondida 400s */
      return p.t() - a;
    }""")
    chk(abs(travado - 0.25) < 1e-9,
        f"delta preso: um salto de 400s avanca no maximo 0,25s (veio {travado})")

    # taxa() saiu com o G8: nenhuma interface a expunha. O que ela
    # provava -- que o acumulo por quadro e exato -- continua provado aqui,
    # e sem um metodo de motor que so o teste usava.
    exata = pgf.evaluate("""() => {
      var p = ESTUDIO_PLAYER; p.irPara(0);
      for (var i = 0; i < 60; i++) p.avancar(1/60);
      return p.t();
    }""")
    chk(abs(exata - 1) < 1e-9, f"60 quadros de 1/60 s caem exatamente em 1 s ({exata})")

    # A verificacao mais valiosa: a PAGINA INTEIRA, nao so o palco. Cobre
    # legenda, selo, regua, transporte e titulo de uma vez.
    pagina = pgf.evaluate("""() => {
      var p = ESTUDIO_PLAYER;
      p.irPara(0);
      for (var t = 0; t <= 60; t += 1/60) p.avancar(1/60);
      p.irPara(60); var percorrido = document.querySelector('.est-wrap').outerHTML;
      p.irPara(0); p.irPara(60);
      var saltado = document.querySelector('.est-wrap').outerHTML;
      p.irPara(110); p.irPara(60);
      var voltado = document.querySelector('.est-wrap').outerHTML;
      return {frente: percorrido === saltado, tras: voltado === saltado};
    }""")
    chk(pagina["frente"], "percorrer ate t e saltar para t dao a mesma PAGINA")
    chk(pagina["tras"], "voltar de 110s para 60s da a mesma pagina que chegar direto")

    chk(pgf.evaluate("typeof ESTUDIO_PLAYER.filme.eventosAte") == "undefined",
        "R4: eventosAte() foi removido junto com o canal de eventos")

    # O selo e funcao de t: chegar por qualquer lado da o mesmo resultado.
    selos = pgf.evaluate("""() => {
      var p = ESTUDIO_PLAYER, f = p.filme, ruins = [];
      f.citacoes.forEach(function (c) {
        var meio = (c.t + c.ate) / 2;
        p.irPara(0); p.irPara(meio); var indo = document.getElementById('selo').textContent;
        p.irPara(f.duracao); p.irPara(meio);
        if (document.getElementById('selo').textContent !== indo) ruins.push(c.plano + ' texto');
        if (f.citacaoEm(meio).guardiao !== c.guardiao) ruins.push(c.plano + ' guardiao');
      });
      p.irPara(0);
      return ruins;
    }""")
    chk(selos == [], f"o selo de citacao e funcao pura de t, nos dois sentidos ({selos[:3]})")

    # Fim do filme: para sozinho e nao passa.
    fim = pgf.evaluate("""() => {
      var p = ESTUDIO_PLAYER; p.irPara(123.8); p.avancar(1);
      return {t: p.t(), tocando: p.tocando(), raf: p._raf()};
    }""")
    chk(abs(fim["t"] - 124) < 1e-9 and not fim["tocando"] and fim["raf"] is None,
        f"o filme para sozinho no fim e nao passa de 124s ({fim})")

    # Pausar nao anda -- aqui a espera real e o ponto: asserir AUSENCIA de
    # movimento e a unica coisa que um relogio falso nao mostra.
    pgf.evaluate("ESTUDIO_PLAYER.irPara(30); ESTUDIO_PLAYER.tocar()")
    pgf.wait_for_timeout(250)
    andou = pgf.evaluate("ESTUDIO_PLAYER.t()") > 30
    pgf.evaluate("ESTUDIO_PLAYER.pausar()")
    parado_em = pgf.evaluate("ESTUDIO_PLAYER.t()")
    pgf.wait_for_timeout(300)
    chk(andou, "tocar() faz o tempo andar de verdade")
    chk(pgf.evaluate("ESTUDIO_PLAYER.t()") == parado_em, "pausado, o tempo nao anda")
    chk(pgf.evaluate("ESTUDIO_PLAYER._raf()") is None, "pausado, nenhum rAF fica agendado")

    # Retomar depois de uma pausa longa nao engole o tempo parado.
    retomada = pgf.evaluate("""() => {
      var p = ESTUDIO_PLAYER; p.irPara(10); p.pausar();
      var a = p.t(); p.tocar(); p._quadro(999999); var d = p.t() - a; p.pausar();
      return d;
    }""")
    chk(abs(retomada) < 1e-9, f"o 1o quadro depois de retomar consome delta zero ({retomada})")

    # Teclado, com semantica nova e exata.
    tec = pgf.evaluate("ESTUDIO_PLAYER.irPara(50); ESTUDIO_PLAYER.t()")
    pgf.keyboard.press("ArrowRight")
    chk(abs(pgf.evaluate("ESTUDIO_PLAYER.t()") - 55) < 1e-9, "seta direita anda exatamente 5s")
    pgf.keyboard.press("l")
    chk(abs(pgf.evaluate("ESTUDIO_PLAYER.t()") - 65) < 1e-9, "L anda exatamente 10s")
    i0 = pgf.evaluate("ESTUDIO_PLAYER.indice()")
    pgf.keyboard.press("]")
    chk(pgf.evaluate("ESTUDIO_PLAYER.indice()") == i0 + 1, "] avanca exatamente um plano")
    chk(abs(pgf.evaluate("ESTUDIO_PLAYER.t() - ESTUDIO_PLAYER.filme.planos[ESTUDIO_PLAYER.indice()].inicio")) < 1e-9,
        "] cai no INICIO do plano, nao perto dele")
    pgf.keyboard.press("End")
    chk(pgf.evaluate("ESTUDIO_PLAYER.indice()") == 11, "End vai para o ultimo plano")
    pgf.keyboard.press("Home")
    chk(pgf.evaluate("ESTUDIO_PLAYER.t()") == 0, "Home volta para o comeco")

    # Legendas: o botao esconde a faixa, a transcricao permanece.
    pgf.keyboard.press("c")
    chk(pgf.eval_on_selector("#legenda", "e=>e.hidden"), "C esconde a legenda na tela")
    chk(pgf.eval_on_selector_all("#transcricao li", "e=>e.length") == 30,
        "a transcricao continua com as 30 falas")
    pgf.keyboard.press("c")

    # Acessibilidade: a legenda NAO e regiao ao vivo (polite enfileira em
    # vez de substituir, e 30 trocas viram uma fila dessincronizada).
    chk(pgf.eval_on_selector("#legenda", "e=>!e.hasAttribute('aria-live') && !e.hasAttribute('role')"),
        "a legenda nao e regiao ao vivo, de proposito")
    chk(pgf.eval_on_selector("#status", "e=>e.getAttribute('role')") == "status",
        "existe uma regiao de estado para acao do usuario")

    # E o laco NUNCA escreve nela.
    mut = pgf.evaluate("""() => new Promise(function (ok) {
      var p = ESTUDIO_PLAYER, n = 0;
      var mo = new MutationObserver(function (m) { n += m.length; });
      mo.observe(document.getElementById('status'), {childList:true, characterData:true, subtree:true});
      p.irPara(20);
      for (var i = 0; i < 120; i++) p.avancar(1/60);
      setTimeout(function () { mo.disconnect(); ok(n); }, 30);
    })""")
    chk(mut == 0, f"120 quadros sem acao do usuario nao anunciam nada ({mut} mutacoes)")

    # Orcamento de quadro, com o cache aquecido: mede regime, nao o salto.
    perf = pgf.evaluate("""() => {
      var p = ESTUDIO_PLAYER, f = p.filme, pior = 0, onde = 0;
      function w(){var s=0;Object.keys(f.rigs).forEach(function(k){s+=f.rigs[k]._escritas;});return s;}
      for (var t = 0; t < f.duracao; t += 0.5) {
        p.irPara(t); var a = w(); p.avancar(1/60); var b = w();
        if (b - a > pior) { pior = b - a; onde = t; }
      }
      p.irPara(0);
      return {pior: pior, onde: onde};
    }""")
    chk(perf["pior"] <= 40,
        f"no maximo 40 escritas de atributo por quadro (pior: {perf['pior']} em t={perf['onde']}s)")

    # Modo quadrinhos: t sobrevive, nenhum rAF roda, e a legenda do plano
    # vem INTEIRA -- quem pede movimento reduzido nao recebe menos filme.
    quad = pgf.evaluate(r"""() => {
      var p = ESTUDIO_PLAYER, f = p.filme; p.irPara(37); var antes = p.t();
      document.getElementById('btModo').click();
      var emQuadrinhos = p.modo(), raf = p._raf();
      var linhas = document.getElementById('legenda').textContent.split('\n').length;
      var temSelo = !document.getElementById('selo').hidden;
      var planoEmQuadrinhos = p.indice();
      document.getElementById('btModo').click();
      return {modo: emQuadrinhos, raf: raf, linhas: linhas, selo: temSelo, voltou: p.modo(),
              planoAntes: f.planoIndice(antes), planoDepois: p.indice(),
              planoQuadrinhos: planoEmQuadrinhos};
    }""")
    chk(quad["modo"] == "quadrinhos" and quad["voltou"] == "movimento",
        "S alterna entre movimento e quadrinhos")
    chk(quad["raf"] is None, "em quadrinhos nenhum rAF fica agendado")
    chk(quad["linhas"] > 1, f"em quadrinhos a legenda do plano vem inteira ({quad['linhas']} linhas)")
    chk(quad["selo"], "em quadrinhos o selo do plano aparece, mesmo fora do instante do poster")
    chk(quad["planoAntes"] == quad["planoQuadrinhos"] == quad["planoDepois"],
        f"o PLANO sobrevive a troca de modo nos dois sentidos ({quad['planoAntes']} -> "
        f"{quad['planoQuadrinhos']} -> {quad['planoDepois']})")

    return pgf


def segundo_filme(nav, pgf):
    """A folha de contato e o filme 02: o motor e agnostico de filme, e a
    camera volta ao neutro em todo corte, nos dois."""
    # A folha de contato: os 12 quadros, o portao da Fase 2.
    pgc = nav.new_page()
    ec = []
    pgc.on("pageerror", lambda e: ec.append(str(e)))
    pgc.goto(B + "paginas/folha-de-contato.html?filme=jornada-dado")
    pgc.wait_for_timeout(900)
    chk(not ec, f"folha de contato carrega sem erro (veio {ec[:2]})")
    chk(pgc.eval_on_selector_all(".est-quadro", "e=>e.length") == 12,
        "a folha de contato mostra os 12 planos")

    # ---- Fase 5: o motor e agnostico de filme --------------------------
    # O segundo filme existe para provar o template. Se qualquer coisa aqui
    # falhar, o motor estava amarrado ao filme 01 e ninguem tinha visto.
    pg2f = nav.new_page()
    e2f = []
    pg2f.on("pageerror", lambda e: e2f.append(str(e)))
    pg2f.on("console", lambda m: e2f.append(m.text) if m.type == "error" else None)
    pg2f.goto(B + "paginas/player.html?filme=legitimo-interesse")
    pg2f.wait_for_timeout(500)
    chk(not e2f, f"o segundo filme carrega sem erro ({e2f[:2]})")
    chk(pg2f.evaluate("ESTUDIO_PLAYER.filme.id") == "legitimo-interesse",
        "?filme= escolhe qual roteiro tocar")
    chk(pg2f.evaluate("ESTUDIO_PLAYER.filme.duracao") == 42, "o segundo filme dura 42s")
    chk(pg2f.evaluate("ESTUDIO_PLAYER.filme.planos.length") == 5, "o segundo filme tem 5 planos")

    puro2 = pg2f.evaluate("""() => {
      var p = ESTUDIO_PLAYER, falhas = [];
      [4.5, 13, 22, 31, 40].forEach(function (t) {
        p.irPara(0); p.irPara(t); var indo = document.querySelector('.est-wrap').outerHTML;
        p.irPara(42); p.irPara(t);
        if (document.querySelector('.est-wrap').outerHTML !== indo) falhas.push(t);
      });
      return falhas;
    }""")
    chk(puro2 == [], f"pureza vale no segundo filme, nos dois sentidos ({puro2})")

    vaza2 = pg2f.evaluate("""() => {
      var f = ESTUDIO_PLAYER.filme, fora = [];
      f.planos.forEach(function (P, k) {
        var elenco = Object.keys(f.dados.planos[k].entra || {});
        Object.keys(f.alvos).forEach(function (a) {
          if (elenco.indexOf(a) < 0 && f.snapshotDe(a, P.poster).op > 0.001) fora.push(P.id + '/' + a);
        });
      });
      return fora;
    }""")
    chk(vaza2 == [], f"elenco por plano vale no segundo filme ({vaza2[:3]})")

    for P in pg2f.evaluate("ESTUDIO_PLAYER.filme.planos.map(p=>({id:p.id,poster:p.poster}))"):
        referencia(f"filmes/legitimo-interesse/baseline/legitimo-interesse-{P['id']}.txt",
                   instantaneo_do_palco(pg2f, P["poster"]),
                   f"legitimo-interesse/{P['id']}: o palco no poster bate com a referencia")


    # Os cinco recursos que o filme 01 nunca exercitou.
    novos = pg2f.evaluate("""() => {
      var p = ESTUDIO_PLAYER, f = p.filme, r = {};
      /* pose 'andando': a Tartaruga entra andando em p02 */
      p.irPara(7.5);
      r.andando = f.snapshotDe('op', 7.5).pose.nome === 'andando';
      /* acao 'estado': dois dados apagam em p03 */
      p.irPara(23);
      r.estado = f.snapshotDe('dado2', 23).estado === 'apagado' &&
                 f.snapshotDe('dado', 23).estado === 'normal';
      /* tres instancias do mesmo rig, com DOM proprio cada uma */
      r.instancias = f.rigs.dado && f.rigs.dado2 && f.rigs.dado3 &&
                     f.rigs.dado.raiz !== f.rigs.dado2.raiz &&
                     f.rigs.dado2.raiz.getAttribute('opacity') !==
                     f.rigs.dado.raiz.getAttribute('opacity');
      /* evento 'marco' vira selo, como 'citar' */
      p.irPara(40);
      r.marco = !!f.citacaoEm(40) && f.citacaoEm(40).artigo === 38;
      /* camera AFASTANDO: zoom menor que 1 */
      var g = f.palco.svg.querySelector('[data-camera]').getAttribute('transform');
      r.zoomFora = parseFloat(/scale\(([\d.]+)\)/.exec(g)[1]) < 1;
      p.irPara(0);
      return r;
    }""")
    for chave, rotulo in [("andando", "a pose 'andando' funciona (nunca usada no filme 01)"),
                          ("estado", "a acao 'estado' apaga so quem devia"),
                          ("instancias", "tres instancias do mesmo rig, com DOM independente"),
                          ("marco", "o evento 'marco' vira selo como 'citar'"),
                          ("zoomFora", "a camera afasta (zoom < 1)")]:
        chk(novos[chave], rotulo)

    # A camera volta ao neutro em todo corte, nos DOIS filmes: sem isto um
    # zoom vazava para a frente e nao voltava mais.
    for pagina, quantos, nome in ((pgf, 12, "jornada-dado"), (pg2f, 5, "legitimo-interesse")):
        zooms = pagina.evaluate("""() => {
          var f = ESTUDIO_PLAYER.filme, fora = [];
          f.planos.forEach(function (P) {
            ESTUDIO_PLAYER.irPara(P.inicio + 0.02);
            var g = f.palco.svg.querySelector('[data-camera]').getAttribute('transform');
            var z = parseFloat((/scale\(([\d.]+)\)/.exec(g) || [0, 1])[1]);
            if (Math.abs(z - 1) > 0.02) fora.push(P.id + '=' + z);
          });
          ESTUDIO_PLAYER.irPara(0);
          return fora;
        }""")
        chk(zooms == [], f"{nome}: todo plano comeca com a camera neutra ({zooms[:3]})")

    pg2f.keyboard.press("]")
    chk(pg2f.evaluate("ESTUDIO_PLAYER.indice()") == 1,
        "o teclado funciona igual no segundo filme")
    pg2f.evaluate("document.getElementById('btModo').click()")
    pg2f.wait_for_timeout(200)
    chk(pg2f.evaluate("ESTUDIO_PLAYER.modo()") == "quadrinhos",
        "o modo quadrinhos funciona igual no segundo filme")

    # ---- movimento reduzido: nasce em quadrinhos -----------------------
    ctx = nav.new_context(reduced_motion="reduce")
    pgr = ctx.new_page()
    er = []
    pgr.on("pageerror", lambda e: er.append(str(e)))
    pgr.goto(B + "paginas/player.html?filme=jornada-dado")
    pgr.wait_for_timeout(500)
    chk(not er, f"player carrega em movimento reduzido sem erro ({er[:2]})")
    chk(pgr.evaluate("ESTUDIO_PLAYER.modo()") == "quadrinhos",
        "com movimento reduzido, o player NASCE em quadrinhos")
    chk(pgr.evaluate("ESTUDIO_PLAYER._raf()") is None,
        "em movimento reduzido nenhum rAF chega a ser agendado")
    chk("movimento" in pgr.eval_on_selector("#btPlay", "e=>e.textContent"),
        "o botao principal oferece ligar o movimento explicitamente")
    chk(pgr.eval_on_selector_all("#transcricao li", "e=>e.length") == 30,
        "a transcricao completa esta disponivel em movimento reduzido")
    ctx.close()


def injecao_de_falha(nav):
    """G1 e G2: todo caminho de erro do motor dispara com a mensagem certa, e o
    que antes caia num padrao em silencio agora lanca."""
    # ---- G1: injecao de falha -- todo erro() tem de disparar ------------
    # A suite cobria muito bem o caminho feliz de dados validos e nada
    # alem dele: 28 caminhos de erro, nenhum teste negativo. Cada erro()
    # e uma promessa ao analista que edita o roteiro sob file:// -- e
    # promessa que nunca foi cobrada nao e promessa.
    #
    # Um roteiro minimo valido, mutado UMA vez por caso: assim a unica
    # diferenca entre passar e falhar e a mutacao, e nao o roteiro.
    pgn = nav.new_page()
    pgn.goto(B + "paginas/player.html?filme=jornada-dado")
    pgn.wait_for_timeout(400)
    pgn.evaluate("""() => {
      window.__BASE = {
        id: '__prova', titulo: 'Prova', duracao: 4,
        elenco: { ana: { rig: 'raposa' } },
        props:  { dado: { rig: 'dado' } },
        planos: [{
          id: 'p01', titulo: 'Um', dur: 4, cenario: 'balcao', poster: 2, arts: [18],
          entra: { ana: { x: 400, y: 620, escala: 1, pose: 'neutro', expressao: 'neutro' } },
          acoes: [{ em: 1, dur: 1, alvo: 'ana', para: { x: 500 }, ease: 'suave' }],
          legendas: [{ em: 0.2, ate: 3.5, txt: 'Uma legenda.' }]
        }]
      };
      window.__provar = function (mutar) {
        var d = JSON.parse(JSON.stringify(window.__BASE));
        if (mutar) mutar(d);
        var caixa = document.createElement('div');
        document.body.appendChild(caixa);
        window.ESTUDIO_FILMES.__prova = d;
        try { Estudio.Filme.carregar('__prova', { palco: Estudio.Palco.criar(caixa) }); return ''; }
        catch (e) { return String(e.message); }
        finally { caixa.remove(); delete window.ESTUDIO_FILMES.__prova; }
      };
    }""")

    # O roteiro-base tem de CARREGAR. Sem isto, todo caso abaixo passaria
    # por acidente, acusando a mutacao quando o erro era do proprio base.
    chk(pgn.evaluate("__provar(null)") == "",
        f"o roteiro-base da injecao e valido ({pgn.evaluate('__provar(null)')!r})")

    CASOS = [
        ("d => { delete d.planos[0].id; }", "sem id ou dur", "plano sem id"),
        ("d => { delete d.planos[0].dur; }", "sem id ou dur", "plano sem dur"),
        ("d => { d.planos[0].cenario = 'nenhum'; }", 'cenário "nenhum"', "cenario inexistente"),
        ("d => { d.planos[0].entra.zzz = { x: 1 }; }", "não está no elenco", "entra com alvo fora do elenco"),
        ("d => { d.planos[0].entra.ana.cor = 'azul'; }", 'propriedade "cor" desconhecida', "entra com propriedade desconhecida"),
        ("d => { d.planos[0].acoes[0].alvo = 'zzz'; }", "fora do elenco", "acao com alvo fora do elenco"),
        ("d => { delete d.planos[0].acoes[0].em; }", 'ação sem "em"', "acao sem em"),
        ("d => { d.planos[0].acoes[0].em = 3.8; d.planos[0].acoes[0].dur = 1; }", "passa da duração", "acao que passa da duracao"),
        ("d => { d.planos[0].acoes[0] = { em: 1, alvo: 'ana' }; }", "sem verbo", "acao sem verbo"),
        ("d => { d.planos[0].acoes[0].para = { cor: 1 }; }", "não é animável", "propriedade nao animavel"),
        ("d => { d.planos[0].acoes[0].ease = 'turbo'; }", "fora da tabela", "ease fora da tabela"),
        ("d => { d.planos[0].acoes[0].evento = 'piscar'; d.planos[0].acoes[0].dados = { artigo: 18, guardiao: 'aguia' }; }",
         "fora dos três", "evento fora dos tres"),
        ("d => { d.planos[0].acoes[0].evento = 'citar'; }", "dados.artigo", "evento sem dados"),
        ("d => { delete d.planos[0].legendas[0].ate; }", "legenda sem em/ate", "legenda sem em/ate"),
        ("d => { d.duracao = 99; }", "duração declarada", "duracao declarada diferente da soma"),
        ("d => { d.elenco.ana.rig = 'girafa'; }", 'rig "girafa"', "rig inexistente"),
        ("d => { d.elenco.ana.camada = 'nuvem'; }", 'camada "nuvem"', "camada inexistente"),
        ("d => { d.planos[0].entra.ana.pose = 'voando'; }", "não tem a pose", "pose que o rig nao tem"),
        ("d => { d.planos[0].entra.ana.expressao = 'furioso'; }", "não tem a expressão", "expressao que o rig nao tem"),
    ]
    for mut, trecho, rotulo in CASOS:
        msg = pgn.evaluate(f"__provar({mut})")
        chk(trecho in msg, f"roteiro invalido e recusado: {rotulo} ({msg[:70]!r})")

    # Os erros que nao passam por carregar() um roteiro.
    SOLTOS = [
        ("Estudio.Filme.carregar('nao-existe')", "não foi carregado", "filme nao carregado"),
        ("Estudio.Rig.criar('girafa')", "não registrado", "personagem nao registrado"),
        ("Estudio.Rig.criar('raposa').pose('voando')", 'pose "voando"', "Rig.pose inexistente"),
        ("Estudio.Rig.criar('raposa').expressao('furioso')", 'expressão "furioso"', "Rig.expressao inexistente"),
        ("(function(){var r=Estudio.Rig.criar('raposa'),s=r.instantaneo();"
         "s.pose={nome:'voando',mistura:1,anterior:'neutro'};return r.aplicar(s);})()",
         'pose "voando"', "aplicar() com pose inexistente"),
        ("(function(){var r=Estudio.Rig.criar('raposa'),s=r.instantaneo();"
         "s.estado='derretido';return r.aplicar(s);})()",
         'estado "derretido"', "aplicar() com estado inexistente"),
        ("Estudio.Palco.criar(document.createElement('div')).cenario('nenhum')",
         'cenário "nenhum"', "Palco.cenario inexistente"),
        ("Estudio.Palco.criar(document.createElement('div')).camera(640, 360, 0)",
         "positivo", "camera com zoom zero"),
        ("Estudio.ease('turbo')", 'easing "turbo"', "ease fora da tabela"),
    ]
    for expr, trecho, rotulo in SOLTOS:
        msg = pgn.evaluate("(() => { try { " + expr + "; return ''; }"
                           " catch (e) { return String(e.message); } })()")
        chk(trecho in msg, f"chamada invalida e recusada: {rotulo} ({msg[:70]!r})")

    # G2: o que NAO deve lancar -- um estado legitimo continua passando.
    chk(pgn.evaluate("(() => { try { var r = Estudio.Rig.criar('raposa'), s = r.instantaneo();"
                     " s.estado = 'apagado'; r.aplicar(s); return 'passou'; }"
                     " catch (e) { return String(e.message); } })()") == "passou",
        "um estado declarado continua passando (a guarda nao e cega)")

    # G2: o que aceita errado sem reclamar. Pior que um erro e um
    # resultado plausivel -- estes quatro nao viram excecao, viram
    # comportamento FIXADO por teste.
    # Dois keyframes no mesmo instante resolvem pelo ULTIMO -- e a busca
    # binaria devolve sempre o ultimo empate, o que torna o ramo defensivo
    # 'b.t <= a.t' de filme.js inalcancavel ENQUANTO as trilhas estiverem
    # ordenadas. Entao o que vale a pena afirmar e a ordenacao, que e a
    # invariante de que aquele ramo depende e que nada conferia.
    chk(pgn.evaluate("""(() => {
      var f = ESTUDIO_PLAYER.filme;
      f.trilhas['__deg|x'] = [{t:0,v:10,ease:'degrau'},{t:2,v:20,ease:'suave'},
                              {t:2,v:99,ease:'suave'},{t:4,v:50,ease:'suave'}];
      var r = [f.snapshotDe('__deg', 1).x, f.snapshotDe('__deg', 2).x];
      delete f.trilhas['__deg|x'];
      return r;
    })()""") == [15, 99],
        "keyframes no mesmo instante resolvem pelo ultimo")

    # A pagina traz UM filme; os outros chegam pelo carregador -- que assim
    # e exercitado fora do caminho da propria pagina.
    pgn.evaluate("(ids) => Promise.all(ids.map(function (i) "
                 "{ return Estudio.carregarFilme(i, '../'); }))",
                 ["jornada-dado", "legitimo-interesse"])
    desordem = pgn.evaluate("""() => {
      var fora = [];
      ['jornada-dado', 'legitimo-interesse'].forEach(function (id) {
        var f = Estudio.Filme.carregar(id, {});
        Object.keys(f.trilhas).forEach(function (k) {
          var kfs = f.trilhas[k];
          for (var i = 1; i < kfs.length; i++) {
            if (kfs[i].t < kfs[i - 1].t) fora.push(id + ' ' + k + ' @' + i);
          }
        });
        ['poses', 'exprs', 'estados'].forEach(function (c) {
          Object.keys(f[c]).forEach(function (a) {
            var ks = f[c][a];
            for (var i = 1; i < ks.length; i++) {
              if (ks[i].t < ks[i - 1].t) fora.push(id + ' ' + c + '/' + a + ' @' + i);
            }
          });
        });
      });
      return fora;
    }""")
    chk(desordem == [],
        f"toda trilha achatada sai ordenada no tempo ({desordem[:3]})")

    # Toda parte animada tem origem declarada: sem isso o transform cai
    # num pivo padrao [100,160] em silencio, e a parte gira pelo lugar
    # errado sem nada acusar.
    semorigem = pgn.evaluate("""() => {
      var falta = [];
      Estudio.Rig.ids().forEach(function (id) {
        var d = Estudio.Rig.definicao(id), org = d.origens || {}, vistas = {};
        ['poses', 'expressoes'].forEach(function (c) {
          Object.keys(d[c] || {}).forEach(function (n) {
            Object.keys(d[c][n] || {}).forEach(function (p) { vistas[p] = 1; });
          });
        });
        Object.keys(vistas).forEach(function (p) {
          if (!org[p]) falta.push(id + '/' + p);
        });
      });
      return falta;
    }""")
    chk(semorigem == [], f"toda parte animada tem origem declarada ({semorigem[:4]})")

    # Um guardiao sem definicao de rig cai no id cru, e nao em 'undefined'.
    chk(pgn.evaluate("Estudio.Rig.definicao('inexistente') === undefined") is True,
        "definicao() de rig desconhecido devolve undefined, sem lancar")


def o_jogo(nav):
    """Fase 6: o jogo e dirigido por entrada, e nenhum rig mudou."""
    # ---- Fase 6: o primeiro jogo ---------------------------------------
    # O jogo dirige o rig por ENTRADA, nao por tempo. E o caminho que o
    # filme nunca exercitou -- e o criterio da fase e que nenhum rig mude.
    pgj = nav.new_page()
    ej = []
    pgj.on("pageerror", lambda e: ej.append(str(e)))
    pgj.on("console", lambda m: ej.append(m.text) if m.type == "error" else None)
    pgj.goto(B + "paginas/jogo.html?jogo=sala-do-titular&semente=7")
    pgj.wait_for_timeout(400)
    chk(not ej, f"o jogo carrega sem erro ({ej[:2]})")

    # O conteudo vem da fonte: se a lei mudar no repo, o jogo muda junto.
    direitos = pgj.evaluate("ESTUDIO_JOGO.dados.direitos.map(d=>d.inciso)")
    chk(direitos == ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"],
        f"os nove direitos do Art. 18, na ordem do caput ({direitos})")
    chk(pgj.eval_on_selector_all("#opcoes button", "e=>e.length") == 9,
        "nove opcoes, uma por direito")

    # Uma partida INTEIRA so por teclado, ate a tela de resultado.
    jogada = pgj.evaluate("""() => {
      var j = ESTUDIO_JOGO;
      return {fila: j.fila(),
              incisos: j.dados.direitos.map(function (d) { return d.inciso; })};
    }""")
    for k, inc in enumerate(jogada["fila"]):
        certo = jogada["incisos"].index(inc) + 1
        pgj.keyboard.press(str(certo) if k < 9 else str(1 + (certo % 9)))
        pgj.keyboard.press("Enter")
    placar = pgj.evaluate("ESTUDIO_JOGO.placar()")
    chk(placar["acertos"] == 9 and placar["erros"] == len(jogada["fila"]) - 9,
        f"partida inteira jogada so por teclado ({placar['acertos']}/{len(jogada['fila'])})")
    chk(not pgj.eval_on_selector("#fim", "e=>e.hidden"), "a tela de resultado aparece no fim")
    chk(pgj.evaluate("ESTUDIO_JOGO._raf()") is None,
        "terminado o jogo, nenhum rAF fica agendado")

    # Determinismo por semente.
    sem = pgj.evaluate("ESTUDIO_JOGO.fila()")
    pgj.goto(B + "paginas/jogo.html?jogo=sala-do-titular&semente=7")
    pgj.wait_for_timeout(300)
    igual = pgj.evaluate("ESTUDIO_JOGO.fila()")
    pgj.goto(B + "paginas/jogo.html?jogo=sala-do-titular&semente=99")
    pgj.wait_for_timeout(300)
    outra = pgj.evaluate("ESTUDIO_JOGO.fila()")
    chk(sem == igual, "a mesma semente da a mesma ordem")
    chk(igual != outra, "sementes diferentes dao ordens diferentes")

    # O rig e o MESMO do filme: mesma pose, mesmo DOM.
    mesmo = pgj.evaluate("""() => {
      var j = ESTUDIO_JOGO;
      j.dpo.pose('neutro').expressao('neutro');
      var svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
      document.body.appendChild(svg);
      var solto = Estudio.Rig.criar('raposa', {palco: svg, paleta: 'alt'});
      solto.aplicar(j.dpo.instantaneo());
      var igual = solto.raiz.innerHTML === j.dpo.raiz.innerHTML;
      solto.destruir(); svg.remove();
      return igual;
    }""")
    chk(mesmo, "a Raposa do jogo e a mesma do filme, no mesmo estado")

    # Movimento reduzido: sem cronometro, sem rAF, conteudo inteiro.
    ctxj = nav.new_context(reduced_motion="reduce")
    pgjr = ctxj.new_page()
    pgjr.goto(B + "paginas/jogo.html?jogo=sala-do-titular")
    pgjr.wait_for_timeout(400)
    chk(pgjr.evaluate("ESTUDIO_JOGO.comPrazo()") is False,
        "com movimento reduzido o jogo roda SEM cronometro")
    chk(pgjr.evaluate("ESTUDIO_JOGO._raf()") is None,
        "com movimento reduzido nenhum rAF chega a ser agendado")
    chk(pgjr.eval_on_selector_all("#opcoes button", "e=>e.length") == 9,
        "com movimento reduzido as nove opcoes continuam la")
    chk(pgjr.eval_on_selector("#prazo", "e=>e.hidden"), "a barra de prazo fica oculta")
    ctxj.close()


def jogo_caminhos_esquecidos(nav):
    """G5: prazo esgotado, foco, Enter e uma partida inteira so de mouse."""
    # ---- G5: o jogo pelos caminhos que ninguem andou --------------------
    # O prazo esgotado e o UNICO caminho que o relogio do jogo percorre
    # sozinho, e era o unico que ninguem percorria: os testes acima ou
    # respondem antes do prazo, ou rodam sob movimento reduzido, que
    # desliga o cronometro. Bombeia o LACO de verdade (_quadro), e nao so
    # avancar(): so assim a linha que reagenda o rAF entra no caminho.
    pgp = nav.new_page()
    ep = []
    pgp.on("pageerror", lambda e: ep.append(str(e)))
    pgp.on("console", lambda m: ep.append(m.text) if m.type == "error" else None)
    pgp.goto(B + "paginas/jogo.html?jogo=sala-do-titular&semente=7")
    pgp.wait_for_timeout(400)
    primeiro = pgp.evaluate("ESTUDIO_JOGO.fila()[0]")
    estouro = pgp.evaluate("""(t0) => {
      var q = ESTUDIO_JOGO.relogio._quadro;
      try { for (var i = 0; i <= 56; i++) q(t0 + i * 250); return ""; }
      catch (e) { return String(e && e.message || e); }
    }""", 0)
    chk(estouro == "" and not ep,
        f"o prazo esgotado nao quebra o jogo ({estouro or ep[:1]})")
    pl = pgp.evaluate("ESTUDIO_JOGO.placar()")
    chk(pl["erros"] == 1 and pl["acertos"] == 0,
        f"prazo esgotado conta como erro, nao como acerto ({pl})")
    fb = pgp.eval_on_selector("#feedback", "e=>e.textContent")
    chk(("Art. 18, " + primeiro) in fb,
        f"prazo esgotado mostra qual era o direito certo ({fb[:60]!r})")
    chk("empo" in pgp.eval_on_selector("#status", "e=>e.textContent"),
        "prazo esgotado e anunciado para quem le a tela")
    # A prova de que o laco sobreviveu: um SEGUNDO prazo tambem estoura.
    # Com o defeito, a excecao subia de dentro de quadro() e a linha que
    # reagenda o rAF nunca rodava -- o cronometro morria de vez.
    pgp.keyboard.press("Enter")
    segundo = pgp.evaluate("""(t0) => {
      var q = ESTUDIO_JOGO.relogio._quadro;
      try { for (var i = 0; i <= 56; i++) q(t0 + i * 250); return ""; }
      catch (e) { return String(e && e.message || e); }
    }""", 20000)
    pl2 = pgp.evaluate("ESTUDIO_JOGO.placar()")
    chk(segundo == "" and pl2["erros"] == 2,
        f"depois de um estouro o cronometro continua vivo ({segundo or pl2})")

    # D2: o foco do DOM e a escolha sao a MESMA coisa. As setas moviam so
    # o aria-current, entao Tab e setas olhavam para opcoes diferentes -- e
    # o Enter respondia a opcao errada. E 'disabled' no botao focado
    # destruia o foco a cada resposta.
    pgf2 = nav.new_page()
    ef2 = []
    pgf2.on("pageerror", lambda e: ef2.append(str(e)))
    pgf2.goto(B + "paginas/jogo.html?jogo=sala-do-titular&semente=7")
    pgf2.wait_for_timeout(400)
    pgf2.keyboard.press("ArrowDown")
    pgf2.keyboard.press("ArrowDown")
    foco = pgf2.evaluate("document.activeElement.id")
    marca = pgf2.eval_on_selector_all(
        "#opcoes button", "es=>es.findIndex(e=>e.getAttribute('aria-current')==='true')")
    chk(foco == "op2" and marca == 2,
        f"as setas movem o foco do DOM junto com a marca ({foco}, {marca})")

    pgf2.eval_on_selector("#op4", "e=>e.focus()")
    pgf2.keyboard.press("Enter")
    resp = pgf2.evaluate("""() => {
      var inc = ESTUDIO_JOGO.dados.direitos[4].inciso;
      var p = ESTUDIO_JOGO.placar();
      return {esperado: inc, visto: Object.keys(p.porInciso)[0],
              certo: ESTUDIO_JOGO.fila()[0]};
    }""")
    # Respondeu a opcao FOCADA (a quinta), e nao a que o cursor apontava.
    chk(resp["visto"] == resp["certo"],
        f"Enter com foco num botao responde AQUELE botao ({resp})")
    chk(pgf2.evaluate("document.activeElement.id") == "op4",
        "o foco sobrevive a resposta (aria-disabled, nao disabled)")
    chk(pgf2.eval_on_selector_all("#opcoes button", "e=>e.every(b=>!b.disabled)") is True,
        "nenhum botao usa o atributo disabled, que apaga o foco")

    # Responder duas vezes nao conta duas.
    dobro = pgf2.evaluate("""() => {
      var j = ESTUDIO_JOGO, a = JSON.stringify(j.placar());
      j.responder(0); j.responder(3);
      return a === JSON.stringify(j.placar());
    }""")
    chk(dobro, "responder de novo na mesma pergunta nao conta de novo")

    # As setas dao a volta nas duas pontas.
    volta = pgf2.evaluate("""() => {
      var n = ESTUDIO_JOGO.dados.direitos.length, r = {};
      document.getElementById('op0').focus();
      document.dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowUp', bubbles:true}));
      r.cima = document.activeElement.id;
      document.getElementById('op' + (n - 1)).focus();
      document.dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowDown', bubbles:true}));
      r.baixo = document.activeElement.id;
      return r;
    }""")
    chk(volta == {"cima": "op8", "baixo": "op0"},
        f"as setas dao a volta nas duas pontas ({volta})")

    # Uma partida inteira so de MOUSE -- a outra metade do caminho.
    pgm = nav.new_page()
    em = []
    pgm.on("pageerror", lambda e: em.append(str(e)))
    pgm.goto(B + "paginas/jogo.html?jogo=sala-do-titular&semente=3")
    pgm.wait_for_timeout(400)
    mfila = pgm.evaluate("""() => ({fila: ESTUDIO_JOGO.fila(),
      incisos: ESTUDIO_JOGO.dados.direitos.map(function (d) { return d.inciso; })})""")
    for inc in mfila["fila"]:
        pgm.click("#op" + str(mfila["incisos"].index(inc)))
        pgm.evaluate("ESTUDIO_JOGO.proximo()")
    pm = pgm.evaluate("ESTUDIO_JOGO.placar()")
    chk(not em and pm["acertos"] == len(mfila["fila"]),
        f"partida inteira so de mouse ({pm['acertos']}/{len(mfila['fila'])}, {em[:1]})")
    chk(not pgm.eval_on_selector("#fim", "e=>e.hidden"),
        "de mouse, a tela de resultado tambem aparece")
    chk(pgm.evaluate("document.activeElement.id") == "fim",
        "terminado o jogo, o foco pousa no resultado e nao no topo")


def paginas_e_preferencias(nav):
    """G6 e G7: a capa, o erro fatal na tela, a troca de tema nas paginas que
    ninguem abria, e o movimento reduzido trocado ao vivo."""
    # ---- G6: as paginas que nenhum teste abria -------------------------
    pgi = nav.new_page()
    ei = []
    pgi.on("pageerror", lambda e: ei.append(str(e)))
    pgi.on("console", lambda m: ei.append(m.text) if m.type == "error" else None)
    pgi.goto(B + "index.html")
    pgi.wait_for_timeout(300)
    chk(not ei, f"a capa do estudio carrega sem erro ({ei[:2]})")
    chk(pgi.eval_on_selector_all("a[href$='.html']", "e=>e.length") > 0,
        "a capa do estudio leva a alguma pagina")

    # O erro de roteiro tem de aparecer na TELA: os analistas editam sob
    # file:// e nao vao abrir o console. E a promessa do E.Chassi.fatal, e
    # nunca tinha sido cobrada.
    pgx = nav.new_page()
    pgx.on("pageerror", lambda e: None)   # o player relanca de proposito
    pgx.goto(B + "paginas/player.html?filme=nao-existe")
    pgx.wait_for_timeout(400)
    fatal = pgx.eval_on_selector_all(".est-erro-fatal", "e=>e.length")
    txt = pgx.eval_on_selector(".est-erro-fatal", "e=>e.textContent") if fatal else ""
    chk(fatal == 1 and "nao-existe" in txt,
        f"filme inexistente mostra o erro na tela, nao uma pagina branca ({txt[:60]!r})")
    chk(pgx.eval_on_selector(".est-erro-fatal", "e=>e.getAttribute('role')") == "alert",
        "o erro fatal e anunciado, nao so desenhado")

    # Troca de tema nas paginas que ninguem cobria. A folha de contato e o
    # caso duro: treze filmes montados de uma vez, cada um com o seu elenco.
    for pagina, quantos in [("paginas/folha-de-contato.html?filme=jornada-dado", 12),
                            ("paginas/personagens.html", 0),
                            ("paginas/jogo.html?jogo=sala-do-titular", 0)]:
        pgt = nav.new_page()
        et = []
        pgt.on("pageerror", lambda e: et.append(str(e)))
        pgt.on("console", lambda m: et.append(m.text) if m.type == "error" else None)
        pgt.goto(B + pagina)
        pgt.wait_for_timeout(500)
        antes = pgt.eval_on_selector_all(".est-rig", "e=>e.length")
        pgt.click("#btTema")
        pgt.wait_for_timeout(200)
        escuro = pgt.evaluate("document.documentElement.getAttribute('data-theme')")
        pintados = pgt.eval_on_selector_all(
            ".est-rig", "es=>es.filter(e=>e.style.getPropertyValue('--p-base')).length")
        chk(not et and escuro == "dark" and antes > 0 and pintados == antes,
            f"{pagina.split('/')[-1].split('?')[0]}: o tema escuro repinta todos os {antes} rigs "
            f"({pintados} pintados, {et[:1]})")
        if quantos:
            chk(pgt.eval_on_selector_all(".est-quadro", "e=>e.length") == quantos,
                f"{pagina.split('/')[-1].split('?')[0]}: os {quantos} quadros continuam la depois do tema")
        pgt.close()

    # ---- G7: movimento reduzido trocado AO VIVO ------------------------
    # player.js escuta 'change' na media query e troca de modo se a pessoa
    # nao escolheu a mao. O caminho inteiro nunca tinha sido percorrido.
    pgv = nav.new_page()
    pgv.goto(B + "paginas/player.html?filme=jornada-dado")
    pgv.wait_for_timeout(400)
    chk(pgv.evaluate("ESTUDIO_PLAYER.modo()") == "movimento",
        "sem preferencia do sistema, o player nasce em movimento")
    pgv.emulate_media(reduced_motion="reduce")
    pgv.wait_for_timeout(200)
    chk(pgv.evaluate("ESTUDIO_PLAYER.modo()") == "quadrinhos",
        "ligar movimento reduzido no sistema troca para quadrinhos ao vivo")
    chk(pgv.evaluate("ESTUDIO_PLAYER._raf()") is None,
        "trocado ao vivo para quadrinhos, nenhum rAF fica agendado")
    pgv.emulate_media(reduced_motion="no-preference")
    pgv.wait_for_timeout(200)
    chk(pgv.evaluate("ESTUDIO_PLAYER.modo()") == "movimento",
        "desligar movimento reduzido no sistema volta para movimento")

    # Depois de a pessoa escolher a mao, o sistema nao manda mais: a
    # escolha explicita vence a preferencia, que e o unico jeito de o botao
    # nao ser desfeito por baixo de quem o apertou.
    # Dois cliques, para terminar em MOVIMENTO: so assim ligar o movimento
    # reduzido depois e capaz de reprovar. Terminar em quadrinhos faria o
    # teste passar vazio, porque a preferencia pediria quadrinhos tambem.
    pgv.click("#btModo")
    pgv.wait_for_timeout(150)
    pgv.click("#btModo")
    pgv.wait_for_timeout(150)
    escolhido = pgv.evaluate("ESTUDIO_PLAYER.modo()")
    chk(escolhido == "movimento", f"dois cliques voltam ao movimento ({escolhido})")
    pgv.emulate_media(reduced_motion="reduce")
    pgv.wait_for_timeout(200)
    chk(pgv.evaluate("ESTUDIO_PLAYER.modo()") == escolhido,
        f"depois de escolher a mao, a preferencia do sistema nao manda mais ({escolhido})")
    pgv.close()


def fumaca_em_file(nav):
    """Sob http isso nunca falha. A regra 'sem fetch, sem modulo' so e de
    verdade se alguem abrir a pagina por file://."""
    # ---- fumaca em file:// ---------------------------------------------
    pg2 = nav.new_page()
    e2 = []
    pg2.on("pageerror", lambda e: e2.append(str(e)))
    pg2.on("console", lambda m: e2.append(m.text) if m.type == "error" else None)
    pg2.goto((RAIZ / "paginas/personagens.html").as_uri())
    pg2.wait_for_timeout(400)
    chk(not e2, f"folha abre por file:// sem erro (veio {e2[:2]})")
    chk(pg2.eval_on_selector_all("svg .est-rig", "e=>e.length") > 0,
        "rigs montam sob file:// (sem fetch, sem type=module)")

    pg3 = nav.new_page()
    e3 = []
    pg3.on("pageerror", lambda e: e3.append(str(e)))
    pg3.on("console", lambda m: e3.append(m.text) if m.type == "error" else None)
    # A query nao entra no Path: as_uri() a escaparia como parte do NOME do
    # arquivo, e o navegador procuraria "player.html%3Ffilme=...".
    pg3.goto((RAIZ / "paginas/player.html").as_uri() + "?filme=jornada-dado")
    pg3.wait_for_timeout(500)
    chk(not e3, f"player abre por file:// sem erro (veio {e3[:2]})")
    chk(pg3.eval_on_selector_all("[data-camada=atores] .est-rig", "e=>e.length") > 0,
        "o filme monta sob file://")
    # CP-004: <audio src> e elemento de midia, carrega por file:// como
    # <script src> carrega. O botao so aparece quando a trilha carregou.
    try:
        pg3.wait_for_selector("#btSom:not([hidden])", timeout=6000)
        chk(True, "a trilha carrega por file:// e o botao Som aparece")
    except Exception:
        chk(False, "a trilha carrega por file:// e o botao Som aparece")
    chk(pg3.evaluate("ESTUDIO_PLAYER.irPara(40); ESTUDIO_PLAYER.avancar(1); ESTUDIO_PLAYER.t()") > 40,
        "o transporte funciona sob file:// (rAF e matchMedia existem la)")

    pg4 = nav.new_page()
    e4 = []
    pg4.on("pageerror", lambda e: e4.append(str(e)))
    pg4.goto((RAIZ / "paginas/player.html").as_uri() + "?filme=legitimo-interesse")
    pg4.wait_for_timeout(500)
    chk(not e4 and pg4.evaluate("ESTUDIO_PLAYER.filme.id") == "legitimo-interesse",
        f"?filme= funciona sob file:// tambem ({e4[:2]})")

    pg5 = nav.new_page()
    e5 = []
    pg5.on("pageerror", lambda e: e5.append(str(e)))
    pg5.on("console", lambda m: e5.append(m.text) if m.type == "error" else None)
    pg5.goto((RAIZ / "paginas/jogo.html").as_uri() + "?jogo=sala-do-titular")
    pg5.wait_for_timeout(400)
    chk(not e5 and pg5.eval_on_selector_all("#opcoes button", "e=>e.length") == 9,
        f"o jogo abre e monta por file:// ({e5[:2]})")


# O contrato publico dos motores, travado. A regra do projeto e que nenhum
# metodo entra na API sem cliente real -- mas nada a cobrava, e foi assim que
# cinco metodos sem um unico chamador chegaram ate a Fase 6.
#
# Um detector sintatico de "metodo sem chamador" foi escrito e descartado:
# acusava vinte nomes, entre eles os seis easings, que sao chaves de dados
# consumidas por nome a partir do roteiro. Guarda com vinte falsos positivos e
# silenciada na primeira semana.
#
# Esta e a versao que funciona: a lista exata. Ela nao adivinha se ha cliente
# -- obriga quem acrescenta um metodo a vir aqui e dizer qual e. Que e a
# pergunta que a regra queria fazer, feita no momento em que da para responder.
CONTRATO = {
    "Estudio.Rig": ["criar", "definicao", "ids", "registrar"],
    "Rig.prototype": ["aplicar", "caixa", "contem", "destruir", "escala", "espelhar",
                      "estado", "expressao", "instantaneo", "opacidade", "parte",
                      "pos", "pose", "tema", "xray"],
    "Estudio.Filme": ["ACOES", "NUMERICAS", "carregar"],
    "Filme.prototype": ["citacaoEm", "instantaneo", "legendaEm", "planoEm",
                        "planoIndice", "renderizar", "snapshotDe", "tema"],
    "Estudio.Palco": ["CAMADAS", "criar"],
    "Palco.prototype": ["camera", "cenario", "rotulo"],
    "Estudio.Chassi": ["fatal", "regua", "transcricao"],
    # CP-004: o reprodutor escravo. Cliente de criar: player.js. Os metodos da
    # INSTANCIA sao internos ao player -- quem os lê e o hook _som, abaixo.
    "Estudio.Som": ["criar"],
    "Relogio": ["MAXDT", "_quadro", "_raf", "avancar", "parar", "tocando", "tocar"],
    "Player": ["_quadro", "_raf", "_som", "alternar", "avancar", "filme", "indice", "irPara",
               "irPlano", "modo", "palco", "pausar", "t", "tocando", "tocar"],
    "Jogo": ["_raf", "avancar", "comPrazo", "dados", "dpo", "fila", "indice", "palco",
             "placar", "proximo", "relogio", "responder"],
}

LEITURA = {
    "Estudio.Rig": "Object.keys(Estudio.Rig)",
    "Rig.prototype": "Object.keys(Object.getPrototypeOf(Estudio.Rig.criar('raposa')))"
                     ".filter(k=>k[0]!=='_')",
    "Estudio.Filme": "Object.keys(Estudio.Filme)",
    "Filme.prototype": "Object.keys(Object.getPrototypeOf(ESTUDIO_PLAYER.filme))"
                       ".filter(k=>k[0]!=='_')",
    "Estudio.Palco": "Object.keys(Estudio.Palco)",
    "Palco.prototype": "Object.keys(Object.getPrototypeOf(ESTUDIO_PLAYER.palco))"
                       ".filter(k=>k[0]!=='_')",
    "Estudio.Chassi": "Object.keys(Estudio.Chassi)",
    "Estudio.Som": "Object.keys(Estudio.Som)",
    "Relogio": "Object.keys(Estudio.Relogio(function(){}))",
    "Player": "Object.keys(ESTUDIO_PLAYER)",
}


def contrato_da_api(nav):
    """A superficie publica de cada motor, item a item.

    Metodo que entra sem cliente real e como o motor vira framework, e a
    unica hora barata de perguntar 'quem chama isto?' e quando a linha e
    escrita. Esta lista faz a pergunta ali."""
    pgk = nav.new_page()
    pgk.goto(B + "paginas/player.html?filme=jornada-dado")
    pgk.wait_for_timeout(400)
    for alvo, expr in LEITURA.items():
        lido = sorted(pgk.evaluate(expr))
        esperado = sorted(CONTRATO[alvo])
        sobra, falta = set(lido) - set(esperado), set(esperado) - set(lido)
        chk(lido == esperado,
            f"o contrato de {alvo} esta como declarado"
            + (f" -- entrou sem cliente declarado: {sorted(sobra)}" if sobra else "")
            + (f" -- sumiu: {sorted(falta)}" if falta else ""))
    pgk.close()

    pgk = nav.new_page()
    pgk.goto(B + "paginas/jogo.html?jogo=sala-do-titular")
    pgk.wait_for_timeout(400)
    lido = sorted(pgk.evaluate("Object.keys(ESTUDIO_JOGO)"))
    chk(lido == sorted(CONTRATO["Jogo"]),
        f"o contrato de Jogo esta como declarado ({lido})")
    pgk.close()


def a_camada_de_som(nav):
    """CP-004: o reprodutor escravo — nasce DESLIGADO, segue filme.t, e o
    modo quadrinhos permanece silencioso. O som nunca escreve o tempo:
    com Som desligado, nada muda em relacao ao filme mudo."""
    pg = nav.new_page()
    pg.goto(B + "paginas/player.html?filme=jornada-dado")
    pg.wait_for_timeout(500)

    # o botao nasce escondido e aparece quando a trilha carrega
    try:
        pg.wait_for_selector("#btSom:not([hidden])", timeout=8000)
        chk(True, "o botao Som aparece quando o filme declara trilha")
    except Exception:
        chk(False, "o botao Som aparece quando o filme declara trilha")
        pg.close()
        return
    chk(pg.eval_on_selector("#btSom", "b => b.getAttribute('aria-pressed')") == "false",
        "o Som nasce DESLIGADO (aria-pressed=false)")
    chk(pg.evaluate("ESTUDIO_PLAYER._som !== null"),
        "o player tem camada de som para filme que declara audio")
    chk(pg.eval_on_selector("#audioTxt", "e => e.textContent") == "com camada de áudio opcional",
        "a nota da pagina diz que a camada e opcional, sem mentir o mudo")

    # armar o som com o filme pausado NAO toca: escravo nao anda sozinho
    pg.click("#btSom")
    pg.wait_for_timeout(150)
    chk(pg.eval_on_selector("#btSom", "b => b.getAttribute('aria-pressed')") == "true",
        "clicar liga o Som (armado)")
    chk(pg.evaluate("ESTUDIO_PLAYER._som._el.paused"),
        "filme pausado: Som armado e o <audio> NAO adianta sozinho")

    # tocar o filme: o audio acompanha
    pg.evaluate("ESTUDIO_PLAYER.tocar()")
    pg.wait_for_timeout(400)
    chk(pg.evaluate("!ESTUDIO_PLAYER._som._el.paused"),
        "tocando o filme, o <audio> toca junto")

    # busca arrasta o audio junto (currentTime = filme.t)
    pg.evaluate("ESTUDIO_PLAYER.irPara(60)")
    pg.wait_for_timeout(250)
    d = pg.evaluate("Math.abs(ESTUDIO_PLAYER._som._el.currentTime - ESTUDIO_PLAYER.t())")
    chk(d < 0.2, f"buscar leva o audio junto (drift {d * 1000:.0f} ms)")

    # drift forcado: porQuadro ressincroniza acima de 80 ms
    pg.evaluate("ESTUDIO_PLAYER._som._el.currentTime = 10")
    pg.evaluate("ESTUDIO_PLAYER.avancar(0.2)")
    d = pg.evaluate("Math.abs(ESTUDIO_PLAYER._som._el.currentTime - ESTUDIO_PLAYER.t())")
    chk(d < 0.2, f"drift acima de 80 ms e corrigido por quadro (resto {d * 1000:.0f} ms)")

    # modo quadrinhos: silencioso nesta CP, e continua funcional
    pg.click("#btModo")
    pg.wait_for_timeout(150)
    chk(pg.evaluate("ESTUDIO_PLAYER._som._el.paused"),
        "modo quadrinhos silencia o audio (CP-004)")
    chk(pg.evaluate("ESTUDIO_PLAYER.modo() === 'quadrinhos'"),
        "e o modo quadrinhos segue funcional")
    pg.click("#btModo")
    pg.evaluate("ESTUDIO_PLAYER.tocar()")
    pg.wait_for_timeout(250)
    chk(pg.evaluate("!ESTUDIO_PLAYER._som._el.paused"),
        "voltar ao movimento retoma o audio ligado")

    # desligar: pausa, aria-pressed volta, o filme mudo e o produto completo
    pg.click("#btSom")
    chk(pg.eval_on_selector("#btSom", "b => b.getAttribute('aria-pressed')") == "false",
        "clicar de novo desliga o Som")
    chk(pg.evaluate("ESTUDIO_PLAYER._som._el.paused"),
        "desligado, o <audio> pausa — comportamento do mudo")
    pg.close()

    # sem trilha, o botao nao nasce: filme mudo e o fallback natural
    pg2 = nav.new_page()
    pg2.goto(B + "paginas/player.html?filme=jornada-dado")
    pg2.wait_for_timeout(400)
    sumiu = pg2.evaluate("""() => new Promise(ok => {
      var bt = document.createElement('button'); bt.hidden = false;
      Estudio.Som.criar({ bt: bt, filme: { id: 'sem-trilha-nenhuma', t: 0 },
                          base: '../' });
      setTimeout(() => ok(bt.hidden), 900);
    })""")
    chk(sumiu, "sem audio/<id>.opus o botao nao aparece — o fallback natural")
    pg2.close()


def escrever_relatorios():
    """Uma execucao deixa evidencia por filme, nao so um numero global.

    E disto que o agente `curador` vive: portao que reprova no mesmo lugar em
    varios filmes nao e um filme ruim, e um portao errado ou uma ferramenta que
    falta. Nao da para descobrir isso a partir de "198 passaram".
    """
    import datetime
    quando = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    for alvo, d in POR_ALVO.items():
        pasta = (RAIZ / "filmes" / alvo) if (RAIZ / "filmes" / alvo).is_dir() else (RAIZ / "jogos" / alvo)
        if not pasta.is_dir():
            continue
        rel = {"alvo": alvo, "quando": quando,
               "checagens_ok": d["ok"],
               "achados": {f"achado-{i+1}": a for i, a in enumerate(d["achados"])},
               "nota": (f"{d['ok']} checagem(ns) verdes" if not d["achados"]
                        else f"{len(d['achados'])} achado(s)")}
        (pasta / "relatorio.json").write_text(
            json.dumps(rel, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    # E o acumulado, que e o que o curador varre.
    hist = RAIZ / "harness" / "runs"
    hist.mkdir(parents=True, exist_ok=True)
    (hist / f"run-{quando.replace(':', '')}.json").write_text(
        json.dumps({"quando": quando, "ok": len(ok), "falhas": len(bad),
                    "achados": bad, "por_alvo": POR_ALVO},
                   ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    print(f"  evidencia: {len(POR_ALVO)} relatorio(s) por alvo + harness/runs/")


def main():
    estaticos()
    links_do_estudio()
    opacidade_de_repouso()
    srv = servidor()
    with sync_playwright() as pw:
        nav = abrir(pw)
        contrato_da_api(nav)
        personagens_e_rigs(nav)
        pgf = filme_e_transporte(nav)
        segundo_filme(nav, pgf)
        a_camada_de_som(nav)
        injecao_de_falha(nav)
        o_jogo(nav)
        jogo_caminhos_esquecidos(nav)
        paginas_e_preferencias(nav)
        fumaca_em_file(nav)

        nav.close()
    srv.shutdown()

    if GRAVAR:
        print(f"\n  {len(gravados)} referencia(s) gravada(s). "
              f"Leia o diff antes de commitar.")
    for m in ok:
        print("  ok  ", m)
    for m in bad:
        print("  FALHOU", m)
    print(f"\n  {len(ok)} passaram, {len(bad)} falharam")
    escrever_relatorios()
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
