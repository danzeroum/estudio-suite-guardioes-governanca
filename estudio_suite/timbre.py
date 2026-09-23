"""O motor de timbre: a portadora animal sob a voz sintetica (CP-005).

Vocoder de canais deterministico, scipy puro, inteiro em diff -- nada de
"arte gerada por modelo": o envelope de cada banda da FALA e extraido e
imposto a banda correspondente da PORTADORA (o som do animal ancorado em
amostras.lock). A voz continua sendo a da CP-004; o animal e camada.

A regra de ouro da CP em uma linha: mistura 0 devolve o pcm INTOCADO,
byte a byte -- a camada so existe quando declarada e medida.

Determinismo: butter/sosfilt/resample_poly sao operacoes fixas de filtro;
mesma entrada + mesmos parametros -> mesmos bytes. Sem sorte, sem semente,
sem nada que duas execucoes possam discordar.

Earcons do Dado: aceso (brilho ascendente ~300 ms), retraido (tom
descendente ~400 ms), citar (carimbo percussivo ~150 ms) -- senoides +
envelope, codigo puro, commitados em sons/ e ancorados no amostras.lock.
Trocar o som do Dado tambem e ato revisado, nao edicao silenciosa.
"""
import math
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, resample_poly, sosfilt

from .comum import RAIZ

TAXA_VOZ = 22050            # o piper sintetiza em 22050; o mix sobe para 48k
TAXA_SOM = 48000            # earcons e portadoras moram em 48 kHz mono
SONS = RAIZ / "sons"

# Faixa util da fala: abaixo de 80 Hz e ruido de pico, acima de 8 kHz e
# sibilancia que o pt_BR-faber-medium mal produz. O banco e log-espacado
# porque a fala ocupa logarithmically o espectro.
F_MIN, F_MAX = 80.0, 8000.0
ENV_CORTE_HZ = 60.0         # passa-baixa do seguidor de envelope
ORDEM_BANDA = 4             # butter passa-banda por canal

# Earcons do Dado: frequencias e duracoes de partida (CP-005). Puro dado --
# mudar o som do Dado e mudar estes numeros E avancar o amostras.lock.
EARCONS = {
    "aceso":    {"de": 392.0, "para": 784.0, "dur": 0.300, "decai": 0.12},
    "retraido": {"de": 660.0, "para": 330.0, "dur": 0.400, "decai": 0.16},
    "citar":    {"de": 150.0, "para": 150.0, "dur": 0.150, "decai": 0.04},
}


# ---- leitura de wav (48 kHz mono pcm16, sem dependencias) -----------------
def _ler_wav(caminho: Path) -> np.ndarray:
    with wave.open(str(caminho), "rb") as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2, (
            f"{caminho.name}: esperado mono pcm16 (a portadora e normalizada "
            f"para 48 kHz mono no amostras.py)")
        taxa = w.getframerate()
        bruto = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return bruto.astype(np.float64) / 32768.0, taxa


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x * x))) if len(x) else 0.0


def _portadora_em_22050(caminho: Path) -> np.ndarray:
    """Portadora 48 kHz -> 22050: mudanca de FORMATO, duracao identica.

    22050/48000 = 147/320 exatos -- resample_poly com razao racional, sem
    sorte e sem interpolacao arbitraria. Time-stretch continua proibido.
    """
    port, taxa = _ler_wav(caminho)
    if taxa != TAXA_SOM:
        raise ValueError(f"{caminho.name}: portadora em {taxa} Hz, esperado 48 kHz")
    return resample_poly(port, 147, 320)


