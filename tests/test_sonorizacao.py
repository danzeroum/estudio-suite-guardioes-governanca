#!/usr/bin/env python3
"""O sexto portao, provado nos dois sentidos — inclusive o que o CI prova.

O contrato do portao de sonorizacao (CP-004) tem uma clausula incomum:
AUSENCIA da ferramenta nao reprova — quando ninguem prometeu nada. O
runner do CI nao tinha a audio-suite e o portao la devolvia INDECISO —
publicado, nomeado, nunca chamado de verde. CP-007: o CI agora INSTALA a
ferramenta (isolada, pinada) e a promete no env
(ESTUDIO_EXIGIR_AUDIO_SUITE=1) — promessa feita, ausencia vira VERMELHO
e derruba o build. Aqui se provam os DOIS contratos, e o resto: verde
com trilha dentro das ancoras, vermelho com trilha estourada, e as duas
formas de a declaracao divergir do real.

Quando a audio-suite nao esta na maquina, os casos de MEDIDA REAL se
anunciam como nao medidos — sem fingir verificacao que nao houve.
"""
import json
import os
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

    # --- sem audio-suite e SEM promessa: INDECISO e ponto (a maquina local)
    # (O job do CI roda com ESTUDIO_EXIGIR_AUDIO_SUITE=1 no env — este caso
    # simula a maquina de quem desenvolve, sem promessa no ar.)
    _filme(declara=True, com_trilha="boa")
    original = _sem_audio_suite()
    os.environ.pop("ESTUDIO_EXIGIR_AUDIO_SUITE", None)
    try:
        v = pipeline.portao_sonorizacao(FANTASMA)
        rel = json.loads((FILMES / FANTASMA / "relatorio.json").read_text(encoding="utf-8"))
        chk(v.estado == "indeciso" and not v.achados,
            f"audio-suite ausente sem promessa: INDECISO sem achado de reprovacao ({v.estado})")
        chk(rel.get("sonorizacao", {}).get("estado") == "indeciso",
            "o INDECISO e publicado no relatorio.json, nomeado como tal")
    finally:
        pipeline._tem_audio_suite = original

    # --- CP-007: com a promessa, ausencia e VERMELHO, publicado -----------
    _sem_audio_suite()
    os.environ["ESTUDIO_EXIGIR_AUDIO_SUITE"] = "1"
    try:
        v = pipeline.portao_sonorizacao(FANTASMA)
        rel = json.loads((FILMES / FANTASMA / "relatorio.json").read_text(encoding="utf-8"))
        chk(v.estado == "vermelho" and "ESTUDIO_EXIGIR_AUDIO_SUITE" in v.achados[0],
            f"audio-suite exigida e ausente: VERMELHO nomeando a promessa ({v.estado}, {v.achados})")
        chk(rel.get("sonorizacao", {}).get("estado") == "vermelho",
            "o VERMELHO da promessa quebrada e publicado no relatorio.json")
        # CP-008: a causa e estruturada -- o campo, nao a frase
        chk(v.causa == "promessa-quebrada",
            f"e a CAUSA do vermelho e 'promessa-quebrada' ({v.causa!r})")
        chk(rel.get("sonorizacao", {}).get("causa") == "promessa-quebrada",
            "a causa tambem e publicada no relatorio.json")
    finally:
        os.environ.pop("ESTUDIO_EXIGIR_AUDIO_SUITE", None)
        pipeline._tem_audio_suite = original

    # --- CP-008: FINDING simulado -> causa trilha-reprovada ---------------
    # Nada aqui toca a audio-suite de verdade: o subprocess e trocado por
    # um que devolve saida 1 com um FINDING -- o contrato exato do mapea-
    # mento. A causa tem de distinguir "reprovei a trilha" de "nao medi".
    import subprocess as _sp
    _run_real = _sp.run
    _tem_real = pipeline._tem_audio_suite
    pipeline._tem_audio_suite = lambda: True

    def _run_falso(cmd, **kw):
        if cmd[0] == "ffmpeg":            # o decode roda antes da medida
            return _sp.CompletedProcess(cmd, 0, "", "")
        finding = {"findings": [{
            "analyzer": "loudness", "metric": "integrated_loudness",
            "value": -10.0, "severity": "fail", "message": "acima da ancora"}]}
        return _sp.CompletedProcess(cmd, 1, json.dumps(finding), "")

    _sp.run = _run_falso
    try:
        _filme(declara=True, com_trilha="boa")
        v = pipeline.portao_sonorizacao(FANTASMA)
        chk(v.estado == "vermelho" and v.causa == "trilha-reprovada",
            f"FINDING da audio-suite: VERMELHO com causa 'trilha-reprovada' "
            f"({v.estado}, {v.causa!r})")
        chk(any("loudness" in a for a in v.achados),
            f"e o achado nomeia o analyzer que reprovou ({v.achados})")
        chk(v.causa != "promessa-quebrada",
            "trilha medida e reprovada NAO e promessa quebrada -- causas distintas")
    finally:
        _sp.run = _run_real
        pipeline._tem_audio_suite = _tem_real

    # --- CP-008: declaracao divergente tem causa propria -------------------
    _filme(declara=True, com_trilha=None)
    v = pipeline.portao_sonorizacao(FANTASMA)
    chk(v.estado == "vermelho" and v.causa == "declaracao-divergente",
        f"declara sem trilha: causa 'declaracao-divergente' ({v.causa!r})")

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

    # --- o passo de CI com a promessa: ausencia da ferramenta derruba ----
    # o build (CP-007). PATH sem o binario + ESTUDIO_EXIGIR_AUDIO_SUITE=1:
    # e o job do CI visto de costas, sem a instalacao da audio-suite.
    env_vermelho = {**os.environ, "PATH": "/usr/bin:/bin",
                    "ESTUDIO_EXIGIR_AUDIO_SUITE": "1"}
    r = subprocess.run([sys.executable, "ci/portao_sonorizacao.py"],
                       capture_output=True, text=True, cwd=RAIZ, env=env_vermelho)
    chk(r.returncode == 1,
        f"com a promessa e sem a ferramenta, o passo de CI sai 1 — exit {r.returncode}")
    chk("VERMELHO" in r.stdout,
        "e o passo NOMEIA o vermelho da promessa quebrada por filme")
    # CP-008: a frase final e a da causa -- promessa quebrada NAO diz
    # "trilha reprovada", porque nada foi medido.
    chk("PROMESSA QUEBRADA" in r.stderr and "nada foi medido" in r.stderr,
        f"a frase final e 'PROMESSA QUEBRADA ... nada foi medido' ({r.stderr.strip()[:80]!r})")
    chk("trilha reprovada" not in r.stderr,
        "e ela NAO diz 'trilha reprovada' — essa frase so existe com FINDING")

    # --- o passo de CI como o job o roda: verde ou indeciso documentado ----
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
    print("  ausencia da ferramenta sem promessa e INDECISO nomeado; com a "
          "promessa (CP-007), VERMELHO que derruba o build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
