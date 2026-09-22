#!/usr/bin/env python3
"""O sexto portao, provado nos dois sentidos — inclusive o que o CI prova.

O contrato do portao de sonorizacao (CP-004) tem uma clausula incomum:
AUSENCIA da ferramenta nao reprova. O runner do CI nao tem a audio-suite, e
o portao la devolve INDECISO — publicado, nomeado, nunca chamado de verde.
Aqui os casos locais provam o resto: verde com trilha dentro das ancoras,
vermelho com trilha estourada, e as duas formas de a declaracao divergir do
real.

Quando a audio-suite nao esta na maquina, os casos de MEDIDA REAL se anunciam
como nao medidos — sem fingir verificacao que nao houve.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import pipeline                      # noqa: E402
from estudio_suite.comum import FILMES                  # noqa: E402

ok, bad = [], []
FANTASMA = "teste-sonoro-fantasma"
TEM_SUITE = pipeline._tem_audio_suite()


def chk(c, msg):
    (ok if c else bad).append(msg)


def _filme(declara, com_trilha=None):
    """Filme minimo; com_trilha: 'boa' copia a trilha real, 'estourada' clipa."""
    d = FILMES / FANTASMA
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    filme = {
        "id": FANTASMA, "titulo": "Fantasma sonoro", "duracao": 6,
        "elenco": {"ana": {"rig": "raposa", "papel": "Titular"}},
        "planos": [{
            "id": "p01", "titulo": "Teste", "dur": 6, "guardiao": "coruja",
            "cenario": "vazio", "poster": 3, "arts": [],
            "entra": {"ana": {"x": 300, "y": 620}},
            "legendas": [{"em": 0.3, "ate": 5.5, "txt": "Um teste do portao."}],
        }],
    }
    if declara:
        filme["audio"] = True
    (d / f"{FANTASMA}.filme.js").write_text(
        "window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};"
        "window.ESTUDIO_FILMES[\"" + FANTASMA + "\"]=\n" +
        json.dumps(filme, ensure_ascii=False, indent=1) + "\n;\n", encoding="utf-8")
    if com_trilha:
        boa = FILMES / "jornada-dado" / "audio" / "jornada-dado.opus"
        destino = d / "audio"
        destino.mkdir()
        if com_trilha == "boa":
            shutil.copy2(boa, destino / f"{FANTASMA}.opus")
        else:
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(boa),
                            "-af", "volume=8.0", "-c:a", "libopus", "-b:a", "40k",
                            str(destino / f"{FANTASMA}.opus")], check=True)
    return d


def _sem_audio_suite():
    """O mundo como o runner do CI o ve."""
    original = pipeline._tem_audio_suite
    pipeline._tem_audio_suite = lambda: False
    return original


def main():
    # --- filme mudo: o portao nem acorda --------------------------------
    _filme(declara=False, com_trilha=None)
    v = pipeline.portao_sonorizacao(FANTASMA)
    chk(v.ok and "nada a medir" in v.nota,
        f"filme mudo: verde com 'nada a medir' ({v.estado}, {v.nota!r})")

    # --- declaracao sem entrega: o contrato mente ------------------------
    _filme(declara=True, com_trilha=None)
    v = pipeline.portao_sonorizacao(FANTASMA)
    chk(v.estado == "vermelho" and "falta" in v.achados[0],
        f"declara audio sem trilha: VERMELHO ({v.achados})")

    # --- entrega sem declaracao: decida, nao acumule ---------------------
    _filme(declara=False, com_trilha="boa")
    v = pipeline.portao_sonorizacao(FANTASMA)
    chk(v.estado == "vermelho" and "decida" in " ".join(v.achados).lower(),
        f"trilha sem declaracao: VERMELHO ({v.achados})")

    # --- o caso do CI: sem audio-suite, INDECISO e ponto -----------------
    _filme(declara=True, com_trilha="boa")
    original = _sem_audio_suite()
    try:
        v = pipeline.portao_sonorizacao(FANTASMA)
        rel = json.loads((FILMES / FANTASMA / "relatorio.json").read_text(encoding="utf-8"))
        chk(v.estado == "indeciso" and not v.achados,
            f"audio-suite ausente: INDECISO sem achado de reprovacao ({v.estado})")
        chk(rel.get("sonorizacao", {}).get("estado") == "indeciso",
            "o INDECISO e publicado no relatorio.json, nomeado como tal")
    finally:
        pipeline._tem_audio_suite = original

    # --- com a ferramenta: verde na ancora, vermelho no estouro ----------
    if TEM_SUITE:
        _filme(declara=True, com_trilha="boa")
        v = pipeline.portao_sonorizacao(FANTASMA)
        chk(v.ok and "ancoras" in v.nota,
            f"trilha dentro das ancoras: VERDE ({v.estado}, {v.nota!r})")

        _filme(declara=True, com_trilha="estourada")
        v = pipeline.portao_sonorizacao(FANTASMA)
        chk(v.estado == "vermelho" and any("clipping" in a or "true_peak" in a
                                           for a in v.achados),
            f"trilha estourada: VERMELHO nomeando o defeito ({v.achados})")
    else:
        chk(True, "audio-suite ausente NESTA maquina: VERDE/VERMELHO reais ficam "
                  "para quem tem a ferramenta — o INDECISO acima e o que o CI prova")

    shutil.rmtree(FILMES / FANTASMA, ignore_errors=True)

    # --- os filmes reais: estado publicado e coerente --------------------
    if TEM_SUITE:
        for fid in ("jornada-dado", "legitimo-interesse"):
            v = pipeline.portao_sonorizacao(fid)
            rel = json.loads((FILMES / fid / "relatorio.json").read_text(encoding="utf-8"))
            chk(v.ok, f"{fid}: trilha real dentro das ancoras ({v.nota!r})")
            chk(rel.get("sonorizacao", {}).get("estado") == "verde",
                f"{fid}: estado VERDE publicado no relatorio.json")

    # --- o passo de CI: indeciso documentado nao quebra o build -----------
    r = subprocess.run([sys.executable, "ci/portao_sonorizacao.py"],
                       capture_output=True, text=True, cwd=RAIZ)
    chk(r.returncode == 0,
        f"o passo de CI fecha 0 (verde ou indeciso documentado) — exit {r.returncode}")
    if not TEM_SUITE:
        chk("indeciso" in r.stdout,
            "e o passo de CI NOMEIA o indeciso, sem chamar de verde")

    print(f"  {len(ok)} verificacoes do portao de sonorizacao"
          + (" (com audio-suite)" if TEM_SUITE else " (audio-suite ausente: medidas reais nao ocorreram)") + ".")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  ausencia da ferramenta e INDECISO nomeado, nao verde nem vermelho.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
