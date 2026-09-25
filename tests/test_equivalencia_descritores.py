#!/usr/bin/env python3
"""A equivalência por descritores da classe avx2, provada nos dois sentidos (CP-012).

O contrato, exigido pela CP:

  DURAÇÃO MEDIDA: a energia separa fala de silêncio — o recorte tem
  tamanho fixo, o número diz QUANTO DELE TEM FALA, e o corte de 50 ms
  é quem tem de movê-lo.

  TETOS: vêm do lock (bloco tolerancia) — sem as quatro chaves, o passo
  RECUSA (lock incompleto), nunca verde por omissão.

  JULGAMENTO: deltas por fala contra os tetos; acima é vermelho COM O
  NÚMERO.

  CONTROLES POSITIVOS: +0,5 dB, +20 cents, fala trocada do mesmo
  guardião e 50 ms de corte — todos têm de REPROVAR, nomeando o
  descritor. Controle que passa é TETO_NAO_DISCRIMINA (a tolerância
  virou ponto) — provado aqui com um teto folgado de loudness.

Roda em CI (numpy do lock, ffmpeg e audio-suite do job fiscais): os
casos de medida real usam tons sintéticos — a síntese de fala de
verdade é da imagem dubladora; aqui se prova o CONTRATO do passo.
Sem audio-suite ou ffmpeg, os casos reais são nomeados como não medidos
e os contratos puros seguem (o padrão do test_vozes).
"""
import importlib.util
import io
import math
import shutil
import subprocess
import sys
import wave
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import voz                                # noqa: E402

# o modulo do passo mora em ci/ (executável do gate): carregado por
# caminho, como o test_pins_do_lock faz com o pins_do_lock.
_spec = importlib.util.spec_from_file_location(
    "equivalencia_descritores", RAIZ / "ci" / "equivalencia_descritores.py")
desc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(desc)

ok, bad = [], []
TEM_SUITE = shutil.which("audio-suite") is not None
TEM_FFMPEG = shutil.which("ffmpeg") is not None
MEDIDA_REAL = TEM_SUITE and TEM_FFMPEG


def chk(c, msg):
    (ok if c else bad).append(msg)


TAXA = 48000


def _tom(freq: float, dur: float, amp: float = 0.05) -> np.ndarray:
    t = np.arange(int(dur * TAXA)) / TAXA
    return np.round(np.sin(2 * math.pi * freq * t) * amp * 32768).astype(np.int16)


def _trilha(caminho: Path, ganho_db: float = 0.0) -> Path:
    """Trilha sintética: silêncio, 3 falas (tons de 440/660/330 Hz) do
    MESMO guardião, silêncio — a geometria exata de um audio.json."""
    g = 10.0 ** (ganho_db / 20.0)
    partes = [
        np.zeros(int(0.5 * TAXA), dtype=np.int16),
        _tom(440.0, 2.0), np.zeros(int(0.3 * TAXA), dtype=np.int16),
        _tom(660.0, 1.5), np.zeros(int(0.3 * TAXA), dtype=np.int16),
        _tom(330.0, 1.8), np.zeros(int(1.6 * TAXA), dtype=np.int16),
    ]
    pcm = np.concatenate(partes)
    if ganho_db != 0.0:
        pcm = np.clip(np.rint(pcm.astype(np.float64) * g), -32768,
                      32767).astype(np.int16)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(pcm.tobytes())
    return caminho


_CLIPES = [
    {"plano": "p01", "em": 0.5, "ate": 2.5, "dur": 2.0, "voz": "sintetico",
     "texto_sha256": "a" * 64},
    {"plano": "p02", "em": 2.8, "ate": 4.3, "dur": 1.5, "voz": "sintetico",
     "texto_sha256": "b" * 64},
    {"plano": "p03", "em": 4.6, "ate": 6.4, "dur": 1.8, "voz": "sintetico",
     "texto_sha256": "c" * 64},
]

_LOCK_CABECALHO = """schema: estudio-suite/voz-lock-teste@1
modelo:
  nome: sintetico
  origem: https://example.invalid/sintetico
arquivos:
  sintetico.onnx:
    sha256: %s
ambiente:
  python: 3.12
""" % ("0" * 64)


def _lock_com_tetos(duracao_ms=6.0, loudness_lu=0.1, f0_hz=1.0,
                    centroide_hz=20.0) -> str:
    return (_LOCK_CABECALHO + f"""tolerancia:
  residuo_max_dbfs: -74.9
  descritores_duracao_ms_max: {duracao_ms:g}
  descritores_loudness_lu_max: {loudness_lu:g}
  descritores_f0_hz_max: {f0_hz:g}
  descritores_centroide_hz_max: {centroide_hz:g}
""")


def _cenario(tmp: Path, ganho_reg: float = 0.0):
    """prova.json + trilhas + manifesto commitado — o formato exato que o
    passo do runner consome (a prova da imagem publica esses WAVs)."""
    com = _trilha(tmp / "fantasma-commitado.wav")
    reg = _trilha(tmp / "fantasma-regenerado.wav", ganho_db=ganho_reg)
    prov = tmp / "prova.json"
    prov.write_text(__import__("json").dumps({
        "classe": {"runner": "avx2", "ancora": "avx512"},
        "wavs_para_compare": [str(com), str(reg)],
    }), encoding="utf-8")
    mani = tmp / "commitado" / "filmes" / "fantasma" / "audio"
    mani.mkdir(parents=True, exist_ok=True)
    (mani / "audio.json").write_text(
        __import__("json").dumps({"clipes": _CLIPES}), encoding="utf-8")
    return prov