def aplicar(pcm: bytes, portadora: Path, mistura: float, bandas: int = 16) -> bytes:
    """Vocoder de canais sobre um clipe PCM16 22050. mistura 0 = intocado.

    A cadeia por clipe da CP-005: fala -> piper -> timbre -> posicionar ->
    mixar. Esta funcao e o estagio "timbre": recebe o clipe ja sintetizado
    e devolve o clipe timbrado, com o MESMO numero de amostras -- o animal
    nao come tempo, so textura.
    """
    if mistura <= 0:
        return pcm                                    # a camada e aditiva de verdade
    voz = np.frombuffer(pcm, dtype=np.int16).astype(np.float64) / 32768.0
    if not len(voz):
        return pcm

    port = _portadora_em_22050(portadora)
    # Ganho da portadora ancorado na fala: o RMS do animal acompanha o RMS
    # da voz (o elefante e a portadora mais alta -- medido, ~-10 dB RMS -- e
    # e aqui que o headroom de que a CP fala e tratado, de forma fixa).
    r_voz, r_port = _rms(voz), _rms(port)
    if r_port > 0:
        port = port * (r_voz / r_port)
    # Portadora mais curta que o clipe faz LOOP (repeticao, nunca esticar);
    # mais longa, trunca. Nada e reamostrado para caber.
    if len(port) < len(voz):
        rep = math.ceil(len(voz) / len(port))
        port = np.tile(port, rep)
    port = port[:len(voz)]

    bordas = np.exp(np.linspace(math.log(F_MIN), math.log(F_MAX), bandas + 1))
    sos_env = butter(2, ENV_CORTE_HZ, "low", fs=TAXA_VOZ, output="sos")
    voc = np.zeros_like(voz)
    for lo, hi in zip(bordas[:-1], bordas[1:]):
        if hi >= TAXA_VOZ / 2:
            break                                  # nyquist: banda que nao existe
        sos = butter(ORDEM_BANDA, [lo, hi], "band", fs=TAXA_VOZ, output="sos")
        env = sosfilt(sos_env, np.abs(sosfilt(sos, voz)))   # envelope da fala
        voc += sosfilt(sos, port) * env                     # ...imposto ao animal
    # O vocoder volta ao RMS da voz: a mistura nao muda o plano de loudness
    # -- o loudnorm do mix continua o unico dono do nivel final.
    r_voc = _rms(voc)
    if r_voc > 0:
        voc = voc * (r_voz / r_voc)
    soma = (1.0 - mistura) * voz + mistura * voc
    saida = np.round(np.clip(soma, -1.0, 1.0) * 32767.0).astype(np.int16)
    return saida.tobytes()


# ---- earcons do Dado --------------------------------------------------------
def _earcon(nome: str) -> np.ndarray:
    """Senoide + envelope, 48 kHz, pico 1.0. Deterministico de ponta a ponta."""
    p = EARCONS[nome]
    n = int(round(p["dur"] * TAXA_SOM))
    t = np.arange(n) / TAXA_SOM
    f = p["de"] + (p["para"] - p["de"]) * (t / p["dur"])   # glide linear
    fase = 2.0 * math.pi * np.cumsum(f) / TAXA_SOM
    s = np.sin(fase)
    # envelope: ataque curto, cauda exponencial -- "carimbo", nao "note"
    ata = int(round(0.010 * TAXA_SOM))
    env = np.ones(n)
    env[:ata] = np.linspace(0.0, 1.0, ata)
    cauda = np.exp(-t / p["decai"])
    env *= 1.0 - (1.0 - cauda) * 0.85
    s = s * env
    return np.round(np.clip(s, -1.0, 1.0) * 32767.0).astype(np.int16)


def gerar_earcons(destino: Path = SONS) -> dict:
    """(Re)gera sons/dado-*.wav. Os arquivos sao commitados e ancorados no
    amostras.lock -- regenerar divergente exige avancar o lock por PR."""
    destino.mkdir(parents=True, exist_ok=True)
    out = {}
    for nome in EARCONS:
        f = destino / f"dado-{nome}.wav"
        with wave.open(str(f), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(TAXA_SOM)
            w.writeframes(_earcon(nome).tobytes())
        out[nome] = f
    return out


def main(argv=None) -> int:
    import sys
    ger = gerar_earcons()
    print(f"  {len(ger)} earcon(s) do Dado regenerado(s) em {SONS.relative_to(RAIZ)}/:")
    import hashlib
    for nome, f in sorted(ger.items()):
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        print(f"    dado-{nome}.wav  ({EARCONS[nome]['dur']*1000:.0f} ms, sha256 {sha[:12]}...)")
    print("  ancorados em amostras.lock; divergir exige avancar o lock por PR.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
