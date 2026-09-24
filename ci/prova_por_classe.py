#!/usr/bin/env python3
"""A prova por classe do job dublador (CP-011) — roda DENTRO da imagem.

O que ela decide, com numeros e no log, para CADA execucao:

  classe do runner == classe da ancora  ->  PROVA DE BYTES: cada .opus
  regenerado (trilha e clipes de plano) byte-identico ao HEAD. Como era
  antes da CP-011 — a identidade continua sendo a prova onde a classe que
  assinou os bytes esta rodando.

  classe divergente E teto registrado   ->  PROVA DE TOLERANCIA:
  (i) duracoes identicas POR FALA (clipes do audio.json regenerado contra
  o commitado: plano, em, ate, dur, voz, texto), (ii) residuo de nulidade
  do PCM decodificado abaixo do teto (o teto vem do voz.lock, bloco
  tolerancia — maximo observado na frota + margem, abaixo de -60 dBFS),
  (iii) audio-suite compare sem regressao (essa parte roda NO RUNNER,
  fora da imagem, sobre os WAVs que esta prova decodifica e publica).

  classe divergente SEM teto           ->  PROVA DE BYTES (doutrina
  antiga): vermelho honesto na classe divergente com TODOS os numeros
  publicados. Tolerancia sem teto medido e registrado nao existe — seria
  afrouxar fiscal com palavra bonita. A fase de medicao da CP-011 roda
  EXATAMENTE aqui: as execucoes publicam o residuo nos DOIS pontos (mix
  pre-opus reconstruido e .opus decodificado) sem gate de tolerancia; o
  teto e derivado desses numeros e so entao registrado no lock.

Os DOIS pontos de residuo sao sempre medidos e publicados:
  - mix pre-opus regenerado x commitado DECODIFICADO: carrega o ruido de
    codec do lado commitado somado ao sinal — e o ponto que INFLA o
    residuo com o que nao e divergencia de classe;
  - regenerado DECODIFICADO x commitado DECODIFICADO: os dois lados
    passaram pelo MESMO codec — o ruido de codec e comum e o que sobra e
    o sinal divergente. E o ponto do teto (a justificativa completa, com
    os numeros de ambas as medicoes, mora na CP-011).

Verificacao separada de validacao (Andre Borges): o veredito carrega
maquina (via job), classe, prova aplicada e numeros — as duas provas
nunca se confundem no log.

Saidas: 0 veredito verde · 1 veredito vermelho (com causa e numeros) ·
2 nao consegui medir (nomeado — decode falhou, lock ilegivel, PCM sem
flags de classe).
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import voz                        # noqa: E402
from estudio_suite.comum import FILMES, filmes_com_audio  # noqa: E402


# ---- o residuo de nulidade (funcao pura, testada) --------------------------
def residuo_dbfs(pcm_a, pcm_b) -> float:
    """RMS da diferenca entre dois PCM int16, em dBFS (plena = 32768).

    PCM identicos -> -inf dBFS (e passa em qualquer teto: -inf <= teto).
    O residuo de nulidade e a pergunta "quanto SOBRA de diferenca quando
    a hipotese e que os dois sao o MESMO som": em dBFS, para que o teto
    diga se o que sobra esta abaixo do que um ouvido humano notaria.
    """
    a = np.asarray(pcm_a, dtype=np.int16)
    b = np.asarray(pcm_b, dtype=np.int16)
    n = min(len(a), len(b))
    r = a[:n].astype(np.float64) - b[:n].astype(np.float64)
    if len(r) == 0:
        return float("-inf")
    rms = float(np.sqrt(np.mean(r * r)))
    if rms == 0.0:
        return float("-inf")
    return 20.0 * math.log10(rms / 32768.0)


def fmt_dbfs(v: float) -> str:
    return "-inf" if v == float("-inf") else f"{v:.1f}"


def veredito_residuo(residuo: float, teto: float) -> tuple:
    """(ok, frase) — a frase sempre carrega o NUMERO, verde ou vermelho."""
    ok = residuo <= teto
    frase = (f"residuo {fmt_dbfs(residuo)} dBFS x teto {teto:g} dBFS "
             f"[{'OK' if ok else 'ACIMA DO TETO'}]")
    return ok, frase


# ---- leitura de PCM --------------------------------------------------------
def _ler_pcm_wav(caminho: Path) -> np.ndarray:
    with wave.open(str(caminho), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise SystemExit(f"ERRO: {caminho}: esperado mono pcm16")
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def _decodificar(opus: Path, saida: Path) -> Path:
    """opus -> wav pcm_s16le: mudanca de FORMATO, mesma duracao e taxa."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-v", "error", "-fflags", "+bitexact",
         "-i", str(opus), "-c:a", "pcm_s16le", "-f", "wav", str(saida)],
        capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise SystemExit(f"ERRO: nao decodifiquei {opus}:\n{r.stderr[-400:]}")
    return saida