def _rodar(argv_extra):
    argv = ["--prova", str(_PROVA.parent), "--commitado", str(_COM)]
    argv += argv_extra
    velho = sys.argv
    saida = io.StringIO()
    rc = None
    try:
        sys.argv = ["equivalencia_descritores.py"] + argv
        with redirect_stdout(saida):
            rc = desc.main()
    finally:
        sys.argv = velho
    return rc, saida.getvalue()


def main():
    # --- duracao medida: a energia separa fala de silencio ---------------
    sil = np.zeros(int(0.2 * TAXA), dtype=np.int16)
    fala = _tom(440.0, 1.0)
    seg = np.concatenate([sil, fala, sil])
    chk(abs(desc.duracao_de_voz(seg, TAXA) - 1000.0) < 1.0,
        f"a duracao medida ignora o silencio das pontas "
        f"({desc.duracao_de_voz(seg, TAXA):.0f} ms de 1400 ms de recorte)")
    chk(desc.duracao_de_voz(sil, TAXA) == 0.0,
        "recorte todo silencioso -> duracao 0")
    # o corte de 50 ms move o numero na medida certa
    cortado = np.concatenate([sil, fala[:-int(0.05 * TAXA)], sil[:int(0.05 * TAXA)]])
    chk(abs((desc.duracao_de_voz(seg, TAXA)
             - desc.duracao_de_voz(cortado, TAXA)) - 50.0) < 1.0,
        "cortar 50 ms do fim move a duracao medida em ~50 ms — o controle "
        "do teto de duracao enxerga por aqui")

    # --- tetos do lock: o que existe e o que falta -------------------------
    tol = {"descritores_duracao_ms_max": "6",
           "descritores_loudness_lu_max": "0.1"}
    tetos = desc.ler_tetos(tol)
    chk(tetos == {"duracao_ms": 6.0, "loudness_lu": 0.1},
        "ler_tetos devolve exatamente o que o lock tem (as duas chaves)")
    chk(desc.julgar(0.05, 0.1) and not desc.julgar(0.15, 0.1),
        "julgar: delta sob o teto passa; acima reprova")

    if not MEDIDA_REAL:
        print(f"  {len(ok)} verificações de contrato puro."
              + (" (audio-suite/ffmpeg ausentes: os casos de medida real "
                 "não ocorreram nesta máquina)" if not MEDIDA_REAL else ""))
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        return 1 if bad else 0

    import json
    import tempfile

    global _PROVA, _COM
    _lock_real = voz.LOCK
    try:
        with tempfile.TemporaryDirectory(prefix="eq-desc-") as td:
            tmp = Path(td)
            _PROVA = _cenario(tmp)
            _COM = tmp / "commitado"

            # (1) lock INCOMPLETO: sem os tetos, mede e publica mas RECUSA
            voz.LOCK = _lock_fake(tmp, _LOCK_CABECALHO)
            rc, out = _rodar([])
            doc = json.loads((tmp / "descritores.json").read_text(encoding="utf-8"))
            chk(rc == 2 and "INCOMPLETO" in out and doc["filmes"][0]["max_abs_delta"],
                "lock sem tetos: RECUSA (exit 2, lock incompleto) com os "
                "deltas medidos publicados — verde por omissao nao existe")

            # (2) VERDE com tetos apertados: trilhas iguais, controles reprovam
            voz.LOCK = _lock_fake(tmp, _lock_com_tetos())
            rc, out = _rodar([])
            chk(rc == 0 and "verde" in out,
                f"trilhas iguais com tetos apertados: verde (exit {rc})")
            chk("loudness delta +0.50" in out and "REPROVOU" in out,
                "controle +0,5 dB reprova nomeando loudness (com o numero)")
            chk("f0 mediana delta" in out and "REPROVOU" in out,
                "controle +20 cents reprova nomeando f0 mediana")
            chk("duracao delta" in out and "REPROVOU" in out,
                "controle 50 ms reprova nomeando duracao")
            chk("trocada" in out and "REPROVOU" in out,
                "controle da fala trocada reprova nomeando os descritores")

            # (3) TETO_NAO_DISCRIMINA: teto de loudness folgado deixa o
            # controle passar -> parada nomeada, exit 1
            voz.LOCK = _lock_fake(tmp, _lock_com_tetos(loudness_lu=2.0))
            rc, out = _rodar([])
            chk(rc == 1 and "TETO_NAO_DISCRIMINA" in out and "loudness" in out,
                f"teto folgado de loudness (2 LU): o controle +0,5 dB passa "
                f"-> TETO_NAO_DISCRIMINA, exit {rc}, descritor nomeado")

            # (4) VERMELHO real: regenerado com +0,3 dB contra teto 0,1
            _div = tmp / "divergente"
            _div.mkdir(parents=True, exist_ok=True)
            _PROVA = _cenario(_div, ganho_reg=0.3)
            voz.LOCK = _lock_fake(tmp, _lock_com_tetos())
            rc, out = _rodar([])
            chk(rc == 1 and "VERMELHO" in out and "loudness" in out,
                f"regenerado +0,3 dB contra teto 0,1 LU: vermelho com o "
                f"numero (exit {rc})")
    finally:
        voz.LOCK = _lock_real

    print(f"  {len(ok)} verificações da equivalência por descritores.")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  a medida diz o número; o teto diz o veredito; e o controle "
          "positivo prova que o teto ainda enxerga.")
    return 0


def _lock_fake(tmp: Path, conteudo: str) -> Path:
    p = tmp / "voz.lock"
    p.write_text(conteudo, encoding="utf-8")
    return p


if __name__ == "__main__":
    sys.exit(main())
