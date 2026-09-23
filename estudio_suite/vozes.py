"""A carteira de voz: cada falante medido contra a propria baseline (CP-005).

Backlog D da CP-004, agora com razao de existir: desde a CP-005 as vozes
tem TIMBRE, e o revisor precisa ver -- por falante -- o que a portadora
animal fez com a voz sintetica. A unidade de medida e o FALANTE (o rotulo
do audio.json): os clipes de cada voz sao extraidos da trilha, concatenados
e medidos pela audio-suite com o perfil guardioes-vozes (descritores:
deriva de F0, silabas por segundo, centroide).

A baseline mora em filmes/<id>/baseline/vozes/<voz>.wav -- mesmo espirito
da baseline visual de palco: referencia que so muda por decisao (diff no
PR), nunca sozinha. Primeira medicao GRAVA a baseline; as seguintes
comparam. Como a cadeia inteira e byte-deterministica, descritor que
divergiu entre baseline e dublagem atual significa que alguma entrada
mudou -- e isso e needs_review (INDECISO), nunca VERMELHO: descritor nao
reprova (regra R1 da audio-suite), e "medida diferente" nao e "medida
errada".

A audio-suite e CLI externa (codigo dela nunca e copiado). Sem o binario,
a carteira NAO consegue medir: INDECISO nomeado, exit 2 -- o mesmo contrato
do portao de sonorizacao. EXCECAO (CP-007): quando o ambiente PROMETE a
ferramenta (ESTUDIO_EXIGIR_AUDIO_SUITE=1, o job do CI), a ausencia vira
VERMELHO, exit 1 -- promessa quebrada e divida de infraestrutura, nao
julgamento de descritor: o R1 continua valendo para o que se mediu.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .comum import ErroDeDados, FILMES, HARNESS, RAIZ, dados_do_filme

PERFIL = HARNESS / "perfis" / "guardioes-vozes.yaml"
DESCRITORES = ("pitch_stab.pitch_drift_cents",
               "speech_rate.syllables_per_second",
               "spectral_health.spectral_centroid")
TAXA, CANAIS = 48000, 1


def _tem_audio_suite() -> bool:
    return shutil.which("audio-suite") is not None


def _exige_audio_suite() -> bool:
    """O ambiente prometeu a ferramenta (CP-007): o job do CI promete."""
    return os.environ.get("ESTUDIO_EXIGIR_AUDIO_SUITE") == "1"


def _voz_arquivo(voz: str) -> str:
    """rotulo do audio.json -> nome de arquivo da baseline."""
    return voz.replace("/", "-") + ".wav"


def _extrair(opus: Path, clipes: list, destino: Path) -> None:
    """Os clipes de um falante, extraidos da trilha e concatenados.

    A posicao e duracao vem do audio.json (o manifesto da dublagem): a
    carteira nao inventa corte, le o que o dublar gravou. Deterministico.
    """
    partes, filtros, rotulos = [], [], []
    for i, c in enumerate(clipes):
        partes += ["-ss", str(c["em"]), "-t", f"{c['dur'] + 0.05:.3f}",
                   "-i", str(opus)]
        filtros.append(f"[{i}:a]atrim=0:{c['dur']:.3f},asetpts=N/SR/TB[a{i}]")
        rotulos.append(f"[a{i}]")
    filtros.append("".join(rotulos) +
                   f"concat=n={len(clipes)}:v=0:a=1,aresample={TAXA}[out]")
    r = subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-v", "error", "-fflags", "+bitexact"] +
        partes + ["-filter_complex", ";".join(filtros), "-map", "[out]",
                  "-ar", str(TAXA), "-ac", str(CANAIS),
                  "-c:a", "pcm_s16le", "-fflags", "+bitexact", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise ErroDeDados(f"nao consegui extrair os clipes da trilha: "
                          f"{r.stderr[-300:]}")


def _medir(wav: Path) -> dict:
    """{metrica: valor} os tres descritores, pela audio-suite (CLI externa)."""
    r = subprocess.run(
        ["audio-suite", "analyze", str(wav), "--profile", str(PERFIL),
         "--format", "json"],
        capture_output=True, text=True, timeout=300)
    if r.returncode not in (0, 1):
        raise ErroDeDados(f"audio-suite devolveu {r.returncode} medindo "
                          f"{wav.name}: {(r.stderr or r.stdout)[-200:]}")
    achados = json.loads(r.stdout or "{}")
    medido = {}
    for f in achados.get("findings", []):
        chave = f"{f.get('analyzer')}.{f.get('metric')}"
        if chave in DESCRITORES and f.get("value") is not None:
            medido[chave] = f["value"]
    return medido


def _publicar(fid: str, estado: str, por_voz: dict, nota: str) -> None:
    """A carteira vira evidencia no relatorio.json (chave propria, preservada)."""
    import datetime
    rel = FILMES / fid / "relatorio.json"
    d = {}
    if rel.exists():
        try:
            d = json.loads(rel.read_text(encoding="utf-8"))
        except Exception:
            d = {}
    d["alvo"] = fid
    d["vozes"] = {"estado": estado, "por_falante": por_voz, "nota": nota,
                  "quando": datetime.datetime.now(datetime.timezone.utc)
                            .isoformat(timespec="seconds")}
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True)
                   + "\n", encoding="utf-8")


def compare(fid: str, gravar: bool = False) -> int:
    """A carteira de um filme: gravar baselines ou medir contra elas.

    Saidas: 0 baselines gravadas ou tudo em linha com a baseline ·
    2 needs_review/INDECISO (descritor divergiu, ou audio-suite ausente
    sem promessa). Descritor NUNCA reprova (R1) -- a carteira aponta, o
    humano decide. A unica saida 1 e a da CP-007: audio-suite exigida
    (ESTUDIO_EXIGIR_AUDIO_SUITE=1) e ausente -- promessa quebrada do
    AMBIENTE, nao veredito sobre a voz.
    """
    dir_audio = FILMES / fid / "audio"
    manifesto = dir_audio / "audio.json"
    opus = dir_audio / f"{fid}.opus"
    if not manifesto.exists() or not opus.exists():
        print(f"  {fid}: sem dublagem versionada — a carteira mede o que existe")
        return 0
    if not PERFIL.exists():
        print(f"  INDECISO: falta o perfil {PERFIL.relative_to(RAIZ)}")
        return 2
    if not _tem_audio_suite() and _exige_audio_suite():
        # CP-007: a promessa mudou o contrato. Sem ela, ausencia e INDECISO
        # nomeado; com ela, o ambiente mentiu sobre a propria infraestrutura
        # -- e carteira sem medida em quem prometeu medir e VERMELHO.
        _publicar(fid, "vermelho", {},
                  "audio-suite exigida (ESTUDIO_EXIGIR_AUDIO_SUITE=1) e ausente")
        print("  VERMELHO: audio-suite exigida (ESTUDIO_EXIGIR_AUDIO_SUITE=1) "
              "e ausente — o ambiente prometeu medir; carteira sem medida "
              "aqui e divida de infraestrutura, nao INDECISO.")
        return 1

    d = dados_do_filme(fid)
    m = json.loads(manifesto.read_text(encoding="utf-8"))
    por_voz = {}
    for c in m.get("clipes", []):
        por_voz.setdefault(c["voz"], []).append(c)

    base_dir = FILMES / fid / "baseline" / "vozes"
    if gravar:
        base_dir.mkdir(parents=True, exist_ok=True)
    tem_suite = _tem_audio_suite()

    gravadas, verdes, revisionar = [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for voz in sorted(por_voz):
            clipes = por_voz[voz]
            candidato = tmp / _voz_arquivo(voz)
            _extrair(opus, clipes, candidato)
            baseline = base_dir / _voz_arquivo(voz)
            if gravar or not baseline.exists():
                # A referencia se grava MESMO sem audio-suite: extrair e
                # posicionar e trabalho do ffmpeg, e a baseline sem medida
                # continua sendo a ancora da proxima comparacao.
                base_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidato, baseline)
                gravadas.append(voz)
                if tem_suite:
                    medido = _medir(baseline)
                    print(f"  gravada   {voz}: baseline com {len(clipes)} clipe(s)"
                          + (" · " + ", ".join(f"{k.split('.')[-1]}={v}"
                                                for k, v in sorted(medido.items()))
                             if medido else ""))
                else:
                    print(f"  gravada   {voz}: baseline com {len(clipes)} clipe(s) — "
                          f"SEM medida (audio-suite ausente)")
                continue
            if not tem_suite:
                print(f"  INDECISO  {voz}: audio-suite ausente — "
                      f"{len(clipes)} clipe(s) sem medida")
                continue
            base, atual = _medir(baseline), _medir(candidato)
            deltas = {k: round(float(atual.get(k, 0)) - float(base.get(k, 0)), 6)
                      for k in DESCRITORES if k in base and k in atual}
            divergiu = [k for k, v in deltas.items() if v != 0]
            if divergiu:
                revisionar.append(voz)
                print(f"  REVIEW    {voz}: " + ", ".join(
                    f"{k.split('.')[-1]} {base.get(k)} -> {atual.get(k)} "
                    f"(delta {deltas[k]:+g})" for k in sorted(divergiu)))
            else:
                verdes.append(voz)
                print(f"  em linha  {voz}: " + ", ".join(
                    f"{k.split('.')[-1]}={atual.get(k)}" for k in sorted(deltas)))

    if not tem_suite:
        # Gravou referencias, talvez -- mas carteira sem medida e carteira
        # NAO medida: INDECISO nomeado, nunca verde por omisso.
        estado = "indeciso"
        nota = ("audio-suite ausente — carteira NAO medida"
                + (f"; {len(gravadas)} baseline(s) gravada(s) como referencia"
                   if gravadas else ""))
    elif gravadas and not (verdes or revisionar):
        estado, nota = "verde", "baselines gravadas — primeira medicao da carteira"
    elif revisionar:
        estado = "indeciso"
        nota = ("descritor divergiu da baseline em " + ", ".join(sorted(revisionar))
                + " — needs_review: a cadeia e deterministica, divergencia "
                  "significa entrada que mudou (redublagem sem regravar "
                  "baseline? rode com --gravar e explique no PR)")
    else:
        estado, nota = "verde", "todas as vozes em linha com as baselines"
    _publicar(fid, estado, {"gravadas": gravadas, "em_linha": verdes,
                            "needs_review": revisionar}, nota)
    print(f"\n  {len(gravadas)} baseline(s) gravada(s), {len(verdes)} em linha, "
          f"{len(revisionar)} em review — {estado}.")
    return 0 if estado == "verde" else 2


def main(argv=None) -> int:
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] != "compare" or len(argv) < 2:
        print("uso: vozes compare <id-do-filme> [--gravar]", file=sys.stderr)
        return 64
    return compare(argv[1], gravar="--gravar" in argv)


if __name__ == "__main__":
    import sys
    sys.exit(main())
