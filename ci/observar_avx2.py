#!/usr/bin/env python3
"""A observação AVX2 de verdade (CP-014): deltas por fala, regenerado x
âncora — SEM GATE.

A diretiva do dono (25/09/2026): "medir o mesmo arquivo em toda cópia
não traz informação". A observação que ficava no gate media a ÂNCORA
commitada em toda cópia avx2 — a âncora é uma só (independente de
classe, medido na CP-013: 33 cópias, valores idênticos). A observação
que INFORMA compara o REGENERADO contra a âncora, fala a fala — e essa
exige build (piper só existe na imagem), por isso mora no DISPATCH
MANUAL `observar_avx2` (.github/workflows/observar-avx2.yml), disparado
quando se quer olhar, nunca em todo PR.

O que este script mede, POR FALA, em cada cópia avx2 que o dispatch
sortear: os QUATRO descritores da CP-012 (o MESMO instrumento — as
funções de ci/equivalencia_descritores.py, importadas por caminho como
os testes fazem; a audio-suite pinada com o perfil
harness/perfis/guardioes-equivalencia.yaml):

  duracao_ms    energia do primeiro ao último sample ativo (numpy)
  loudness_lu   loudness.integrated_loudness (BS.1770-4)
  f0_hz         pitch_f0.f0_median_hz (AS-DESC-008, YIN) — com o delta
                também em CENTS (1200·log2(reg/anc))
  centroide_hz  spectral_health.spectral_centroid

O RECORTE de cada lado sai do MANIFESTO DO PRÓPRIO LADO: o audio.json
commitado rege a âncora, o regenerado rege o regenerado — os slots [em,
em+dur] de uma síntese diferente podem divergir, e a divergência de slot
é DADO (publicada junto), não ruído a esconder. A pareação das falas é
por índice (fala k x fala k); manifestos com contagens diferentes são
registrados como achado do filme, e as falas do prefixo comum seguem
medidas.

CP-016 (proposta, 25/09/2026): o script REGISTRA TAMBÉM o sha256 do PCM
mixado de cada lado — o mix.pcm_f32_sha256 do audio.json REGENERADO (a
síntese avx2 DESTA cópia) e o da âncora commitada (a síntese avx512 que
o gate ancora) — o MESMO campo que o gate lê na classe avx512, aqui
como OBSERVAÇÃO: é o dado que alimenta a pergunta da CP-016 (a síntese
avx2 é byte-determinística entre modelos e execuções?). O modelo de CPU
da cópia vai no artefato (cpu) — a pergunta é ENTRE modelos. Sem gate,
sem teto, sem veredito: o número é publicado, a leitura é da CP.

SEM GATE, SEM TETO, SEM CONTROLE, SEM VERDE: nada aqui reprova, bloqueia
ou valida — o rotulo do artefato é "observação, sem gate" (a decisão (e)
da CP-013 segue intocada: o gate é SÓ bytes do PCM em cópia AVX-512). A
falha de medição é STATUS PUBLICADO (falhou:<motivo>); o script só
reprova (saída 2) quando não consegue escrever o artefato NENHUM — a
observação pedida que não observa é vermelho honesto, não verde mudo.

Saídas: 0 observação publicada (mesmo com falhas por filme no status) ·
2 nada foi observado — sem audio-suite, sem arquivos, sem artefato.
"""
import argparse
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite.comum import FILMES, filmes_com_audio  # noqa: E402

# o instrumento é o da CP-012 (ci/equivalencia_descritores.py) e o
# decodificador é o da CP-013 (ci/observacao_ancora.py) — importados por
# caminho, como os testes fazem: o instrumento é um só, nada é copiado
_spec_eq = importlib.util.spec_from_file_location(
    "equivalencia_descritores", RAIZ / "ci" / "equivalencia_descritores.py")
eq = importlib.util.module_from_spec(_spec_eq)
_spec_eq.loader.exec_module(eq)

_spec_obs = importlib.util.spec_from_file_location(
    "observacao_ancora", RAIZ / "ci" / "observacao_ancora.py")
obs = importlib.util.module_from_spec(_spec_obs)
_spec_obs.loader.exec_module(obs)


