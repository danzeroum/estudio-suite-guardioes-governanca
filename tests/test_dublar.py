#!/usr/bin/env python3
"""O fiscal de redublagem, provado nos dois sentidos.

"Editar o filme sem regravar a referencia" ja era erro caro o bastante para
ter fiscal proprio -- a dublagem herda a regra, porque audio e derivado: quem
edita a legenda sem rodar dublar deixa divida que so aparece quando alguem
OUVE. Aqui a divida aparece em texto, no portao storyboard.

Os casos usam um filme fantasma com dublagem fantasma (audio.json calculado,
sem audio de verdade): o fiscal compara TEXTO e TEMPO, nao bytes de audio --
por isso o teste roda em CI, onde piper nao existe.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import fala                          # noqa: E402
from estudio_suite.comum import FILMES, filmes_existentes  # noqa: E402
from estudio_suite.pipeline import fiscal_redublagem    # noqa: E402

ok, bad = [], []
FANTASMA = "teste-dublagem-fantasma"


def chk(c, msg):
    (ok if c else bad).append(msg)


def _hash(txt):
    return hashlib.sha256(fala.normalizar(txt).encode("utf-8")).hexdigest()


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


def _criar_dublagem(clipes):
    """audio.json fantasma: [{plano, em, ate, dur, voz, texto_sha256}]."""
    d = FILMES / FANTASMA / "audio"
    d.mkdir(parents=True, exist_ok=True)
    manifesto = {"filme": FANTASMA, "clipes": clipes}
    (d / "audio.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _cenario(legendas, clipes):
    _criar_filme(legendas)
    _criar_dublagem(clipes)


def main():
    # --- em sincronia: o fiscal cala -----------------------------------
    L1 = (0.3, 5.5, "Uma legenda que fala.")
    L2 = (6.0, 11.0, "Outra legenda, outro tempo.")
    _cenario([L1, L2], [
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2])},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2])},
    ])
    achados_sync = fiscal_redublagem(FANTASMA)
    chk(achados_sync == [],
        f"em sincronia, nenhum achado ({achados_sync})")

    # --- texto editado sem redublar: divida apontada -------------------
    _cenario([(0.3, 5.5, "Uma legenda EDITADA."), L2], [
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2])},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2])},
    ])
    a = fiscal_redublagem(FANTASMA)
    chk(len(a) == 1 and "mudou de texto" in a[0] and "dublar" in a[0],
        f"texto editado sem redublar e apontado com o comando que resolve ({a})")

    # --- tempo editado sem redublar: divida apontada -------------------
    _cenario([(0.3, 5.0, L1[2]), L2], [
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2])},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2])},
    ])
    a = fiscal_redublagem(FANTASMA)
    chk(len(a) == 1 and "termina em" in a[0],
        f"tempo editado sem redublar e apontado ({a})")

    # --- legenda nova, sem clipe: divida apontada ----------------------
    _cenario([L1, L2, (11.2, 11.9, "Nova no fim.")], [
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2])},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2])},
    ])
    a = fiscal_redublagem(FANTASMA)
    chk(any("nao existe na dublagem" in x for x in a),
        f"legenda sem clipe e apontada ({a})")

    # --- legenda apagada, clipe sobrando: divida apontada --------------
    _cenario([L1], [
        {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 4.2, "voz": "coruja",
         "texto_sha256": _hash(L1[2])},
        {"plano": "p01", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
         "texto_sha256": _hash(L2[2])},
    ])
    a = fiscal_redublagem(FANTASMA)
    chk(any("clipe(s) para" in x for x in a),
        f"clipe orfao de legenda apagada e apontado ({a})")

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