# ---- duracoes por fala -----------------------------------------------------
_CHAVES_DE_FALA = ("plano", "em", "ate", "dur", "voz", "texto_sha256")


def comparar_duracoes(commitado: list, regenerado: list) -> list:
    """Divergencias de duracao POR FALA — a lista vazia e o verde.

    Compara as chaves que assinam cada fala no manifesto: plano, em, ate,
    dur (arredondado a 1 ms na gravacao), voz e o hash do texto. A duracao
    e o contrato da tolerancia entre classes: os BYTES divergem (kernel
    SIMD diferente), a FALA nao pode (a mesma legenda, o mesmo tempo de
    tela).
    """
    divergencias = []
    if len(commitado) != len(regenerado):
        divergencias.append(
            f"{len(commitado)} fala(s) no commitado x {len(regenerado)} no "
            f"regenerado — a dublagem nao cobre as mesmas falas")
    por_chave = {(c.get("plano"), c.get("em")): c for c in commitado}
    for c in regenerado:
        ref = por_chave.get((c.get("plano"), c.get("em")))
        if ref is None:
            divergencias.append(
                f"plano {c.get('plano')} em {c.get('em')}: fala sem "
                f"correspondente no commitado")
            continue
        for k in _CHAVES_DE_FALA:
            if ref.get(k) != c.get(k):
                divergencias.append(
                    f"plano {c.get('plano')} em {c.get('em')} ({c.get('voz')}): "
                    f"{k} commitado {ref.get(k)} x regenerado {c.get(k)}")
    return divergencias


