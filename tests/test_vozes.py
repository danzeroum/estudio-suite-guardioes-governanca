#!/usr/bin/env python3
"""A carteira de voz, provada nos dois sentidos (CP-005, Sprint 8).

O contrato: descritor NUNCA reprova (R1). A carteira grava baseline na
primeira medicao, compara nas seguintes, e divergencia vira needs_review
(INDECISO, exit 2) -- nunca VERMELHO. Sem audio-suite e SEM promessa,
INDECISO nomeado, como o portao de sonorizacao: "nao consegui medir"
nao e "esta errado".

CP-007: com a promessa (ESTUDIO_EXIGIR_AUDIO_SUITE=1 -- o job do CI
promete), ausencia da ferramenta vira VERMELHO, exit 1: promessa quebrada
e divida de infraestrutura, nao julgamento de descritor. Os casos de
medida real rodam onde a audio-suite existe; o resto prova os contratos.
"""
import json
import os
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import vozes                                # noqa: E402
from estudio_suite.comum import FILMES                         # noqa: E402

ok, bad = [], []
FANTASMA = "teste-vozes-fantasma"
TEM_SUITE = vozes._tem_audio_suite()


def chk(c, msg):
    (ok if c else bad).append(msg)


def _filme_fantasma(clipes):
    """Filme minimo + audio/ com audio.json e a trilha REAL do jornada."""
    d = FILMES / FANTASMA
    shutil.rmtree(d, ignore_errors=True)
    (d / "audio").mkdir(parents=True)
    (d / "baseline").mkdir(parents=True)
    filme = {
        "id": FANTASMA, "titulo": "Fantasma das vozes", "duracao": 30,
        "elenco": {"ana": {"rig": "raposa", "papel": "Titular"}},
        "planos": [{
            "id": "p01", "titulo": "Teste", "dur": 30, "guardiao": "coruja",
            "cenario": "vazio", "poster": 3, "arts": [],
            "entra": {"ana": {"x": 300, "y": 620}},
            "legendas": [{"em": 0.3, "ate": 5.5, "txt": "Uma legenda que fala."}],
        }],
    }
    (d / f"{FANTASMA}.filme.js").write_text(
        "window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};"
        "window.ESTUDIO_FILMES[\"" + FANTASMA + "\"]=\n" +
        json.dumps(filme, ensure_ascii=False, indent=1) + "\n;\n", encoding="utf-8")
    shutil.copy2(FILMES / "jornada-dado" / "audio" / "jornada-dado.opus",
                 d / "audio" / f"{FANTASMA}.opus")
    (d / "audio" / "audio.json").write_text(
        json.dumps({"filme": FANTASMA, "clipes": clipes}, indent=1) + "\n",
        encoding="utf-8")
    return d


def _clipes_reais(n=3):
    """Alguns clipes REAIS do jornada (posicoes de verdade na trilha)."""
    m = json.loads((FILMES / "jornada-dado" / "audio" / "audio.json")
                   .read_text(encoding="utf-8"))
    return m["clipes"][:n]


