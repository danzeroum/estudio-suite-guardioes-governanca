#!/usr/bin/env python3
"""O fiscal de redublagem, provado nos dois sentidos.

"Editar o filme sem regravar a referencia" ja era erro caro o bastante para
ter fiscal proprio -- a dublagem herda a regra, porque audio e derivado: quem
edita a legenda sem rodar dublar deixa divida que so aparece quando alguem
OUVE. Aqui a divida aparece em texto, no portao storyboard.

Os casos usam um filme fantasma com dublagem fantasma (audio.json calculado,
sem audio de verdade): o fiscal compara TEXTO e TEMPO, nao bytes de audio --
por isso o teste roda em CI, onde piper nao existe. Desde a CP-007 o fiscal
cobra TAMBEM o campo ambiente do manifesto (== voz.lock), e o dublar confere
o ambiente instalado ANTES de sintetizar -- o caso divergente e provado com
onnxruntime mentindo via importlib.metadata, sem tocar arquivo nenhum.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import fala                          # noqa: E402
from estudio_suite.comum import ErroDeDados, FILMES, filmes_existentes  # noqa: E402
from estudio_suite.pipeline import fiscal_redublagem    # noqa: E402

ok, bad = [], []
FANTASMA = "teste-dublagem-fantasma"


def chk(c, msg):
    (ok if c else bad).append(msg)


def _hash(txt):
    return hashlib.sha256(fala.normalizar(txt).encode("utf-8")).hexdigest()


def _timbre_coruja():
    """O timbre esperado do rig coruja REAL (CP-005): o fiscal compara o
    gravado contra o que o rig declara HOJE -- o fantasma em sincronia
    carrega o mesmo dicionario que o dublar gravaria."""
    from estudio_suite import amostras
    from estudio_suite.dublar import voz_do_rig
    t = voz_do_rig("coruja")["timbre"]
    return {"portadora": t["portadora"], "mistura": float(t["mistura"]),
            "bandas": int(t["bandas"]),
            "portadora_sha256": amostras.ancora()[t["portadora"]]["sha256"]}


def _timbre_coruja():
    """O timbre esperado do rig coruja REAL (CP-005): o fiscal compara o
    gravado contra o que o rig declara HOJE -- o fantasma em sincronia
    carrega o mesmo dicionario que o dublar gravaria."""
    from estudio_suite import amostras
    from estudio_suite.dublar import voz_do_rig
    t = voz_do_rig("coruja")["timbre"]
    return {"portadora": t["portadora"], "mistura": float(t["mistura"]),
            "bandas": int(t["bandas"]),
            "portadora_sha256": amostras.ancora()[t["portadora"]]["sha256"]}


def _criar_filme(legendas):
    """Filme minimo com as legendas dadas [(em, ate, txt)] no plano p01."""
    d = FILMES / FANTASMA
    d.mkdir(parents=True, exist_ok=True)
    filme = {
        "id": FANTASMA, "titulo": "Fantasma da dublagem", "duracao": 12,
        "elenco": {"ana": {"rig": "raposa", "papel": "Titular"}},
        "planos": [{
            "id": "p01", "titulo": "Teste", "dur": 12, "guardiao": "coruja",
            "cenario": "vazio", "poster": 3, "arts": [],
            "entra": {"ana": {"x": 300, "y": 620}},
            "legendas": [{"em": em, "ate": ate, "txt": txt} for em, ate, txt in legendas],
        }],
    }
    (d / f"{FANTASMA}.filme.js").write_text(
        "window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};"
        "window.ESTUDIO_FILMES[\"" + FANTASMA + "\"]=\n" +
        json.dumps(filme, ensure_ascii=False, indent=1) + "\n;\n", encoding="utf-8")
    return d


def _criar_dublagem(clipes, ambiente="do-lock"):
    """audio.json fantasma: [{plano, em, ate, dur, voz, texto_sha256}].

    ambiente="do-lock" grava o bloco ambiente do voz.lock (o que o dublar
    gravaria); ambiente=None grava manifesto SEM o campo (a divida que a
    CP-007 cobra); qualquer dict e gravado como esta (divergencia proposital).
    """
    from estudio_suite import voz as _voz
    d = FILMES / FANTASMA / "audio"
    d.mkdir(parents=True, exist_ok=True)
    manifesto = {"filme": FANTASMA, "clipes": clipes}
    if ambiente == "do-lock":
        manifesto["ambiente"] = _voz.ancora()["ambiente"]
    elif ambiente is not None:
        manifesto["ambiente"] = ambiente
    (d / "audio.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _cenario(legendas, clipes):
    _criar_filme(legendas)
    _criar_dublagem(clipes)


def main():
    T = _timbre_coruja()
    # --- em sincronia: o fiscal cala -----------------------------------
    L1 = (0.3, 5.5, "Uma legenda que fala.")
    L2 = (6.0, 11.0, "Outra legenda, outro tempo.")
    _cenario([L1, L2], [
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2]), "timbre": dict(T)},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2]), "timbre": dict(T)},
    ])
    achados_sync = fiscal_redublagem(FANTASMA)
    chk(achados_sync == [],
        f"em sincronia, nenhum achado ({achados_sync})")

    # --- texto editado sem redublar: divida apontada -------------------
    _cenario([(0.3, 5.5, "Uma legenda EDITADA."), L2], [
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2]), "timbre": dict(T)},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2]), "timbre": dict(T)},
    ])
    a = fiscal_redublagem(FANTASMA)
    chk(len(a) == 1 and "mudou de texto" in a[0] and "dublar" in a[0],
        f"texto editado sem redublar e apontado com o comando que resolve ({a})")

    # --- tempo editado sem redublar: divida apontada -------------------
    _cenario([(0.3, 5.0, L1[2]), L2], [
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2]), "timbre": dict(T)},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2]), "timbre": dict(T)},
    ])
    a = fiscal_redublagem(FANTASMA)
    chk(len(a) == 1 and "termina em" in a[0],
        f"tempo editado sem redublar e apontado ({a})")

    # --- legenda nova, sem clipe: divida apontada ----------------------
    _cenario([L1, L2, (11.2, 11.9, "Nova no fim.")], [
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2]), "timbre": dict(T)},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2]), "timbre": dict(T)},
    ])
    a = fiscal_redublagem(FANTASMA)
    chk(any("nao existe na dublagem" in x for x in a),
        f"legenda sem clipe e apontada ({a})")

    # --- legenda apagada, clipe sobrando: divida apontada --------------
    _cenario([L1], [
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2]), "timbre": dict(T)},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2]), "timbre": dict(T)},
    ])
    a = fiscal_redublagem(FANTASMA)
    chk(any("clipe(s) para" in x for x in a),
        f"clipe orfao de legenda apagada e apontado ({a})")

    # --- audio.json sem ambiente: dublagem de mundo desconhecido (CP-007) --
    _criar_filme([L1, L2])
    _criar_dublagem([
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2]), "timbre": dict(T)},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2]), "timbre": dict(T)},
    ], ambiente=None)
    a = fiscal_redublagem(FANTASMA)
    chk(len(a) == 1 and "sem o campo ambiente" in a[0] and "dublar" in a[0],
        f"manifesto sem ambiente e apontado com o comando que resolve ({a})")

    # --- ambiente divergente do lock: nomeado, campo a campo (CP-007) ----
    from estudio_suite import voz as _voz
    amb_errado = dict(_voz.ancora()["ambiente"], numpy="9.9.9")
    _criar_dublagem([
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2]), "timbre": dict(T)},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2]), "timbre": dict(T)},
    ], ambiente=amb_errado)
    a = fiscal_redublagem(FANTASMA)
    chk(len(a) == 1 and "diverge do voz.lock" in a[0] and "numpy" in a[0]
        and "9.9.9" in a[0],
        f"ambiente divergente e apontado nomeando o pacote e a versao ({a})")

    # --- dublar em ambiente divergente: ErroDeDados, nenhum arquivo (CP-007)
    # O onnxruntime MENTE via importlib.metadata -- o caminho exato que a
    # conferencia usa. E o materializar e espiado: conferencia que passa do
    # ponto de escrita e conferencia que nao conferiu nada.
    import importlib.metadata as _md
    import types as _types
    from estudio_suite import dublar as _dub
    _versao_real = _md.version
    _materializar_real = _voz.materializar
    tocou = []

    def _espiar(*a_, **k_):
        tocou.append(1)
        return _materializar_real(*a_, **k_)

    _voz.materializar = _espiar
    _md.version = lambda nome: ("9.9.9" if nome == "onnxruntime"
                                else _versao_real(nome))
    try:
        try:
            _dub.dublar("jornada-dado")
            chk(False, "dublar em ambiente divergente tinha de levantar ErroDeDados")
        except ErroDeDados as e:
            msg = str(e)
            chk("onnxruntime" in msg and "1.30.0" in msg and "9.9.9" in msg,
                f"a divergencia nomeia pacote, esperado e instalado ({msg[:150]!r})")
            chk("pip install onnxruntime==1.30.0" in msg,
                "e diz o comando que corrige, sem flag de contorno")
            # CP-008: a saida portatil vem ANTES das correcoes pacote a pacote
            chk("ferramentas/dublador/dublar.sh" in msg
                and msg.index("ferramentas/dublador/dublar.sh")
                < msg.index("pip install onnxruntime==1.30.0"),
                "a imagem dubladora e oferecida primeiro, as correcoes vem depois")
        chk(not tocou,
            "a conferencia vem ANTES de materializar: ambiente errado nao "
            "escreve nem o workspace, quanto menos audio")
    finally:
        _md.version = _versao_real
        _voz.materializar = _materializar_real

    # --- arquitetura divergente (CP-008): platform.machine() mentindo -----
    # A CPU faz parte do ambiente: o onnxruntime despacha kernels pela
    # arquitetura, e uma conferencia que passa em arm64 nao prova bytes que
    # nasceram em x86_64. O dublar recusa citando a arquitetura, sem tocar
    # arquivo -- o espiao do materializar continua vigiando.
    _platform_real = _voz.platform
    _stub = _types.ModuleType("platform")
    _stub.machine = lambda: "aarch64"
    _voz.platform = _stub
    _voz.materializar = _espiar
    tocou.clear()
    try:
        try:
            _dub.dublar("jornada-dado")
            chk(False, "dublar em arquitetura divergente tinha de levantar ErroDeDados")
        except ErroDeDados as e:
            msg = str(e)
            chk("arquitetura" in msg and "aarch64" in msg and "x86_64" in msg,
                f"a divergencia de arquitetura nomeia esperado e instalado ({msg[:150]!r})")
        chk(not tocou,
            "arquitetura errada tambem nao escreve arquivo nenhum")
    finally:
        _voz.platform = _platform_real
        _voz.materializar = _materializar_real

    # --- voz.lock sem arquitetura: lock INCOMPLETO, nunca x86_64 por osmose
    # (CP-008). Assumir a arquitetura da maquina que roda seria ancorar por
    # coincidencia: o lock recusado e o lock que falta dado, nao o ambiente
    # que "por acaso" bate.
    _lock_real = _voz.LOCK
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _tmp:
        sem_arquitetura = Path(_tmp) / "voz.lock"
        sem_arquitetura.write_text(
            _lock_real.read_text(encoding="utf-8").replace("  arquitetura: x86_64\n", ""),
            encoding="utf-8")
        _voz.LOCK = sem_arquitetura
        _voz.materializar = _espiar
        tocou.clear()
        try:
            _dub.dublar("jornada-dado")
            chk(False, "dublar com lock sem arquitetura tinha de recusar")
        except ErroDeDados as e:
            msg = str(e)
            chk("arquitetura" in msg and "incompleto" in msg.lower(),
                f"lock sem arquitetura e recusado como lock incompleto ({msg[:150]!r})")
            chk("x86_64" not in msg.split("lock INCOMPLETO")[1].split("\n")[0]
                or "assumir" in msg,
                "e nao assume x86_64 por padrao -- a saida e medir e ancorar")
        chk(not tocou, "lock incompleto tambem nao toca arquivo nenhum")
    _voz.LOCK = _lock_real
    _voz.materializar = _materializar_real

    # --- sem audio/: filme mudo e valido, fiscal cala ------------------
    _criar_filme([L1, L2])
    shutil.rmtree(FILMES / FANTASMA / "audio", ignore_errors=True)
    chk(fiscal_redublagem(FANTASMA) == [],
        "filme sem audio/ nao e fiscalizado — a camada e aditiva")
    shutil.rmtree(FILMES / FANTASMA, ignore_errors=True)

    # --- os filmes reais com dublagem commitada estao em dia -----------
    dublados = [f for f in filmes_existentes()
                if (FILMES / f / "audio" / "audio.json").exists()]
    chk(len(dublados) >= 2, f"os filmes dubladados estao versionados ({dublados})")
    for fid in dublados:
        a = fiscal_redublagem(fid)
        chk(a == [], f"{fid}: dublagem commitada em dia com as legendas ({a})")

    print(f"  {len(ok)} verificacoes do fiscal de redublagem.")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  legenda editada sem dublar e divida apontada, nao divida ouvida.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