# ---- a prova ----------------------------------------------------------------
def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--commitado", default="/commitado",
                    help="espelho do audio commitado (raiz do repositorio)")
    ap.add_argument("--saida", default="/prova",
                    help="onde o prova.json e os WAVs decodificados vao")
    args = ap.parse_args()
    commitado = Path(args.commitado)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    a = voz.ancora()
    classe_ancora = str(a["ambiente"].get("classe_simd", "")).strip()
    tol = voz.tolerancia()
    teto = None
    if "residuo_max_dbfs" in tol:
        teto = float(str(tol["residuo_max_dbfs"]).strip())
    classe_runner = voz.classe_simd_medida()

    # Qual prova roda — dito no LOG antes de qualquer numero, para o
    # leitor nunca confundir verificacao com validacao.
    if classe_runner == classe_ancora:
        prova = "bytes"
    elif teto is not None:
        prova = "tolerancia"
    else:
        prova = "bytes-sem-tolerancia-registrada"
    print(f"== PROVA POR CLASSE (CP-011)")
    print(f"   classe do runner:  {classe_runner} (flags medidas)")
    print(f"   classe da ancora:  {classe_ancora} (voz.lock)")
    print(f"   teto de residuo:   {fmt_dbfs(teto) if teto is not None else 'NAO REGISTRADO'} dBFS"
          + (f" (voz.lock, margem {tol.get('margem_db', '?')} dB, base {tol.get('base', '?')})"
             if teto is not None else " — sem teto nao existe tolerancia"))
    print(f"   PROVA APLICADA:    {prova}")

    filmes = list(filmes_com_audio())
    if not filmes:
        print("   nenhum filme declara audio — nada a provar (a prova por "
              "classe e a prova de QUEM FALA)")
        (saida / "prova.json").write_text(json.dumps(
            {"prova": prova, "classe": {"runner": classe_runner,
                                        "ancora": classe_ancora},
             "filmes": [], "veredito": "sem filmes com audio"}, indent=1) + "\n",
            encoding="utf-8")
        return 0

    relatorio, vermelho = [], []
    wavs_para_compare = []
    for fid in filmes:
        print(f"\n== {fid}")
        base_reg = FILMES / fid / "audio"
        base_com = commitado / "filmes" / fid / "audio"
        # (i) bytes — a VERIFICACAO: sempre medida, sempre publicada (nao
        # e gate na classe divergente COM teto, mas o numero nunca falta)
        divergentes = []
        for f in sorted(base_reg.glob("*.opus")):
            espelho = base_com / f.name
            if not espelho.exists():
                divergentes.append(f"{f.name}: sem espelho commitado")
            elif _sha256(f) != _sha256(espelho):
                divergentes.append(f.name)
        n_opus = len(list(base_reg.glob("*.opus")))
        print(f"   bytes: {n_opus - len(divergentes)}/{n_opus} .opus identicos"
              + (f" — DIVERGENTES: {', '.join(divergentes)}"
                 if divergentes else " (trilha + clipes de plano)"))

        # (ii) duracoes por fala — do manifesto regenerado contra o commitado
        try:
            mani_com = json.loads((base_com / "audio.json").read_text(encoding="utf-8"))
            mani_reg = json.loads((base_reg / "audio.json").read_text(encoding="utf-8"))
        except FileNotFoundError as e:
            print(f"   ERRO: manifesto ausente ({e}) — nao consegui medir")
            (saida / "prova.json").write_text(json.dumps(
                {"veredito": "NAO MEDIDO", "erro": str(e)}, indent=1) + "\n",
                encoding="utf-8")
            return 2
        div_dur = comparar_duracoes(mani_com.get("clipes", []),
                                    mani_reg.get("clipes", []))
        print(f"   duracoes por fala: "
              + ("identicas" if not div_dur
                 else f"{len(div_dur)} divergencia(s): " + "; ".join(div_dur[:4])))

        # (iii) residuo nos DOIS pontos, sempre medido e publicado
        wav_com = saida / f"{fid}-commitado.wav"
        wav_reg = saida / f"{fid}-regenerado.wav"
        _decodificar(base_com / f"{fid}.opus", wav_com)
        _decodificar(base_reg / f"{fid}.opus", wav_reg)
        pcm_com, pcm_reg = _ler_pcm_wav(wav_com), _ler_pcm_wav(wav_reg)
        res_opus = residuo_dbfs(pcm_com, pcm_reg)
        mix_wav = RAIZ / "workspace" / "voz-etapas" / f"{fid}.mix.wav"
        res_mix = None
        if mix_wav.exists():
            res_mix = residuo_dbfs(_ler_pcm_wav(mix_wav), pcm_com)
        print(f"   residuo opus decodificado x commitado decodificado: "
              f"{fmt_dbfs(res_opus)} dBFS"
              + (f" | mix pre-opus x commitado decodificado: {fmt_dbfs(res_mix)} dBFS"
                 f" (leva o ruido de codec do lado commitado — ponto de "
                 f"diagnostico, nao de teto)" if res_mix is not None else ""))
        if len(pcm_com) != len(pcm_reg):
            print(f"   ATENCAO: {len(pcm_com)} amostras no commitado x "
                  f"{len(pcm_reg)} no regenerado")
        wavs_para_compare += [str(wav_com), str(wav_reg)]

        # o veredito deste filme, pela prova que vale para a classe
        problema = None
        if prova == "bytes":
            if divergentes:
                problema = (f"{len(divergentes)}/{n_opus} .opus divergentes "
                            f"({', '.join(divergentes[:3])}) na classe da "
                            f"ancora — aqui a prova e BYTES")
        elif prova == "tolerancia":
            if div_dur:
                problema = f"duracoes por fala divergentes: {'; '.join(div_dur[:3])}"
            else:
                ok, frase = veredito_residuo(res_opus, teto)
                print(f"   {frase}")
                if not ok:
                    problema = frase
        else:  # bytes-sem-tolerancia-registrada
            if divergentes:
                problema = (f"{len(divergentes)}/{n_opus} .opus divergentes e "
                            f"tolerancia SEM teto registrado no lock — a "
                            f"tolerancia nasce da medicao destas execucoes "
                            f"(CP-011), nunca antes dela")
        if problema:
            vermelho.append(f"{fid}: {problema}")
            print(f"   VEREDITO DO FILME: VERMELHO — {problema}")
        else:
            print(f"   VEREDITO DO FILME: verde ({prova})")

        relatorio.append({
            "filme": fid,
            "bytes": {"identicos": not divergentes,
                      "divergentes": divergentes,
                      "total_opus": n_opus},
            "duracoes": {"ok": not div_dur, "divergencias": div_dur},
            "residuo_dbfs": {
                "opus_decodificado": (None if res_opus is None
                                      else (fmt_dbfs(res_opus) if res_opus == float("-inf")
                                            else round(res_opus, 2))),
                "mix_pre_opus": (None if res_mix is None
                                 else (fmt_dbfs(res_mix) if res_mix == float("-inf")
                                       else round(res_mix, 2))),
            },
            "amostras": {"commitado": len(pcm_com), "regenerado": len(pcm_reg)},
        })

    veredito = ("verde — " + prova if not vermelho
                else f"VERMELHO — {prova}: " + " | ".join(vermelho))
    doc = {
        "classe": {"runner": classe_runner, "ancora": classe_ancora,
                   "teto_dbfs": teto},
        "prova": prova,
        "filmes": relatorio,
        "wavs_para_compare": wavs_para_compare,
        "veredito": veredito,
    }
    (saida / "prova.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n== VEREDITO: {veredito}")
    print("   (o audio-suite compare roda no RUNNER sobre os WAVs publicados;"
          " o veredito final da execucao combina as duas provas)")
    return 1 if vermelho else 0


if __name__ == "__main__":
    sys.exit(main())
