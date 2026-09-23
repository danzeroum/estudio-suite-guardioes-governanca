#!/usr/bin/env python3
"""O motor de timbre e os earcons, provados nos dois sentidos (CP-005, Sprint 7).

O contrato caro da CP-005: a camada e ADITIVA de verdade. mistura 0 devolve
o clipe byte a byte (o teste prova no PCM), o vocoder e deterministico
(mesma entrada -> mesmos bytes, duas vezes), e a duracao NUNCA muda -- o
animal nao come tempo, so textura. Os earcons sao codigo puro: duracoes
declaradas, 48 kHz mono, ancorados no amostras.lock.

O fiscal de redublagem estendido tambem e provado aqui: timbre no rig sem
redublar e divida apontada, parametro mudou e divida apontada, momento do
Dado mudou e divida apontada.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import amostras                       # noqa: E402
from estudio_suite import dublar                         # noqa: E402
from estudio_suite import pipeline                       # noqa: E402
from estudio_suite import timbre                         # noqa: E402
from estudio_suite.comum import FILMES                   # noqa: E402

ok, bad = [], []
FANTASMA = "teste-timbre-fantasma"


def chk(c, msg):
    (ok if c else bad).append(msg)


def _pcm_teste(segundos=1.5, taxa=22050):
    """Fala sintetica: vibrato + formante + pausa -- parecida com voz."""
    n = int(segundos * taxa)
    t = np.arange(n) / taxa
    f = 180.0 + 40.0 * np.sin(2 * np.pi * 3.0 * t)
    s = 0.6 * np.sin(2 * np.pi * np.cumsum(f) / taxa)
    s += 0.2 * np.sin(2 * np.pi * 1400.0 * t)
    s *= (0.5 + 0.5 * np.sin(2 * np.pi * 2.5 * t))
    s[int(0.7 * n):int(0.8 * n)] = 0.0        # pausa: envelope de silencio
    return (np.clip(s, -1, 1) * 32767).astype(np.int16).tobytes()


def _portadora_teste(caminho: Path, segundos=8.0, taxa=48000):
    n = int(segundos * taxa)
    t = np.arange(n) / taxa
    f = 500.0 + 200.0 * np.sin(2 * np.pi * 1.3 * t)
    s = 0.7 * np.sin(2 * np.pi * np.cumsum(f) / taxa) + 0.3 * np.sin(2 * np.pi * 90.0 * t)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(taxa)
        w.writeframes((np.clip(s, -1, 1) * 32767).astype(np.int16).tobytes())


def _filme_fantasma():
    d = FILMES / FANTASMA
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    filme = {
        "id": FANTASMA, "titulo": "Fantasma do timbre", "duracao": 8,
        "elenco": {"ana": {"rig": "raposa", "papel": "Titular"}},
        "planos": [{
            "id": "p01", "titulo": "Teste", "dur": 8, "guardiao": "coruja",
            "cenario": "vazio", "poster": 3, "arts": [],
            "entra": {"ana": {"x": 300, "y": 620}},
            "acoes": [
                {"em": 1.0, "dur": 2.0, "alvo": "dado", "para": {"escala": 1, "op": 1},
                 "ease": "elastico"},
                {"em": 4.0, "alvo": "dado", "evento": "citar",
                 "dados": {"artigo": 5, "guardiao": "coruja"}},
            ],
            "legendas": [{"em": 0.3, "ate": 5.5, "txt": "Uma legenda que fala."}],
        }],
    }
    (d / f"{FANTASMA}.filme.js").write_text(
        "window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};"
        "window.ESTUDIO_FILMES[\"" + FANTASMA + "\"]=\n" +
        json.dumps(filme, ensure_ascii=False, indent=1) + "\n;\n", encoding="utf-8")
    return d


def _dublagem(clipes, earcons=None):
    # O ambiente do lock via junto: dublagem "em dia" desde a CP-007 nasce
    # com ele -- o fantasma em sincronia carrega o que o dublar gravaria.
    from estudio_suite import voz as _voz
    d = FILMES / FANTASMA / "audio"
    d.mkdir(parents=True, exist_ok=True)
    manifesto = {"filme": FANTASMA, "clipes": clipes,
                 "ambiente": _voz.ancora()["ambiente"]}
    if earcons is not None:
        manifesto["earcons"] = earcons
    (d / "audio.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    tmp = Path(__import__("tempfile").mkdtemp())
    port = tmp / "portadora-teste.wav"
    _portadora_teste(port)
    pcm = _pcm_teste()

    # --- mistura 0: o clipe volta INTOCADO, byte a byte ------------------
    chk(timbre.aplicar(pcm, port, mistura=0.0) == pcm,
        "mistura 0 devolve o pcm identico — a camada e aditiva de verdade")

    # --- determinismo: duas execucoes, mesmos bytes ----------------------
    a1 = timbre.aplicar(pcm, port, mistura=0.35, bandas=16)
    a2 = timbre.aplicar(pcm, port, mistura=0.35, bandas=16)
    chk(a1 == a2, "vocoder deterministico: mesma entrada, mesmos bytes")

    # --- a textura entra E a duracao nao muda ----------------------------
    chk(a1 != pcm, "mistura 0.35 muda o clipe (a portadora entra)")
    chk(len(a1) == len(pcm),
        "o animal nao come tempo: mesmo numero de amostras (time-stretch proibido)")
    saida = np.frombuffer(a1, dtype=np.int16)
    chk(saida.dtype == np.int16 and np.abs(saida).max() <= 32767,
        "saida em PCM16 sem estouro")

    # --- portadora mais curta que o clipe: LOOP, nunca esticar ----------
    curta = tmp / "portadora-curta.wav"
    _portadora_teste(curta, segundos=0.4)
    b = timbre.aplicar(pcm, curta, mistura=0.35, bandas=8)
    chk(len(b) == len(pcm), "portadora curta faz loop e a duracao segue a da voz")

    # --- earcons: codigo puro, ancorados no lock --------------------------
    esperado = {"aceso": 0.300, "retraido": 0.400, "citar": 0.150}
    ancoradas = amostras.ancora()
    for nome, dur_alvo in esperado.items():
        f = RAIZ / "sons" / f"dado-{nome}.wav"
        chk(f.exists(), f"dado-{nome}.wav commitado em sons/")
        if f.exists():
            with wave.open(str(f), "rb") as w:
                taxa, canais, n = w.getframerate(), w.getnchannels(), w.getnframes()
            chk(taxa == 48000 and canais == 1, f"dado-{nome}.wav em 48 kHz mono")
            chk(abs(n / taxa - dur_alvo) <= 0.010,
                f"dado-{nome}.wav dura {n/taxa*1000:.0f} ms (alvo {dur_alvo*1000:.0f} ms)")
            entrada = ancoradas.get(f"dado-{nome}")
            chk(entrada and entrada["sha256"] == hashlib.sha256(f.read_bytes()).hexdigest(),
                f"dado-{nome}.wav ancorado no amostras.lock com sha batendo")

    # --- a regeneracao e reproduzivel ------------------------------------
    antes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
             for f in sorted((RAIZ / "sons").glob("*.wav"))}
    timbre.gerar_earcons()
    depois = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
              for f in sorted((RAIZ / "sons").glob("*.wav"))}
    chk(antes == depois, "regenerar earcons reproduz os mesmos bytes (deterministico)")

    # --- os rigs declaram timbre, e as portadoras estao ancoradas --------
    for rig, portadora in (("aguia", "aguia-guincho"), ("coruja", "coruja-pio"),
                           ("elefante", "elefante-trompa"), ("raposa", "raposa-latido")):
        t = dublar.voz_do_rig(rig).get("timbre") or {}
        chk(t.get("portadora") == portadora and float(t.get("mistura", 0)) == 0.35,
            f"{rig}: declara timbre {portadora} mistura 0.35")
        chk(portadora in ancoradas, f"{rig}: portadora ancorada no lock")
    chk("timbre" not in dublar.voz_do_rig("tartaruga"),
        "tartaruga sem timbre (decisao (b): so ritmo)")
    chk("timbre" not in dublar.voz_do_rig("dado"),
        "dado sem timbre (mudo por roteiro)")

    # --- fiscal de redublagem: timbre e earcons --------------------------
    _filme_fantasma()
    L = [{"em": 0.3, "ate": 5.5, "txt": "Uma legenda que fala."}][0]
    P = json.loads((FILMES / FANTASMA / f"{FANTASMA}.filme.js").read_text()
                   .split("=\n", 1)[1].rstrip().rstrip(";"))["planos"][0]
    _t, _r, _rot, tim = dublar.quem_fala(P, L, {"ana": {"rig": "raposa", "papel": "Titular"}})
    sha_coruja = ancoradas["coruja-pio"]["sha256"]
    tim_coruja = {"portadora": "coruja-pio", "mistura": 0.35, "bandas": 16,
                  "portadora_sha256": sha_coruja}
    clip_ok = {"plano": "p01", "em": 0.3, "ate": 5.5, "dur": 2.0, "voz": "coruja",
               "texto_sha256": hashlib.sha256(
                   dublar.fala.normalizar(L["txt"]).encode()).hexdigest(),
               "timbre": dict(tim_coruja)}
    earcons_ok = [{"plano": "p01", "em": 1.0, "tipo": "aceso", "arquivo": "dado-aceso.wav",
                   "ganho_db": -10.0},
                  {"plano": "p01", "em": 4.0, "tipo": "citar", "arquivo": "dado-citar.wav",
                   "ganho_db": -10.0}]

    # em sincronia total: o fiscal cala
    _dublagem([clip_ok], earcons_ok)
    a = pipeline.fiscal_redublagem(FANTASMA)
    chk(a == [], f"rig timbrado + dublagem em dia: fiscal cala ({a})")

    # timbre REMOVIDO do rig (simulado): dublagem com timbre sobrando
    original_quem_fala = dublar.quem_fala
    dublar.quem_fala = lambda P, L, el: original_quem_fala(P, L, el)[:3] + (None,)
    try:
        a = pipeline.fiscal_redublagem(FANTASMA)
        chk(any("COM timbre" in x for x in a), f"timbre que saiu do rig e divida ({a})")
    finally:
        dublar.quem_fala = original_quem_fala

    # parametro de mistura mudou no rig: divida
    dublar.quem_fala = lambda P, L, el: original_quem_fala(P, L, el)[:3] + (
        {"portadora": "coruja-pio", "mistura": 0.5, "bandas": 16},)
    try:
        _dublagem([clip_ok], earcons_ok)
        a = pipeline.fiscal_redublagem(FANTASMA)
        chk(any("mistura: 0.35 -> 0.5" in x for x in a),
            f"parametro de timbre mudou e e apontado ({a})")
        # portadora do lock avancou (sha diferente): divida
        clip_sha = dict(clip_ok)
        clip_sha["timbre"] = dict(tim_coruja, portadora_sha256="f" * 64)
        _dublagem([clip_sha], earcons_ok)
        a = pipeline.fiscal_redublagem(FANTASMA)
        chk(any("lock avancou" in x for x in a),
            f"portadora com sha divergente do lock e divida ({a})")
    finally:
        dublar.quem_fala = original_quem_fala

    # momento do Dado mudou no filme sem redublar: divida
    _dublagem([clip_ok], earcons_ok[:-1])
    a = pipeline.fiscal_redublagem(FANTASMA)
    chk(any("momentos do Dado" in x for x in a),
        f"earcon sem redublagem e divida ({a})")

    shutil.rmtree(FILMES / FANTASMA, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)

    # --- o fiscal global dos sons versionados fecha 0 --------------------
    r = subprocess.run([sys.executable, "-c",
                        "import sys; sys.path.insert(0, '.'); "
                        "from estudio_suite import amostras; sys.exit(amostras.checar())"],
                       capture_output=True, text=True, cwd=RAIZ)
    chk(r.returncode == 0,
        f"sons ancorados: fiscal global conforme — exit {r.returncode} ({r.stdout.strip()[-80:]})")

    # --- os filmes reais: dublagens commitadas em dia --------------------
    for fid in ("jornada-dado", "legitimo-interesse"):
        if (FILMES / fid / "audio" / "audio.json").exists():
            a = pipeline.fiscal_redublagem(fid)
            chk(a == [], f"{fid}: dublagem commitada em dia com rigs e Dado ({a})")

    print(f"  {len(ok)} verificacoes do motor de timbre e dos earcons.")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  o animal e camada sobre a voz — e mistura 0 prova que so camada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