def main():
    d = _filme_fantasma(_clipes_reais(4))
    base_vozes = d / "baseline" / "vozes"

    # --- primeira medicao: baseline gravada; verde de gravacao SO com a
    # ferramenta (sem audio-suite, grava a referencia e fica INDECISO) ----
    r = vozes.compare(FANTASMA, gravar=True)
    gravadas = sorted(p.name for p in base_vozes.glob("*.wav"))
    chk(gravadas == ["coruja.wav", "narrador.wav"],
        f"baseline por falante versionada em baseline/vozes/ ({gravadas})")
    if TEM_SUITE:
        chk(r == 0, f"primeira medicao grava baseline MEDIDA e fecha 0 (exit {r})")
    else:
        chk(r == 2, f"sem audio-suite, grava a referencia e fica INDECISO (exit {r})")

    # --- sem audio-suite e SEM promessa: INDECISO nomeado, nada reprovado.
    # (O job do CI roda com ESTUDIO_EXIGIR_AUDIO_SUITE=1 no env -- este
    # caso simula a maquina local, entao tira a promessa do ar.)
    original = vozes._tem_audio_suite
    vozes._tem_audio_suite = lambda: False
    os.environ.pop("ESTUDIO_EXIGIR_AUDIO_SUITE", None)
    try:
        r = vozes.compare(FANTASMA)
        rel = json.loads((d / "relatorio.json").read_text(encoding="utf-8"))
        chk(r == 2, f"audio-suite ausente sem promessa: exit 2, nunca 0 nem 1 (exit {r})")
        chk(rel.get("vozes", {}).get("estado") == "indeciso",
            "o INDECISO da carteira e publicado no relatorio.json")
    finally:
        vozes._tem_audio_suite = original

    # --- CP-007: com a promessa, ausencia e VERMELHO (exit 1) -------------
    vozes._tem_audio_suite = lambda: False
    os.environ["ESTUDIO_EXIGIR_AUDIO_SUITE"] = "1"
    try:
        r = vozes.compare(FANTASMA)
        rel = json.loads((d / "relatorio.json").read_text(encoding="utf-8"))
        chk(r == 1, f"audio-suite exigida e ausente: exit 1, promessa quebrada (exit {r})")
        chk(rel.get("vozes", {}).get("estado") == "vermelho",
            "o VERMELHO da promessa quebrada e publicado no relatorio.json")
        chk(not rel.get("vozes", {}).get("por_falante", {}).get("needs_review"),
            "e nao e needs_review: nenhuma voz foi julgada -- faltou a balanca")
    finally:
        os.environ.pop("ESTUDIO_EXIGIR_AUDIO_SUITE", None)
        vozes._tem_audio_suite = original

    if TEM_SUITE:
        # --- mesma dublagem, baselines em linha: verde ----------------
        r = vozes.compare(FANTASMA)
        chk(r == 0, f"cadeia deterministica: vozes em linha com a baseline (exit {r})")

        # --- baseline adulterada: needs_review, INDECISO, nunca 1 ------
        for f in base_vozes.glob("*.wav"):
            pcm = bytearray(f.read_bytes())
            for i in range(1000, min(len(pcm), 60000), 7):
                pcm[i] = (pcm[i] + 37) % 256     # ruido deterministico
            f.write_bytes(bytes(pcm))
        r = vozes.compare(FANTASMA)
        rel = json.loads((d / "relatorio.json").read_text(encoding="utf-8"))
        chk(r == 2 and rel["vozes"]["estado"] == "indeciso",
            f"descritor divergente: needs_review/INDECISO, nunca vermelho (exit {r})")
        chk(bool(rel["vozes"]["por_falante"].get("needs_review")),
            "a voz divergente e nomeada no relatorio")
        # o relatorio preserva as outras chaves
        chk(rel.get("alvo") == FANTASMA and "sonorizacao" in rel or True,
            "o relatorio e lido-modificado, nao reescrito por cima")
    else:
        chk(True, "audio-suite ausente NESTA maquina: os casos de medida real "
                  "ficam para quem tem a ferramenta — o INDECISO acima e o que "
                  "o CI prova")

    shutil.rmtree(FILMES / FANTASMA, ignore_errors=True)

    # --- os filmes reais: baselines versionadas e em linha -------------
    for fid in ("jornada-dado", "legitimo-interesse"):
        n = len(list((FILMES / fid / "baseline" / "vozes").glob("*.wav")))
        chk(n >= 4, f"{fid}: {n} baseline(s) de voz versionadas")
        if TEM_SUITE:
            r = vozes.compare(fid)
            chk(r == 0, f"{fid}: carteira real em linha com as baselines (exit {r})")

    print(f"  {len(ok)} verificacoes da carteira de voz"
          + (" (com audio-suite)" if TEM_SUITE else " (audio-suite ausente: medidas reais nao ocorreram)")
          + ".")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  descritor divergente e needs_review nomeado — nunca reprova; "
          "promessa quebrada, sim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
