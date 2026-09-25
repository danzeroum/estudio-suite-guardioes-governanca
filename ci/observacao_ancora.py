#!/usr/bin/env python3
"""A observação da âncora na classe avx2 (CP-013) — roda NO RUNNER.

CP-014 (25/09/2026): ESTE SCRIPT SAIU DO GATE. A diretiva do dono —
"medir o mesmo arquivo em toda cópia não traz informação" — tirou a
medição da âncora do workflow dublador inteira: a cópia avx2 do gate
sai cedo SEM audio-suite e SEM medir a âncora (33 cópias já tinham
medido valores idênticos entre si e iguais à medição local — a âncora
é independente de classe; a medição repetida não informava nada). A
observação de VERDADE, que INFORMA, compara o regenerado contra a
âncora, fala a fala, com build — e é o DISPATCH MANUAL `observar_avx2`
(.github/workflows/observar-avx2.yml, ci/observar_avx2.py). Este script
segue no repositório como INSTRUMENTO TESTADO (é dele que o
ci/observar_avx2.py importa o decodificador OGG-Opus via libsndfile, e
são dele as funções de medição da âncora isolada para qualquer uso
futuro ad-hoc) — instrumento é um só, código não se copia.

A decisão do dono (24/09/2026, saída (e)): "a prova decisiva é bytes do
PCM mixado em cópia AVX-512 visível; AVX2 é observação; sem amostra
decisiva é vermelho nomeado". A classe avx2 SAI DO GATE inteira — a
validação por descritores da CP-012 chocou no limite físico do ruído
(TETO_NAO_DISCRIMINA: o controle de +20 cents mede 2,02–2,87 Hz e o
ruído da frota move o F0 mediana em ~2,2 Hz por fala), e a resposta do
dono foi trocar a pergunta, não afrouxar o teto.

O que uma cópia avx2 pode MEDIR sem build: os descritores da ÂNCORA —
o PCM commitado decodificado no runner e medido fala a fala pelo MESMO
instrumento da CP-012 (audio-suite CLI, perfil
harness/perfis/guardioes-equivalencia.yaml + energia numpy). A medição
do REGENERADO exigiria build (piper só existe na imagem) e NÃO roda:
observação não paga o preço do build porque não é gate. O que esta
observação entrega: (1) a âncora descritiva publicada em toda execução
— o lado de referência de qualquer comparação futura, medido em
máquinas reais da frota; (2) o instrumento rodando (o pitch_f0 que
declara p10–p90 junto com a mediana — a fala 22/p10/elefante declara
132,9–478,2 Hz NA PRÓPRIA âncora: o instrumento se declara instável
nela, e é isso que a issue do audio-suite pergunta).

SEM GATE, SEM TETO, SEM CONTROLE: nada aqui reprova nada. A observação
é publicada (observacao.json + log no artefato de identidade), e a
FALHA da medição é publicada como status — não derruba a cópia, porque
a cópia avx2 termina NEUTRA por desenho (a classe dela não decide nada
no gate do agregador). A cópia só reprova se a CLASSIFICAÇÃO falhar —
classe é o veredito da cópia, e quem a declara é o classificador único
de estudio_suite/voz.py, não este passo.

Decodificação: o runner não tem ffmpeg (medido na CP-012 — FileNotFoundError
na cópia-4) — mas o .opus da trilha é um OGG-Opus, e o libsndfile
(mesma biblioteca que a audio-suite usa para WAV/OGG/FLAC) lê Ogg Opus
(medido). O PCM decodificado vira WAV pcm16 e os segmentos por fala
saem pelo [em, em+dur] do PRÓPRIO audio.json — o mesmo recorte da
equivalência da CP-012 (ci/equivalencia_descritores.py, importado aqui
por caminho: o instrumento é um só, as funções não são copiadas).

Saída: 0 SEMPRE (observação não reprova; a falha é status no json).
"""
import argparse
import importlib.util
import json
import sys
import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite.comum import FILMES, filmes_com_audio  # noqa: E402

# o instrumento é o da CP-012 — carregado por caminho (ci/ não é pacote),
# como os testes fazem: medir_segmento/extrair_segmento não ganham cópia
_spec = importlib.util.spec_from_file_location(
    "equivalencia_descritores", RAIZ / "ci" / "equivalencia_descritores.py")
eq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eq)


