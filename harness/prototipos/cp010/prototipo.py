"""Protótipo da CP-010 — pitch por guardião, medido.

NÃO é o dublar. Sintetiza sozinho, fora de filmes/, e nunca escreve em
filmes/*/audio: tudo que gera mora em workspace/cp010/ (gitignored, regerável).

Cadeia medida, na ordem da CP-006 (fala -> piper -> PROSÓDIA -> timbre):

    texto -> piper (ritmo do rig, noise 0, como o dublar)
          -> deslocamento de F0 (o que a CP-010 propõe; 3 técnicas)
          -> timbre do rig (estudio_suite.timbre.aplicar, importado só p/ leitura)
          -> F0 medida pelo descritor pitch_f0 da audio-suite (S1, AS-DESC-008)

Técnicas comparadas:
  - world : pyworld (WORLD: harvest + cheaptrick + d4c; F0 × razão; ressíntese)
  - psola : TD-PSOLA em numpy/scipy, marcas de pitch pela F0 do próprio YIN
  - modelo: trocar o modelo piper (outros pt_BR do piper-voices), sem DSP

Uso (do zero, venv ISOLADO — nunca o do estúdio):
    python3 -m venv /tmp/venv-cp010
    /tmp/venv-cp010/bin/pip install -r harness/prototipos/cp010/requisitos.txt
    /tmp/venv-cp010/bin/python harness/prototipos/cp010/prototipo.py

Saídas: workspace/cp010/resultado.json (+ .md) e as amostras .wav
regeráveis em workspace/cp010/amostras/. Nada disso é commitado.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.request
import wave
from pathlib import Path

import numpy as np
import yaml
from scipy.signal import resample_poly

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from estudio_suite import fala  # noqa: E402  (leitura: normalizador de fala)
from estudio_suite import timbre as _tim  # noqa: E402  (leitura: o vocoder da CP-005)
from estudio_suite.dublar import _length_scale, voz_do_rig  # noqa: E402  (leitura)

TAXA = 22050  # o piper sintetiza em 22050
WORKSPACE = RAIZ / "workspace" / "cp010"
AQUI = Path(__file__).resolve().parent

# Mesmas três frases para todos: a comparação isola a VOZ, não o texto.
# Frases neutras, sem afirmação sobre a lei (nada aqui vai para legenda).
FRASES = [
    "Eu cuido para que cada dado siga o caminho certo.",
    "Antes de decidir, a gente olha com calma o que foi pedido.",
    "Quando algo muda, todo mundo precisa saber o motivo.",
]

# Os falantes dos filmes publicados (rótulos da carteira de voz).
FALANTES = {
    "aguia": {"rig": "aguia"},
    "coruja": {"rig": "coruja"},
    "elefante": {"rig": "elefante"},
    "narrador": {"rig": None},
    "raposa": {"rig": "raposa"},
    "tartaruga": {"rig": "tartaruga"},
}

MODELOS_EXTRA = {
    "pt_BR-edresson-low": "edresson/low",
    "pt_BR-jeff-medium": "jeff/medium",
    "pt_BR-cadu-medium": "cadu/medium",
}
BASE_HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR"


# ---- utilidades --------------------------------------------------------------
def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _baixar(url: str, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "estudio-suite-cp010"})
    with urllib.request.urlopen(req, timeout=120) as r, open(destino, "wb") as f:
        f.write(r.read())


def _gravar_wav(caminho: Path, x: np.ndarray, taxa: int = TAXA) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.round(np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(pcm.tobytes())


def _pcm_para_float(pcm: bytes) -> np.ndarray:
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float64) / 32768.0


def _float_para_pcm(x: np.ndarray) -> bytes:
    return np.round(np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()


# ---- âncoras: modelo (voz.lock) e portadoras (amostras.lock) ---------------
def modelo_travado() -> Path:
    """O modelo do voz.lock, baixado para workspace/ e conferido por sha256."""
    lock = yaml.safe_load((RAIZ / "voz.lock").read_text(encoding="utf-8"))
    destino = WORKSPACE / "modelos"
    for nome, a in lock["arquivos"].items():
        f = destino / nome
        if not f.exists() or _sha256(f) != a["sha256"]:
            _baixar(f"{lock['modelo']['origem']}/{nome}", f)
        if _sha256(f) != a["sha256"]:
            raise SystemExit(f"{nome}: sha diverge do voz.lock — não sintetizo com modelo não ancorado")
    return destino / f"{lock['modelo']['nome']}.onnx"


def modelo_extra(nome: str, caminho_hf: str) -> tuple[Path, str]:
    """Modelo alternativo (não ancorado — é justamente o que a alternativa C mudaria)."""
    destino = WORKSPACE / "modelos"
    for suf in (".onnx", ".onnx.json"):
        f = destino / f"{nome}{suf}"
        if not f.exists():
            _baixar(f"{BASE_HF}/{caminho_hf}/{nome}{suf}", f)
    f = destino / f"{nome}.onnx"
    return f, _sha256(f)


def portadoras() -> dict[str, Path]:
    """Portadoras do amostras.lock -> wav 48 kHz mono pcm16 em workspace/.

    O estúdio normaliza com ffmpeg; aqui o mp3 (conferido pelo MESMO sha do
    lock) é decodificado por libsndfile e reamostrado por resample_poly. Os
    bytes do .wav podem diferir do caminho do estúdio (decodificador outro);
    para medir F0 isso é irrelevante, e fica declarado no resultado.
    """
    import soundfile as sf

    lock = yaml.safe_load((RAIZ / "amostras.lock").read_text(encoding="utf-8"))
    saida = {}
    for aid, a in lock["amostras"].items():
        if not str(a.get("url", "")).startswith("http"):
            continue
        mp3 = WORKSPACE / "portadoras" / f"{aid}.mp3"
        wav = WORKSPACE / "portadoras" / f"{aid}.wav"
        if not mp3.exists() or _sha256(mp3) != a["sha256"]:
            _baixar(a["url"], mp3)
        if _sha256(mp3) != a["sha256"]:
            raise SystemExit(f"{aid}: sha diverge do amostras.lock — não uso portadora não ancorada")
        if not wav.exists():
            x, taxa = sf.read(str(mp3), always_2d=True)
            x = x.mean(axis=1)
            g = math.gcd(48000, taxa)
            _gravar_wav(wav, resample_poly(x, 48000 // g, taxa // g), 48000)
        saida[aid] = wav
    return saida


# ---- síntese (a mesma configuração do dublar) -------------------------------
def carregar_voz(onnx: Path):
    from piper import PiperVoice

    return PiperVoice.load(str(onnx))


def sintetizar(voz, texto: str, ritmo: float) -> bytes:
    from piper import SynthesisConfig

    cfg = SynthesisConfig(length_scale=_length_scale(ritmo), noise_scale=0.0, noise_w_scale=0.0)
    return b"".join(c.audio_int16_bytes for c in voz.synthesize(fala.normalizar(texto), cfg))


# ---- medida (descritor de S1) ------------------------------------------------
def medir(x: np.ndarray, taxa: int = TAXA) -> dict:
    from audio_suite.analyzers import all_analyzers
    from audio_suite.models import PCM

    f = all_analyzers()["pitch_f0"].analyze(PCM(samples=x.astype(np.float32), sample_rate=taxa), {})[0]
    e = f.evidence
    return {
        "status": f.status.value,
        "f0_mediana_hz": f.value,
        "p25_hz": e.get("f0_p25_hz"),
        "p75_hz": e.get("f0_p75_hz"),
        "iqr_st": round(12 * math.log2(e["f0_p75_hz"] / e["f0_p25_hz"]), 3) if f.value else None,
        "fracao_vozeada": e.get("voiced_fraction"),
    }


# ---- técnica A: WORLD --------------------------------------------------------
def deslocar_world(x: np.ndarray, semitons: float, taxa: int = TAXA) -> np.ndarray:
    import pyworld as pw

    if semitons == 0:
        return x
    f0, t = pw.harvest(x, taxa)
    sp = pw.cheaptrick(x, f0, t, taxa)
    ap = pw.d4c(x, f0, t, taxa)
    y = pw.synthesize(f0 * 2 ** (semitons / 12), sp, ap, taxa)
    y = y[: len(x)] if len(y) >= len(x) else np.pad(y, (0, len(x) - len(y)))
    return y


# ---- técnica B: TD-PSOLA (numpy/scipy) ----------------------------------------
def deslocar_psola(x: np.ndarray, semitons: float, taxa: int = TAXA) -> np.ndarray:
    """TD-PSOLA: marcas de análise a cada período (F0 do YIN), marcas de
    síntese com período / razão, segmento Hann de 2 períodos da marca de
    análise mais próxima somado na marca de síntese. Duração preservada;
    trechos não vozeados passam com espaçamento fixo (10 ms) inalterado.
    """
    from audio_suite.analyzers.pitch_f0 import rastrear_f0

    if semitons == 0:
        return x
    razao = 2 ** (semitons / 12)
    f0, _ = rastrear_f0(x, taxa, fmin=60.0, fmax=500.0)
    hop = int(round(taxa * 0.010))
    meio_quadro = int(round(taxa * 0.040)) // 2  # o quadro i do YIN é centrado em i*hop + janela/2

    def periodo_em(n: int) -> float | None:
        i = int(round((n - meio_quadro) / hop))
        i = min(max(i, 0), len(f0) - 1) if len(f0) else -1
        return taxa / f0[i] if i >= 0 and np.isfinite(f0[i]) else None

    # marcas de análise: no pico POSITIVO dentro de ±P/2 do passo previsto
    # (polaridade fixa; |x| alternaria entre picos + e −, meio período de jitter)
    marcas, n = [], 0
    while n < len(x):
        p = periodo_em(n)
        if p is None:
            marcas.append((n, None))
            n += hop
            continue
        a, b = max(0, int(n - p / 2)), min(len(x), int(n + p / 2) + 1)
        pico = a + int(np.argmax(x[a:b])) if b > a else n
        pico = max(pico, marcas[-1][0] + 1) if marcas else pico
        marcas.append((pico, p))
        n = int(pico + p)
    pos = np.array([m[0] for m in marcas])

    y = np.zeros(len(x))
    peso = np.zeros(len(x))
    t = 0.0
    while t < len(x):
        k = int(np.argmin(np.abs(pos - t)))
        centro, p = marcas[k]
        passo = p / razao if p is not None else hop
        meia = int(round(p)) if p is not None else hop
        a, b = centro - meia, centro + meia
        seg_a, seg_b = max(0, a), min(len(x), b)
        janela = np.hanning(2 * meia + 1)[seg_a - a : seg_a - a + (seg_b - seg_a)]
        destino = int(round(t)) - (centro - seg_a)
        d_a, d_b = max(0, destino), min(len(x), destino + (seg_b - seg_a))
        if d_b > d_a:
            o = d_a - destino
            y[d_a:d_b] += x[seg_a + o : seg_a + o + (d_b - d_a)] * janela[o : o + (d_b - d_a)]
            peso[d_a:d_b] += janela[o : o + (d_b - d_a)]
        t += passo
    return y / np.maximum(peso, 1e-3) * (peso > 1e-3)


TECNICAS = {"world": deslocar_world, "psola": deslocar_psola}


# ---- cadeia por falante ------------------------------------------------------
def voz_do_falante(rotulo: str) -> tuple[float, dict | None, str]:
    rig = FALANTES[rotulo]["rig"]
    if rig is None:
        return float(fala.NARRADOR["ritmo"]), None, str(fala.NARRADOR.get("pitch", ""))
    v = voz_do_rig(rig)
    tim = v.get("timbre")
    if tim and (not tim.get("portadora") or float(tim.get("mistura", 0) or 0) <= 0):
        tim = None
    return float(v.get("ritmo", 0) or 0), tim, str(v.get("pitch", ""))


def falar(voz, rotulo: str, semitons: float, tecnica: str | None, ports: dict) -> np.ndarray:
    ritmo, tim, _ = voz_do_falante(rotulo)
    partes = []
    for frase in FRASES:
        x = _pcm_para_float(sintetizar(voz, frase, ritmo))
        if tecnica and semitons:
            x = TECNICAS[tecnica](x, semitons)
        pcm = _float_para_pcm(x)
        if tim:
            pcm = _tim.aplicar(pcm, ports[tim["portadora"]], mistura=float(tim["mistura"]),
                               bandas=int(tim.get("bandas", 16)))
        partes.append(_pcm_para_float(pcm))
        partes.append(np.zeros(int(0.25 * TAXA)))
    return np.concatenate(partes)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sem-modelos-extra", action="store_true", help="não mede a alternativa C")
    args = ap.parse_args(argv)

    alvos = yaml.safe_load((AQUI / "alvos.yaml").read_text(encoding="utf-8"))
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    amostras = WORKSPACE / "amostras"
    ports = portadoras()
    voz = carregar_voz(modelo_travado())

    res: dict = {"frases": FRASES, "atual": {}, "tecnicas": {}, "modelos_extra": {}, "determinismo": {}}

    # 1. o que a dublagem faz hoje (sem deslocamento)
    for rot in FALANTES:
        x = falar(voz, rot, 0.0, None, ports)
        _gravar_wav(amostras / f"atual-{rot}.wav", x)
        _, tim, pitch = voz_do_falante(rot)
        res["atual"][rot] = {"pitch_declarado": pitch, "timbre": bool(tim), **medir(x)}
        print(f"  atual     {rot:10s} {res['atual'][rot]['f0_mediana_hz']} Hz")

    # 2. alvo em Hz = referência medida × 2^(st/12); deslocamento = alvo vs. atual
    ref = float(np.median([r["f0_mediana_hz"] for r in res["atual"].values()]))
    res["referencia_hz"] = round(ref, 2)
    st_por_falante = {rot: float(alvos["semitons"][alvos["categoria"][rot]]) for rot in FALANTES}
    for tec in TECNICAS:
        res["tecnicas"][tec] = {}
        for rot in FALANTES:
            alvo_hz = ref * 2 ** (st_por_falante[rot] / 12)
            desloc = 12 * math.log2(alvo_hz / res["atual"][rot]["f0_mediana_hz"])
            x = falar(voz, rot, desloc, tec, ports)
            _gravar_wav(amostras / f"{tec}-{rot}.wav", x)
            m = medir(x)
            m.update(
                {
                    "alvo_st": st_por_falante[rot],
                    "alvo_hz": round(alvo_hz, 2),
                    "deslocamento_aplicado_st": round(desloc, 3),
                    "erro_cents": round(1200 * math.log2(m["f0_mediana_hz"] / alvo_hz), 1),
                    "duracao_preservada": len(x) == len(falar(voz, rot, 0.0, None, ports)),
                }
            )
            res["tecnicas"][tec][rot] = m
            print(f"  {tec:9s} {rot:10s} alvo {alvo_hz:6.1f} medido {m['f0_mediana_hz']} ({m['erro_cents']:+.0f} c)")

    # 3. determinismo de cada técnica: 2× no mesmo processo, bytes iguais?
    x0 = _pcm_para_float(sintetizar(voz, FRASES[0], 0.0))
    for tec, fn in TECNICAS.items():
        a, b = _float_para_pcm(fn(x0, -3.0)), _float_para_pcm(fn(x0.copy(), -3.0))
        res["determinismo"][tec] = {
            "mesmo_processo_identico": a == b,
            "sha256": hashlib.sha256(a).hexdigest(),
        }

    # 4. alternativa C: outros modelos piper pt_BR, sem DSP
    if not args.sem_modelos_extra:
        for nome, caminho in MODELOS_EXTRA.items():
            try:
                onnx, sha = modelo_extra(nome, caminho)
                v = carregar_voz(onnx)
                x = np.concatenate([_pcm_para_float(sintetizar(v, f, 0.0)) for f in FRASES])
                res["modelos_extra"][nome] = {"sha256": sha, "taxa": v.config.sample_rate, **medir(x, v.config.sample_rate)}
                print(f"  modelo    {nome:22s} {res['modelos_extra'][nome]['f0_mediana_hz']} Hz")
            except Exception as exc:  # noqa: BLE001
                res["modelos_extra"][nome] = {"erro": f"{type(exc).__name__}: {exc}"}

    # distâncias entre guardiões (st) no melhor caso de cada técnica
    def dist(tabela):
        rots = list(tabela)
        return {
            f"{a}~{b}": round(abs(12 * math.log2(tabela[a]["f0_mediana_hz"] / tabela[b]["f0_mediana_hz"])), 2)
            for i, a in enumerate(rots)
            for b in rots[i + 1 :]
        }

    res["distancias_st"] = {"atual": dist(res["atual"]), **{t: dist(res["tecnicas"][t]) for t in TECNICAS}}
    res["nota_portadoras"] = (
        "portadoras decodificadas por libsndfile (não ffmpeg); mp3 conferido pelo sha do amostras.lock"
    )
    (WORKSPACE / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  resultado: {(WORKSPACE / 'resultado.json').relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
