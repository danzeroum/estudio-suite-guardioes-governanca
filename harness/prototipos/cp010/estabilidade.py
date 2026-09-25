"""CP-010 — a etapa de pitch é estável entre classes de SIMD?

Verificação, não validação: roda SÓ a etapa de pitch (PSOLA e WORLD) sobre
PCM FIXO — sintetizado uma vez e conferido por sha256 a cada execução, para
isolar o piper/onnxruntime (onde o Agente A localizou a divergência entre
runners AVX2 e AVX-512) — em níveis de CPU controlados:

  N0  nada desligado
  N1  NPY_DISABLE_CPU_FEATURES sem AVX-512
  N2  N1 + AVX2, FMA3, AVX (e F16C, que o numpy exige desligar com o AVX)
  N3  N2 + GLIBC_TUNABLES sem AVX-512/AVX2/FMA/AVX na libm da glibc
      (o pyworld não usa numpy no núcleo: liga em libm/libstdc++, cujas
      variantes por CPU são escolhidas por ifunc e ESCAPAM do NPY_*)

cada um com threads 1 e 2 (OMP/OPENBLAS/MKL_NUM_THREADS) e repetido 2×.
Cada execução é um processo novo (a seleção de SIMD é feita na importação).
Hash = sha256 do PCM int16 de saída (o que o dublar gravaria) e do float64
antes da quantização (o que a quantização poderia esconder).

Extra, fora da etapa de pitch: o timbre do estúdio (scipy: butter/sosfilt/
resample_poly), porque o scipy não entra na etapa de pitch mas entra na
cadeia logo depois — e "scipy não provado" era a pendência do terceiro.

Uso (venv isolado do protótipo):
    python harness/prototipos/cp010/estabilidade.py            # gera a entrada se faltar e mede
Saída: workspace/cp010-estabilidade/estabilidade.json
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
import yaml

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
DESTINO = RAIZ / "workspace" / "cp010-estabilidade"
ENTRADA = DESTINO / "pcm"

_AVX512 = "AVX512F AVX512CD AVX512_KNL AVX512_KNM AVX512_SKX AVX512_CLX AVX512_CNL AVX512_ICL"
NIVEIS = {
    "N0": {},
    "N1": {"NPY_DISABLE_CPU_FEATURES": _AVX512},
    "N2": {"NPY_DISABLE_CPU_FEATURES": _AVX512 + " AVX2 FMA3 F16C AVX"},
    "N3": {
        "NPY_DISABLE_CPU_FEATURES": _AVX512 + " AVX2 FMA3 F16C AVX",
        "GLIBC_TUNABLES": "glibc.cpu.hwcaps=-AVX512F,-AVX512DQ,-AVX512BW,-AVX512VL,-AVX512CD,-AVX2,-FMA,-FMA4,-AVX",
    },
}
TECNICAS = ("psola", "world", "timbre")
THREADS = (1, 2)
REPETICOES = 2


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _ler(caminho: Path) -> np.ndarray:
    with wave.open(str(caminho), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0


def _alvos() -> dict[str, float]:
    a = yaml.safe_load((AQUI / "alvos.yaml").read_text(encoding="utf-8"))
    return {g: float(a["semitons"][c]) for g, c in a["categoria"].items()}


# ---- a entrada fixa -------------------------------------------------------------
def gerar_entrada() -> dict:
    """PCM do piper por falante (as 3 frases, ritmo do rig), gravado UMA vez."""
    sys.path.insert(0, str(AQUI))
    import prototipo as p

    ENTRADA.mkdir(parents=True, exist_ok=True)
    voz = p.carregar_voz(p.modelo_travado())
    shas = {}
    for g in p.FALANTES:
        ritmo, _, _ = p.voz_do_falante(g)
        x = np.concatenate([p._pcm_para_float(p.sintetizar(voz, f, ritmo)) for f in p.FRASES])
        p._gravar_wav(ENTRADA / f"{g}.wav", x)
        shas[g] = hashlib.sha256((ENTRADA / f"{g}.wav").read_bytes()).hexdigest()
    (ENTRADA / "entrada.json").write_text(json.dumps(shas, indent=1), encoding="utf-8")
    return shas


# ---- o filho: uma configuração, um processo ---------------------------------
def filho(tecnica: str, saida_npy: str) -> None:
    sys.path.insert(0, str(AQUI))
    import prototipo as p
    from numpy._core._multiarray_umath import __cpu_features__ as cpu

    shas = json.loads((ENTRADA / "entrada.json").read_text(encoding="utf-8"))
    alvos = _alvos()
    ports = p.portadoras() if tecnica == "timbre" else {}
    res = {"cpu": {k: bool(cpu.get(k)) for k in ("AVX512F", "AVX2", "FMA3", "AVX")}, "por_falante": {}}
    saidas = {}
    for g in sorted(shas):
        wav = ENTRADA / f"{g}.wav"
        if hashlib.sha256(wav.read_bytes()).hexdigest() != shas[g]:
            raise SystemExit(f"entrada {g} mudou — a comparação exige PCM fixo")
        x = _ler(wav)
        if tecnica == "timbre":
            _, tim, _ = p.voz_do_falante(g)
            if not tim:
                continue
            y = p._pcm_para_float(p._tim.aplicar(p._float_para_pcm(x), ports[tim["portadora"]],
                                                 mistura=float(tim["mistura"]), bandas=int(tim.get("bandas", 16))))
        else:
            if alvos[g] == 0:
                continue  # deslocamento 0 devolve o pcm intocado: nada a medir
            y = p.TECNICAS[tecnica](x, alvos[g])
        saidas[g] = y
        res["por_falante"][g] = {"f64": _sha(np.ascontiguousarray(y, dtype=np.float64).tobytes()),
                                 "i16": _sha(p._float_para_pcm(y))}
    np.savez(saida_npy, **saidas)
    print(json.dumps(res))


# ---- o pai: a matriz --------------------------------------------------------
def main() -> int:
    if not (ENTRADA / "entrada.json").exists():
        print("  gerando a entrada fixa (piper, uma vez)…")
        gerar_entrada()
    entrada = json.loads((ENTRADA / "entrada.json").read_text(encoding="utf-8"))
    tmp = Path(tempfile.mkdtemp())
    execucoes = []
    for tec, nivel, th, rep in itertools.product(TECNICAS, NIVEIS, THREADS, range(1, REPETICOES + 1)):
        env = {k: v for k, v in os.environ.items() if k not in ("NPY_DISABLE_CPU_FEATURES", "GLIBC_TUNABLES")}
        env.update(NIVEIS[nivel])
        env.update({"OMP_NUM_THREADS": str(th), "OPENBLAS_NUM_THREADS": str(th), "MKL_NUM_THREADS": str(th),
                    "PYTHONWARNINGS": "ignore"})
        npy = tmp / f"{tec}-{nivel}-t{th}-r{rep}.npz"
        r = subprocess.run([sys.executable, __file__, "--filho", tec, str(npy)], env=env,
                           capture_output=True, text=True, cwd=str(RAIZ))
        if r.returncode != 0:
            raise SystemExit(f"{tec}/{nivel}/t{th}: {r.stderr[-600:]}")
        d = json.loads(r.stdout.strip().splitlines()[-1])
        execucoes.append({"tecnica": tec, "nivel": nivel, "threads": th, "rep": rep, "npz": str(npy), **d})
        print(f"  {tec:6s} {nivel} t{th} r{rep}  cpu={''.join('1' if v else '0' for v in d['cpu'].values())}"
              f"  i16={_sha(json.dumps({g: v['i16'] for g, v in d['por_falante'].items()}, sort_keys=True).encode())[:12]}")

    veredito = {}
    for tec in TECNICAS:
        ex = [e for e in execucoes if e["tecnica"] == tec]
        ref = next(e for e in ex if e["nivel"] == "N0" and e["threads"] == 1 and e["rep"] == 1)
        ref_npz = np.load(ref["npz"])
        linhas, divergentes = [], []
        for e in ex:
            iguais = e["por_falante"] == ref["por_falante"]
            linha = {k: e[k] for k in ("nivel", "threads", "rep", "cpu")}
            linha["hash_i16"] = _sha(json.dumps({g: v["i16"] for g, v in e["por_falante"].items()},
                                                sort_keys=True).encode())
            linha["identico_a_N0"] = iguais
            if not iguais:
                npz = np.load(e["npz"])
                dif = max(float(np.max(np.abs(npz[g] - ref_npz[g]))) for g in ref_npz.files)
                linha["delta_max_dbfs"] = round(20 * np.log10(dif), 1) if dif > 0 else None
                divergentes.append(f"{e['nivel']}/t{e['threads']}")
            linhas.append(linha)
        veredito[tec] = {
            "execucoes": linhas,
            "hashes_distintos_i16": len({ln["hash_i16"] for ln in linhas}),
            "veredito": "estável entre classes" if not divergentes else "exige tolerância",
            "divergentes": sorted(set(divergentes)),
        }
    DESTINO.mkdir(parents=True, exist_ok=True)
    out = {"entrada_sha256": entrada, "niveis": NIVEIS, "tecnicas": veredito,
           "ambiente": {"python": sys.version.split()[0], "numpy": np.__version__}}
    (DESTINO / "estabilidade.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for tec, v in veredito.items():
        print(f"  {tec:6s} → {v['veredito']} ({v['hashes_distintos_i16']} hash(es) i16 distinto(s) em "
              f"{len(v['execucoes'])} execuções) {v['divergentes'] or ''}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--filho":
        filho(sys.argv[2], sys.argv[3])
    else:
        sys.exit(main())