def decodificar_ancora(opus: Path, destino: Path) -> Path:
    """O .opus commitado da trilha -> WAV pcm16, no runner, sem ffmpeg.

    O libsndfile lê Ogg Opus (o container do .opus desta suíte — medido:
    sf.info devolve 'OGG' / 'OPUS', 48000 Hz); é a mesma biblioteca de
    leitura que a audio-suite usa. Mudança de FORMATO, não de conteúdo:
    os bytes do .opus não são tocados — isto é leitura, e a âncora segue
    sendo o HEAD.
    """
    import soundfile as sf
    pcm, sr = sf.read(str(opus), dtype="int16", always_2d=True)
    if pcm.shape[1] != 1:
        raise ValueError(f"{opus.name}: esperado mono, veio {pcm.shape[1]} canal(is)")
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sr))
        w.writeframes(np.ascontiguousarray(pcm[:, 0], dtype=np.int16).tobytes())
    return destino


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--saida", default="/tmp/identidade",
                    help="onde o observacao.json vai (default: /tmp/identidade)")
    ap.add_argument("--classe", default=None,
                    help="a classe do runner (default: variável CLASSE_DO_RUNNER)")
    args = ap.parse_args()
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    classe = args.classe or __import__("os").environ.get("CLASSE_DO_RUNNER", "?")

    print("== OBSERVAÇÃO DA ÂNCORA (CP-013, classe avx2 — sem build, sem gate)")
    print(f"   classe do runner: {classe}")
    print(f"   instrumento:      audio-suite (pin do workflow) + energia numpy,")
    print(f"                     as MESMAS funções da equivalência da CP-012")
    print("   o que isto NÃO é: não é gate, não reprova, não valida — é a")
    print("                     âncora descritiva publicada como observação")

    doc = {
        "prova": "observacao-ancora",
        "classe": classe,
        "gate": False,
        "filmes": [],
        "status": "ok",
        "nota": ("observação sem gate (CP-013, decisão (e)): a classe avx2 "
                 "não decide nada no agregador; os descritores da âncora são "
                 "publicados como referência medida — os deltas avx2 da "
                 "CP-012 seguem registrados na CP e na issue do audio-suite"),
    }
    import tempfile
    with tempfile.TemporaryDirectory(prefix="obs-") as td:
        tmp = Path(td)
        for fid in filmes_com_audio():
            try:
                base = FILMES / fid / "audio"
                mani = json.loads((base / "audio.json").read_text(encoding="utf-8"))
                clipes = mani.get("clipes", [])
                wav = decodificar_ancora(base / f"{fid}.opus",
                                         tmp / f"{fid}-ancora.wav")
                print(f"\n== {fid}: {len(clipes)} falas (âncora commitada)")
                falas = []
                maximos = {}
                for k, c in enumerate(clipes):
                    seg = eq.extrair_segmento(wav, c["em"], c["dur"],
                                              tmp / f"{fid}-{k}.wav")
                    m = eq.medir_segmento(seg)
                    falas.append({"fala": k, "plano": c["plano"],
                                  "voz": c["voz"], "ancora": m})
                    for chave, v in m.items():
                        maximos[chave] = max(maximos.get(chave, 0.0), abs(v))
                # mediana por voz — a estatística que a CP-010 propõe medir
                por_voz = {}
                for f in falas:
                    if "f0_hz" in f["ancora"]:
                        por_voz.setdefault(f["voz"], []).append(f["ancora"]["f0_hz"])
                vozes = {v: round(float(np.median(xs)), 2)
                         for v, xs in sorted(por_voz.items())}
                for v, med in vozes.items():
                    print(f"   F0 mediana da voz {v:10s}: {med:8.2f} Hz")
                for f in falas:
                    if abs(f["ancora"].get("f0_hz", 0)) >= 200 and f["voz"] == "elefante":
                        print(f"   (fala {f['fala']} {f['plano']}/{f['voz']}: "
                              f"F0 {f['ancora']['f0_hz']:.2f} Hz — a fala de "
                              f"timbre misto que motiva a issue do audio-suite)")
                doc["filmes"].append({
                    "filme": fid, "falas": falas, "f0_mediana_por_voz": vozes,
                })
                print(f"   falas medidas: {len(falas)}; âncora decodificada "
                      f"sem ffmpeg ({wav.name})")
            except Exception as e:
                doc["status"] = f"falhou:{fid}:{type(e).__name__}"
                print(f"   FALHOU a observação de {fid}: {type(e).__name__}: {e}"
                      f" — publicado no observacao.json; NÃO é gate")
                doc["filmes"].append({
                    "filme": fid, "erro": f"{type(e).__name__}: {e}",
                })

    (saida / "observacao.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n== observação publicada: {saida / 'observacao.json'} "
          f"(status: {doc['status']})")
    print("   (a cópia avx2 termina NEUTRA — classe publicada, observação "
          "publicada, nada julgado aqui)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
