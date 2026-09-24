#!/usr/bin/env python3
"""A equivalencia por descritores da classe avx2 (CP-012) — roda NO RUNNER.

A decisao do dono (24/09/2026): "AVX2 por equivalencia de descritores com
controle positivo". O PCM da classe avx2 diverge no CRU (30/30 falas,
CP-011) e o null test nao e a pergunta certa — a nulidade nao e
audibilidade: diferencas numericas numa rede neural geram residuo alto
(-38 dBFS) em audio perceptualmente igual. A pergunta certa: OUTRA CPU
entrega o MESMO SOM? E som, para o mesmo filme, se a FALA e a mesma:
mesma duracao, mesmo nivel, mesma altura, mesma cor.

O que este passo faz, POR FALA, sobre os WAVs decodificados que a prova
da imagem publica (/tmp/prova/<fid>-commitado.wav e <fid>-regenerado.wav):

  DESCRITORES (a audio-suite e o motor de medida — CLI externa, pinada
  por SHA, codigo nunca copiado; o perfil mora em
  harness/perfis/guardioes-equivalencia.yaml):
    duracao_ms   energia medida pela suite (primeiro ao ultimo sample
                 ativo) — o recorte [em, em+dur] do audio.json
    loudness_lu  loudness.integrated_loudness (BS.1770-4)
    f0_hz        pitch_f0.f0_median_hz (AS-DESC-008: F0 mediana sobre
                 quadros vozeados, YIN)
    centroide_hz spectral_health.spectral_centroid

  JULGAMENTO: |delta| de cada descritor, fala a fala, contra os TETOS do
  voz.lock (bloco tolerancia, chaves descritores_*): maximo OBSERVADO na
  frota AVX2 contra a ancora + margem declarada, num lugar so. Sem os
  tetos, o passo RECUSA (saida 2, "lock incompleto") — mas mede e publica
  TUDO antes: e destes numeros que os tetos nascem (fase de medicao).

  CONTROLE POSITIVO (em toda execucao, toda classe): variantes
  deliberadas sobre o lado REGENERADO — +0,5 dB numa fala, +20 cents
  numa fala, uma fala TROCADA por outra do mesmo guardiao e 50 ms de
  corte — cada uma tem de REPROVAR nomeando o descritor que a pegou.
  Controle que passa e TETO_NAO_DISCRIMINA (saida 1, parada nomeada):
  teto que aceita a frota e nao enxerga mudanca real e tolerancia morta.

O veredito desta classe COMPLETA o da prova na imagem: la o PCM foi
declarado DIFERENTE (a classe avx2 nao entrega bytes iguais — e por isso
mesmo existe esta validacao por descritores), aqui se decide se o SOM e
equivalente. Verificacao separada de validacao (Andre Borges): cada
numero publicado carrega fala, descritor, valor dos dois lados e delta.

Saidas: 0 verde (equivalente por descritores, controles reprovando) ·
1 vermelho (delta acima do teto, ou TETO_NAO_DISCRIMINA — com numeros) ·
2 nao consegui medir (audio-suite ausente, WAVs ausentes, lock ilegivel).
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import voz                        # noqa: E402
from estudio_suite.comum import HARNESS              # noqa: E402

PERFIL = HARNESS / "perfis" / "guardioes-equivalencia.yaml"

# o mapa descritor -> (metrica da audio-suite, unidade, teto no lock).
# UMA fonte so para os tetos: o voz.lock (bloco tolerancia).
DESCRITORES = {
    "loudness_lu": ("loudness.integrated_loudness", "LU",
                    "descritores_loudness_lu_max"),
    "f0_hz": ("pitch_f0.f0_median_hz", "Hz",
              "descritores_f0_hz_max"),
    "centroide_hz": ("spectral_health.spectral_centroid", "Hz",
                     "descritores_centroide_hz_max"),
}
TETO_DURACAO = "descritores_duracao_ms_max"

# os controles positivos (CP-012): variacao, alvo e o descritor que tem
# de pegar cada um. A semente do +0,5 dB e fixa para o numero ser
# conferivel — o ganho e deterministico, mas o caminho fica declarado.
GANHO_DB_CONTROLE = 0.5
CENTS_CONTROLE = 20.0
CORTE_MS_CONTROLE = 50.0


# ---- o instrumento: a audio-suite (CLI externa) ----------------------------
def tem_audio_suite() -> bool:
    return shutil.which("audio-suite") is not None


def medir_audio_suite(wav: Path) -> dict:
    """{chave do DESCRITORES: valor} — as tres metricas, pela audio-suite."""
    r = subprocess.run(
        ["audio-suite", "analyze", str(wav), "--profile", str(PERFIL),
         "--format", "json"],
        capture_output=True, text=True, timeout=300)
    if r.returncode not in (0, 1):
        raise SystemExit(f"ERRO: audio-suite devolveu {r.returncode} medindo "
                         f"{wav.name}: {(r.stderr or r.stdout)[-300:]}")
    achados = json.loads(r.stdout or "{}")
    por_metrica = {f"{f.get('analyzer')}.{f.get('metric')}": f.get("value")
                   for f in achados.get("findings", [])}
    out = {}
    for chave, (metrica, _un, _t) in DESCRITORES.items():
        v = por_metrica.get(metrica)
        if v is not None:
            out[chave] = float(v)
    return out


# ---- extracao e duracao (numpy, sem scipy) ---------------------------------
def extrair_segmento(wav: Path, em: float, dur: float, destino: Path) -> Path:
    """O recorte [em, em+dur] do WAV decodificado — o mesmo para os dois
    lados, pela posicao que o PROPRIO audio.json gravou (a carteira de
    voz ja extrai assim; aqui a unidade e a FALA, nao o falante)."""
    with wave.open(str(wav), "rb") as w:
        sr = w.getframerate()
        w.setpos(int(round(em * sr)))
        pcm = w.readframes(int(round(dur * sr)))
    with wave.open(str(destino), "wb") as o:
        o.setnchannels(1)
        o.setsampwidth(2)
        o.setframerate(sr)
        o.writeframes(pcm)
    return destino


def ler_pcm(wav: Path) -> np.ndarray:
    with wave.open(str(wav), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def duracao_de_voz(pcm, sr: int) -> float:
    """Duracao em ms do primeiro ao ultimo sample ativo (energia).

    O recorte tem tamanho fixo (o slot da fala); o que a equivalencia
    pergunta e QUANTO DELE TEM FALA. Piso de |x| > 3 (int16, ~ -80 dBFS):
    abaixo disso e silencio digital. O corte de 50 ms e exatamente quem
    tem de mover este numero — o controle positivo o prova.
    """
    a = np.asarray(pcm, dtype=np.int16)
    ativos = np.flatnonzero(np.abs(a.astype(np.float64)) > 3.0)
    if len(ativos) == 0:
        return 0.0
    return float(ativos[-1] - ativos[0] + 1) / sr * 1000.0


def medir_segmento(wav: Path) -> dict:
    """Os QUATRO descritores de um segmento (audio-suite + energia)."""
    with wave.open(str(wav), "rb") as w:
        sr = w.getframerate()
    pcm = ler_pcm(wav)
    d = medir_audio_suite(wav)
    d["duracao_ms"] = round(duracao_de_voz(pcm, sr), 1)
    return d


# ---- as variantes dos controles (ffmpeg — o mesmo da cadeia) ---------------
def _ffmpeg_filtro(seg: Path, filtros: str, destino: Path) -> Path:
    r = subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-v", "error", "-fflags", "+bitexact",
         "-i", str(seg), "-af", filtros, "-ac", "1", "-ar", "48000",
         "-c:a", "pcm_s16le", "-fflags", "+bitexact", str(destino)],
        capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise SystemExit(f"ERRO: ffmpeg nao gerou a variante do controle "
                         f"({filtros}): {r.stderr[-300:]}")
    return destino


def variante_ganho(seg: Path, destino: Path) -> Path:
    """+0,5 dB na fala — o controle do teto de loudness."""
    return _ffmpeg_filtro(seg, f"volume={GANHO_DB_CONTROLE}dB", destino)


def variante_cents(seg: Path, destino: Path) -> Path:
    """+20 cents na fala, duracao preservada — o controle do teto de F0.

    asetrate sobe a altura (e acelera), aresample volta a taxa, atempo
    devolve o tempo: o que sobra e UM tom acima. O numero que tem de
    reprovar e o da F0 mediana (pitch_f0) — a duracao pode mexer poucos
    ms de borda, e o recorte segue comparavel.
    """
    f = 2.0 ** (CENTS_CONTROLE / 1200.0)
    return _ffmpeg_filtro(
        seg, f"asetrate=48000*{f:.6f},aresample=48000,"
             f"atempo={1.0 / f:.6f}", destino)


def variante_corte(seg: Path, destino: Path) -> Path:
    """50 ms cortados do FIM da fala — o controle do teto de duracao."""
    with wave.open(str(seg), "rb") as w:
        dur = w.getnframes() / w.getframerate()
    return _ffmpeg_filtro(seg, f"atrim=0:{max(0.0, dur - CORTE_MS_CONTROLE / 1000.0):.3f}",
                          destino)


# ---- o julgamento -----------------------------------------------------------
def ler_tetos(tol: dict) -> dict:
    """{descritor: teto} do lock — o que estiver registrado."""
    tetos = {}
    for chave, (_m, _u, k_teto) in DESCRITORES.items():
        if k_teto in tol:
            try:
                tetos[chave] = float(str(tol[k_teto]).strip())
            except ValueError:
                pass
    if TETO_DURACAO in tol:
        try:
            tetos["duracao_ms"] = float(str(tol[TETO_DURACAO]).strip())
        except ValueError:
            pass
    return tetos


def julgar(delta: float, teto: float) -> bool:
    return abs(delta) <= teto


def fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:+.2f}" if abs(v) < 1000 else f"{v:+.1f}"
    return str(v)


def _fala_para_controle(clipes: list, chave: str):
    """A fala alvo de um controle — deterministica: a primeira da lista."""
    if not clipes:
        return None
    if chave == "swap":
        # a fala trocada: a PRIMEIRA fala da voz mais frequente contra a
        # ULTIMA da mesma voz (duas falas do MESMO guardiao, textos
        # diferentes) — o cenario real de uma redublagem que posicionou
        # o clipe errado
        por_voz = {}
        for c in clipes:
            por_voz.setdefault(c["voz"], []).append(c)
        if not por_voz:
            return None
        voz_top = max(sorted(por_voz), key=lambda v: len(por_voz[v]))
        falas = por_voz[voz_top]
        if len(falas) < 2:
            return None
        return (falas[0], falas[-1], voz_top)
    return clipes[0 if chave in ("ganho",) else
                  (1 if chave == "cents" else
                   (min(2, len(clipes) - 1) if chave == "corte" else 0))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--prova", default="/tmp/prova",
                    help="dir da prova da imagem (prova.json e WAVs)")
    ap.add_argument("--commitado", default="/tmp/commitado",
                    help="espelho do audio commitado (manifestos)")
    ap.add_argument("--saida", default=None,
                    help="onde o descritores.json vai (default: --prova)")
    args = ap.parse_args()
    prova_dir = Path(args.prova)
    commitado = Path(args.commitado)
    saida = Path(args.saida) if args.saida else prova_dir

    prova = json.loads((prova_dir / "prova.json").read_text(encoding="utf-8"))
    classe = prova.get("classe", {}).get("runner", "?")
    tol = voz.tolerancia()
    tetos = ler_tetos(tol)
    todas_as_chaves = ("descritores_loudness_lu_max", "descritores_f0_hz_max",
                       "descritores_centroide_hz_max", TETO_DURACAO)
    faltam = sorted(set(todas_as_chaves) - set(tol))

    print("== EQUIVALENCIA POR DESCRITORES (CP-012, classe avx2 — no runner)")
    print(f"   classe do runner:  {classe} (prova da imagem)")
    print(f"   perfil:            {PERFIL.relative_to(RAIZ)}")
    print(f"   tetos registrados: {len(tetos)}/4"
          + ("" if tetos else " — NAO REGISTRADOS: a medida roda e publica,"
                              " o veredito nao fica verde por omissao"))
    for chave, teto in sorted(tetos.items()):
        print(f"     {chave:14s} <= {teto:g}")
    if not tem_audio_suite():
        print("   ERRO: audio-suite ausente no runner — a medida por "
              "descritores nao existe sem o instrumento (pinada por SHA "
              "no workflow)", file=sys.stderr)
        return 2

    recusa_lock = None
    if len(tetos) < 4:
        recusa_lock = (f"voz.lock sem os tetos de descritores — lock "
                       f"INCOMPLETO para a classe avx2 (faltam: "
                       f"{', '.join(faltam)}). Os deltas desta execucao "
                       f"saem publicados: o teto nasce da medicao da frota "
                       f"(CP-012, fase 2); sem ele, nao ha veredito verde")

    vermelho, controles_falhos = [], []
    relatorio = []
    import tempfile
    with tempfile.TemporaryDirectory(prefix="descritores-") as td:
        tmp = Path(td)
        pares = prova.get("wavs_para_compare", [])
        for i in range(0, len(pares), 2):
            # o prova.json publica NOMES; o diretorio e o do passo. (Se um
            # dia vier caminho absoluto que existe, tambem serve — o contrato
            # e o WAV certo, nao a casa dele.)
            def _resolve(w):
                w = Path(w)
                return w if w.exists() else (prova_dir / w.name)
            wav_com, wav_reg = _resolve(pares[i]), _resolve(pares[i + 1])
            fid = wav_com.name.replace("-commitado.wav", "")
            print(f"\n== {fid}")
            mani = commitado / "filmes" / fid / "audio" / "audio.json"
            clipes = json.loads(mani.read_text(encoding="utf-8"))["clipes"]
            medicoes = {"commitado": {}, "regenerado": {}}
            maximos = {}
            # (1) a medida: fala a fala, os dois lados
            for k, c in enumerate(clipes):
                seg_c = extrair_segmento(wav_com, c["em"], c["dur"],
                                         tmp / f"{fid}-{k}-com.wav")
                seg_r = extrair_segmento(wav_reg, c["em"], c["dur"],
                                         tmp / f"{fid}-{k}-reg.wav")
                m_c = medir_segmento(seg_c)
                m_r = medir_segmento(seg_r)
                medicoes["commitado"][k] = m_c
                medicoes["regenerado"][k] = m_r
                for chave in list(DESCRITORES) + ["duracao_ms"]:
                    if chave in m_c and chave in m_r:
                        d = m_r[chave] - m_c[chave]
                        maximos.setdefault(chave, 0.0)
                        maximos[chave] = max(maximos[chave], abs(d))
            # publica os maximos e o detalhe (fala a fala) no json
            print("   max |delta| por descritor (frota contra a ancora):")
            for chave in sorted(maximos):
                unidade = dict((k, u) for k, (_m, u, _t) in DESCRITORES.items()).get(
                    chave, "ms" if chave == "duracao_ms" else "")
                print(f"     {chave:14s} {maximos[chave]:+8.2f} {unidade}"
                      + (f"  x teto {tetos[chave]:g}" if chave in tetos else
                         "  (teto NAO registrado)"))
            detalhe = []
            for k in range(len(clipes)):
                m_c, m_r = medicoes["commitado"][k], medicoes["regenerado"][k]
                deltas = {chave: round(m_r[chave] - m_c[chave], 3)
                          for chave in m_c if chave in m_r}
                detalhe.append({"fala": k, "plano": clipes[k]["plano"],
                                "voz": clipes[k]["voz"],
                                "commitado": m_c, "regenerado": m_r,
                                "delta": deltas})

            # (2) o julgamento (so com teto registrado)
            if recusa_lock is None:
                acima = []
                for k in range(len(clipes)):
                    deltas = detalhe[k]["delta"]
                    for chave, delta in deltas.items():
                        if chave in tetos and not julgar(delta, tetos[chave]):
                            acima.append(
                                f"fala {k} ({clipes[k]['plano']}/"
                                f"{clipes[k]['voz']}): {chave} delta "
                                f"{delta:+.2f} x teto {tetos[chave]:g}")
                if acima:
                    vermelho.append(f"{fid}: " + "; ".join(acima[:4]))
                    print(f"   VERMELHO: {len(acima)} descritor(es) acima "
                          f"do teto — {'; '.join(acima[:3])}")
                else:
                    print("   equivalente por descritores: todos os deltas "
                          "sob os tetos, fala a fala")

            # (3) os CONTROLES POSITIVOS — em toda execucao
            print("   controles positivos (variacao deliberada tem de "
                  "REPROVAR):")
            controle_rel = []
            alvo_ganho = _fala_para_controle(clipes, "ganho")
            alvo_cents = _fala_para_controle(clipes, "cents")
            alvo_corte = _fala_para_controle(clipes, "corte")
            alvo_swap = _fala_para_controle(clipes, "swap")
            if alvo_ganho is not None:
                k = clipes.index(alvo_ganho)
                seg_r = extrair_segmento(wav_reg, alvo_ganho["em"],
                                         alvo_ganho["dur"],
                                         tmp / f"{fid}-ctl-ganho-in.wav")
                var = variante_ganho(seg_r, tmp / f"{fid}-ctl-ganho.wav")
                m_var = medir_segmento(var)
                m_com = medicoes["commitado"][k]
                delta = m_var["loudness_lu"] - m_com["loudness_lu"]
                teto = tetos.get("loudness_lu")
                pegou = (abs(delta) > teto) if teto is not None else None
                nome = f"+{GANHO_DB_CONTROLE:g} dB na fala {k} ({alvo_ganho['voz']})"
                julg = ("REPROVOU — pegou" if pegou else
                        ("NAO PEGOU" if pegou is not None else
                         "teto NAO registrado — medida publicada"))
                print(f"     {nome}: loudness delta {delta:+.2f} LU"
                      + (f" x teto {teto:g}" if teto is not None else "")
                      + f" [{julg}]")
                if pegou is False:
                    controles_falhos.append(f"{fid}: {nome} — loudness "
                                            f"delta {delta:+.2f} LU ficou "
                                            f"sob o teto")
                controle_rel.append({"controle": "ganho", "fala": k,
                                     "descritor": "loudness_lu",
                                     "delta": round(delta, 3), "pegou": pegou})
            if alvo_cents is not None:
                k = clipes.index(alvo_cents)
                seg_r = extrair_segmento(wav_reg, alvo_cents["em"],
                                         alvo_cents["dur"],
                                         tmp / f"{fid}-ctl-cents-in.wav")
                var = variante_cents(seg_r, tmp / f"{fid}-ctl-cents.wav")
                m_var = medir_segmento(var)
                m_com = medicoes["commitado"][k]
                delta = m_var["f0_hz"] - m_com["f0_hz"]
                teto = tetos.get("f0_hz")
                pegou = (abs(delta) > teto) if teto is not None else None
                nome = (f"+{CENTS_CONTROLE:g} cents na fala {k} "
                        f"({alvo_cents['voz']})")
                julg = ("REPROVOU — pegou" if pegou else
                        ("NAO PEGOU" if pegou is not None else
                         "teto NAO registrado — medida publicada"))
                print(f"     {nome}: f0 mediana delta {delta:+.2f} Hz"
                      + (f" x teto {teto:g}" if teto is not None else "")
                      + f" [{julg}]")
                if pegou is False:
                    controles_falhos.append(f"{fid}: {nome} — f0 delta "
                                            f"{delta:+.2f} Hz ficou sob o "
                                            f"teto")
                controle_rel.append({"controle": "cents", "fala": k,
                                     "descritor": "f0_hz",
                                     "delta": round(delta, 3), "pegou": pegou})
            if alvo_corte is not None:
                k = clipes.index(alvo_corte)
                seg_r = extrair_segmento(wav_reg, alvo_corte["em"],
                                         alvo_corte["dur"],
                                         tmp / f"{fid}-ctl-corte-in.wav")
                var = variante_corte(seg_r, tmp / f"{fid}-ctl-corte.wav")
                m_var = medir_segmento(var)
                m_com = medicoes["commitado"][k]
                delta = m_var["duracao_ms"] - m_com["duracao_ms"]
                teto = tetos.get("duracao_ms")
                pegou = (abs(delta) > teto) if teto is not None else None
                nome = (f"{CORTE_MS_CONTROLE:g} ms cortados da fala {k} "
                        f"({alvo_corte['voz']})")
                julg = ("REPROVOU — pegou" if pegou else
                        ("NAO PEGOU" if pegou is not None else
                         "teto NAO registrado — medida publicada"))
                print(f"     {nome}: duracao delta {delta:+.1f} ms"
                      + (f" x teto {teto:g}" if teto is not None else "")
                      + f" [{julg}]")
                if pegou is False:
                    controles_falhos.append(f"{fid}: {nome} — duracao delta "
                                            f"{delta:+.1f} ms ficou sob o "
                                            f"teto")
                controle_rel.append({"controle": "corte", "fala": k,
                                     "descritor": "duracao_ms",
                                     "delta": round(delta, 1), "pegou": pegou})
            if alvo_swap is not None:
                alvo, outra, voz_swap = alvo_swap
                k, j = clipes.index(alvo), clipes.index(outra)
                # a fala TROCADA: o clipe da OUTRA fala posicionado no
                # lugar desta — medidas da outra fala contra as do alvo
                m_com_alvo = medicoes["commitado"][k]
                m_var = medicoes["regenerado"][j]
                nome = (f"fala {k} trocada pela {j} (guardiao "
                        f"{voz_swap})")
                pegues, medidas_swap = [], []
                for chave in list(DESCRITORES) + ["duracao_ms"]:
                    if chave not in m_var or chave not in m_com_alvo:
                        continue
                    delta = m_var[chave] - m_com_alvo[chave]
                    medidas_swap.append(f"{chave} {delta:+.2f}")
                    if chave in tetos and abs(delta) > tetos[chave]:
                        pegues.append(f"{chave} {delta:+.2f} "
                                      f"(teto {tetos[chave]:g})")
                pegou = bool(pegues) if tetos else None
                julg = ("REPROVOU — pegou" if pegou else
                        ("NAO PEGOU" if pegou is not None else
                         "teto NAO registrado — medidas publicadas"))
                print(f"     {nome}: deltas {', '.join(medidas_swap)}"
                      + ("; ACIMA DOS TETOS: " + ", ".join(pegues) if pegues
                         else ("; nenhum acima dos tetos" if tetos else ""))
                      + f" [{julg}]")
                if pegou is False:
                    controles_falhos.append(f"{fid}: {nome} — nenhum "
                                            f"descritor passou do teto: os "
                                            f"tetos nao discriminam a "
                                            f"troca de conteudo")
                controle_rel.append({"controle": "swap",
                                     "fala": k, "por": j,
                                     "descritores": pegues, "pegou": pegou})
            elif alvo_swap is None:
                print("     (fala trocada: sem par do mesmo guardiao neste "
                      "filme — controle nao aplicavel)")
                controle_rel.append({"controle": "swap",
                                     "nota": "sem par do mesmo guardiao"})

            relatorio.append({
                "filme": fid,
                "max_abs_delta": {k: round(v, 3) for k, v in sorted(maximos.items())},
                "tetos": {k: tetos.get(k) for k in sorted(
                    list(DESCRITORES) + ["duracao_ms"])},
                "detalhe_por_fala": detalhe,
                "controles": controle_rel,
            })

    veredito = []
    if vermelho:
        veredito.append("VERMELHO — " + " | ".join(vermelho))
    if controles_falhos:
        veredito.append("TETO_NAO_DISCRIMINA — " + " | ".join(controles_falhos))
    if recusa_lock:
        veredito.append("RECUSA (lock incompleto): " + recusa_lock)
    if not veredito:
        veredito.append("verde — equivalente por descritores, controles "
                        "positivos reprovando")

    doc = {
        "classe": classe,
        "prova": "descritores-por-fala",
        "tetos": {k: v for k, v in sorted(tetos.items())},
        "filmes": relatorio,
        "veredito": " | ".join(veredito),
    }
    (saida / "descritores.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n== VEREDITO: {' | '.join(veredito)}")
    if recusa_lock:
        return 2
    if vermelho or controles_falhos:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