def _cents(f_reg: float, f_anc: float):
    """delta de F0 em cents — None se algum lado não mediu F0."""
    if not (f_reg and f_anc):
        return None
    return round(1200.0 * float(np.log2(f_reg / f_anc)), 2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--commitado", required=True,
                    help="diretório com a âncora (filmes/*/audio/*.opus e "
                         "audio.json COPIADOS ANTES da dublagem)")
    ap.add_argument("--saida", default="/tmp/observacao",
                    help="onde o observacao-avx2.json vai")
    args = ap.parse_args()
    commitado = Path(args.commitado)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    classe = os.environ.get("CLASSE_DO_RUNNER", "?")
    copia = os.environ.get("COPIA", "?")
    run_id = os.environ.get("RUN_ID", "?")

    print("== OBSERVAÇÃO AVX2 (CP-014 — dispatch manual, sem build de gate)")
    print(f"   cópia: {copia} | classe: {classe} | run: {run_id}")
    print("   o que isto NÃO é: não é gate, não reprova, não valida, não")
    print("   tem teto — o rótulo é 'observação, sem gate'")
    if not eq.tem_audio_suite():
        print("ERRO: sem audio-suite no PATH — o instrumento da observação "
              "não existe; nada observado (saída 2, nomeada)", file=sys.stderr)
        return 2

    doc = {
        "prova": "observacao-avx2",
        "rotulo": "observação, sem gate",
        "gate": False,
        "copia": copia,
        "classe": classe,
        "cpu": os.environ.get("CPU_MODELO", "ilegivel"),
        "run_id": run_id,
        "instrumento": ("audio-suite pinada (perfil guardioes-equivalencia) "
                        "+ energia numpy — as MESMAS funções da CP-012; "
                        "sha256 do PCM mixado por filme (CP-016, proposta)"),
        "filmes": [],
        "status": "ok",
    }
    algum_filme = False
    with tempfile.TemporaryDirectory(prefix="obs-avx2-") as td:
        tmp = Path(td)
        for fid in filmes_com_audio():
            try:
                base_com = commitado / "filmes" / fid / "audio"
                base_reg = FILMES / fid / "audio"
                for necessario in (base_com / f"{fid}.opus",
                                   base_com / "audio.json",
                                   base_reg / f"{fid}.opus",
                                   base_reg / "audio.json"):
                    if not necessario.exists():
                        raise FileNotFoundError(str(necessario))
                mani_com = json.loads(
                    (base_com / "audio.json").read_text(encoding="utf-8"))
                mani_reg = json.loads(
                    (base_reg / "audio.json").read_text(encoding="utf-8"))
                clipes_com = mani_com.get("clipes", [])
                clipes_reg = mani_reg.get("clipes", [])

                wav_com = obs.decodificar_ancora(
                    base_com / f"{fid}.opus", tmp / f"{fid}-ancora.wav")
                wav_reg = obs.decodificar_ancora(
                    base_reg / f"{fid}.opus", tmp / f"{fid}-regenerado.wav")

                achado_manifesto = None
                n_pares = min(len(clipes_com), len(clipes_reg))
                if len(clipes_com) != len(clipes_reg):
                    achado_manifesto = (
                        f"manifesto divergente: {len(clipes_com)} falas "
                        f"commitadas x {len(clipes_reg)} regeneradas — "
                        f"pareadas as {n_pares} do prefixo comum")

                falas = []
                for k in range(n_pares):
                    m_com = eq.medir_segmento(
                        eq.extrair_segmento(
                            wav_com, clipes_com[k]["em"],
                            clipes_com[k]["dur"],
                            tmp / f"{fid}-com-{k}.wav"))
                    m_reg = eq.medir_segmento(
                        eq.extrair_segmento(
                            wav_reg, clipes_reg[k]["em"],
                            clipes_reg[k]["dur"],
                            tmp / f"{fid}-reg-{k}.wav"))
                    delta = {}
                    for chave in ("duracao_ms", "loudness_lu",
                                  "f0_hz", "centroide_hz"):
                        if chave in m_com and chave in m_reg:
                            delta[chave] = round(
                                float(m_reg[chave]) - float(m_com[chave]), 2)
                    f = {
                        "fala": k,
                        "plano": clipes_com[k].get("plano"),
                        "voz": clipes_com[k].get("voz"),
                        "ancora": {c: m_com.get(c) for c in
                                   ("duracao_ms", "loudness_lu", "f0_hz",
                                    "centroide_hz")},
                        "regenerado": {c: m_reg.get(c) for c in
                                       ("duracao_ms", "loudness_lu", "f0_hz",
                                        "centroide_hz")},
                        "delta": delta,
                        "slot_ancora": {"em": clipes_com[k]["em"],
                                        "dur": clipes_com[k]["dur"]},
                        "slot_regenerado": {"em": clipes_reg[k]["em"],
                                            "dur": clipes_reg[k]["dur"]},
                    }
                    cents = _cents(m_reg.get("f0_hz"), m_com.get("f0_hz"))
                    if cents is not None:
                        f["delta"]["f0_cents"] = cents
                    falas.append(f)

                # máximos |delta| por descritor — o resumo honesto
                maximos = {}
                for chave in ("duracao_ms", "loudness_lu", "f0_hz",
                              "centroide_hz"):
                    vals = [abs(f["delta"][chave]) for f in falas
                            if chave in f.get("delta", {})]
                    maximos[chave] = round(max(vals), 2) if vals else None
                cents_vals = [abs(f["delta"]["f0_cents"]) for f in falas
                              if "f0_cents" in f.get("delta", {})]
                maximos["f0_cents"] = (round(max(cents_vals), 1)
                                       if cents_vals else None)

                filme_doc = {
                    "filme": fid, "falas": falas, "delta_maximo": maximos,
                }
                # CP-016 (proposta): o sha256 do PCM mixado de cada lado —
                # o MESMO campo que o gate lê (mix.pcm_f32_sha256), aqui
                # como observação. O regenerado é a síntese avx2 DESTA
                # cópia; a âncora é a commitada (classe avx512). Divergir
                # da âncora é o ESPERADO (a classe muda os kernels do
                # MLAS — CP-011); o que a CP-016 pergunta é se o
                # REGENERADO é igual entre cópias/modelos/execuções.
                try:
                    filme_doc["hash_pcm_mixado"] = {
                        "regenerado_avx2": str(
                            mani_reg.get("mix", {}).get("pcm_f32_sha256")
                            or "nao-registrado"),
                        "ancora_commitada": str(
                            mani_com.get("mix", {}).get("pcm_f32_sha256")
                            or "nao-registrado"),
                    }
                except Exception as e:
                    filme_doc["hash_pcm_mixado"] = {
                        "regenerado_avx2": f"falhou:{type(e).__name__}",
                        "ancora_commitada": f"falhou:{type(e).__name__}"}
                if achado_manifesto:
                    filme_doc["achado"] = achado_manifesto
                doc["filmes"].append(filme_doc)
                algum_filme = True
                print(f"\n== {fid}: {n_pares} falas pareadas"
                      + (f" — ACHADO: {achado_manifesto}"
                         if achado_manifesto else ""))
                for chave, val in maximos.items():
                    print(f"   delta máximo de {chave:14s}: {val}")
            except Exception as e:
                doc["status"] = f"falhou:{fid}:{type(e).__name__}"
                doc["filmes"].append({
                    "filme": fid, "erro": f"{type(e).__name__}: {e}"})
                print(f"   FALHOU a observação de {fid}: "
                      f"{type(e).__name__}: {e} — publicado, NÃO é gate")

    if not algum_filme:
        print("ERRO: nenhum filme observado — o artefato não nasce; "
              "vermelho honesto (saída 2)", file=sys.stderr)
        return 2

    (saida / "observacao-avx2.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(f"\n== observação publicada: "
          f"{saida / 'observacao-avx2.json'} (status: {doc['status']})")
    print("   rótulo: 'observação, sem gate' — nada disso reprova merge "
          "nenhum (a decisão (e) segue: o gate é bytes do PCM em AVX-512)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
