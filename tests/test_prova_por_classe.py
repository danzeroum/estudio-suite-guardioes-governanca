#!/usr/bin/env python3
"""A prova por classe de SIMD, provada nos dois sentidos (CP-011).

O contrato em quatro frentes, todas exigidas pela CP:

  CLASSIFICADOR: flags de lscpu sintéticas (Intel com avx512f; AMD sem
  avx512f; AMD COM avx512f) -> classes esperadas. A chave é a FLAG, não o
  fabricante — o dia em que um AMD com avx512f divergir, a chave ganha
  mais uma flag por MEDIÇÃO (CLASSE_MAL_DEFINIDA), nunca por precaução.
  Flags ausentes -> recusa nomeada, nunca palpite.

  RESÍDUO: PCM idêntico -> -inf dBFS e passa; ruído injetado 6 dB acima
  do teto -> reprova COM O NÚMERO. O resíduo é o que sobra quando a
  hipótese é "mesmo som": sem número não existe tolerância.

  FILTRO: filme sem declaração de áudio -> fora da lista do job; filme
  com áudio -> dentro. A declaração mora no próprio filme.js, nunca em
  lista de nomes — e o dublar recusa quem não fala.

  BORDA: lock sem classe_simd -> dublar e job recusam ("lock
  incompleto"), como lock sem threads e sem arquitetura.

Roda em CI (numpy do lock, sem piper): tudo aqui é função pura ou dado
sintético — a síntese de verdade é da imagem dubladora.
"""
import importlib.util
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import voz                                # noqa: E402
from estudio_suite.comum import ErroDeDados, FILMES, filmes_com_audio  # noqa: E402

# O modulo da prova mora em ci/ (executável do gate): carregado por
# caminho, como o test_pins_do_lock faz com o pins_do_lock.
_spec = importlib.util.spec_from_file_location(
    "prova_por_classe", RAIZ / "ci" / "prova_por_classe.py")
prova = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prova)

ok, bad = [], []
FANTASMA = "teste-prova-classe-fantasma"


def chk(c, msg):
    (ok if c else bad).append(msg)


def _lscpu(flags: str, modelo="CPU sintética") -> str:
    return json.dumps({"lscpu": [
        {"field": "Model name:", "data": modelo},
        {"field": "Flags:", "data": flags},
    ]})


# flags reais resumidas dos runners medidos na CP-009 (tabela de 8)
_INTEL_8370C = ("fpu vme de pse tsc msr fma cx16 pcid sse4_1 sse4_2 x2apic "
                "movbe popcnt aes xsave avx f16c rdrand avx2 lahf_lm abm "
                "fsgsbase tsc_adjust bmi1 avx512f avx512dq avx512cd "
                "avx512bw avx512vl avx512_vnni avx512_bf16")
_AMD_EPYC_7763 = ("fpu vme de pse tsc msr fma cx16 pcid sse4_1 sse4_2 "
                  "x2apic movbe popcnt aes xsave avx f16c rdrand lahf_lm "
                  "cmp_legacy svm extapic cr8_legacy abm sse4a misalignsse "
                  "3dnowprefetch osvw ibs skinit wdt avx2")
# Zen 4 reporta avx512f no lscpu: a classe segue a FLAG, o fabricante não
_AMD_COM_AVX512 = _AMD_EPYC_7763 + " avx512f avx512bw avx512vl vpclmulqdq"


def _filme_fantasma(declara_audio):
    d = FILMES / FANTASMA
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    filme = {
        "id": FANTASMA, "titulo": "Fantasma da prova por classe", "duracao": 8,
        "planos": [{
            "id": "p01", "titulo": "T", "dur": 8, "guardiao": "coruja",
            "cenario": "vazio", "poster": 3, "arts": [], "entra": {},
            "legendas": [],
        }],
    }
    if declara_audio:
        filme["audio"] = True
    (d / f"{FANTASMA}.filme.js").write_text(
        "window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};"
        "window.ESTUDIO_FILMES[\"" + FANTASMA + "\"]=\n" +
        json.dumps(filme, ensure_ascii=False, indent=1) + "\n;\n", encoding="utf-8")
    return d


def main():
    # --- classificador: flags sintéticas, classes esperadas ---------------
    chk(voz.classe_simd_de_flags(voz.flags_do_lscpu_json(_lscpu(_INTEL_8370C)))
        == "avx512",
        "lscpu Intel Xeon 8370C (avx512f) -> avx512 (a classe que reproduz)")
    chk(voz.classe_simd_de_flags(voz.flags_do_lscpu_json(_lscpu(_AMD_EPYC_7763)))
        == "avx2",
        "lscpu AMD EPYC 7763 (sem avx512f) -> avx2 (a classe que divergia)")
    chk(voz.classe_simd_de_flags(voz.flags_do_lscpu_json(_lscpu(_AMD_COM_AVX512)))
        == "avx512",
        "AMD com avx512f -> avx512: a FLAG decide, o fabricante NÃO (se essa "
        "classe divergir, a chave ganha flag por medição — CLASSE_MAL_DEFINIDA)")
    # o parser não lê texto traduzido, e o campo Flags do JSON
    chk(voz.flags_do_lscpu_json('{"lscpu": [{"field": "Flags:", "data": "avx2"}]}')
        == {"avx2"},
        "parser do lscpu --json: campo Flags, determinístico")
    # /proc/cpuinfo: o fallback da imagem slim
    chk(voz.flags_do_proc_cpuinfo(
        "processor\t: 0\nvendor_id\t: x\nflags\t\t: fpu avx2 avx512f\n")
        >= {"avx2", "avx512f"},
        "parser do /proc/cpuinfo lê a linha flags (fallback da imagem)")
    # flags ausentes: recusa nomeada, nunca palpite
    for flags, rotulo in ((set(), "conjunto vazio"),
                           ({"fpu", "sse", "mmx"}, "flags sem SIMD moderno")):
        try:
            voz.classe_simd_de_flags(flags)
            chk(False, f"flags {rotulo} deviam ser RECUSA nomeada")
        except ErroDeDados as e:
            chk("classe indeterminada" in str(e) and "RECUSA" in str(e),
                f"flags {rotulo}: recusa nomeada ({str(e)[:60]}...)")
    chk(voz.flags_do_proc_cpuinfo("processor\t: 0\nsem flags\n") == set()
        and voz.flags_do_lscpu_json("{}") == set(),
        "parsers ilegíveis devolvem vazio — quem decide a recusa é o classificador")

    # --- resíduo de nulidade: -inf passa; ruído 6 dB acima reprova --------
    rng = np.random.default_rng(42)
    sinal = np.round(rng.standard_normal(22050) * 3000).astype(np.int16)
    chk(prova.residuo_dbfs(sinal, sinal) == float("-inf"),
        "PCM idêntico -> resíduo -inf dBFS")
    okr, fraser = prova.veredito_residuo(float("-inf"), -66.0)
    chk(okr and "-inf" in fraser and "-66" in fraser,
        f"-inf dBFS passa no teto e a frase carrega os números ({fraser})")
    # ruído com RMS 6 dB acima do teto: teto -66 -> ruído a -60 dBFS
    alvo = 10 ** (-60.0 / 20.0) * 32768.0
    ruido = rng.standard_normal(22050)
    ruido = np.round(ruido * (alvo / np.sqrt(np.mean(ruido * ruido)))).astype(np.int16)
    res = prova.residuo_dbfs(sinal, np.clip(
        sinal.astype(np.int32) + ruido.astype(np.int32), -32768, 32767).astype(np.int16))
    okr, fraser = prova.veredito_residuo(res, -66.0)
    chk(not okr and "ACIMA DO TETO" in fraser,
        f"ruído 6 dB acima do teto reprova COM O NÚMERO ({fraser})")
    chk(-60.6 < res < -59.4,
        f"o resíduo medido bate com o injetado (~-60 dBFS; mediu {res:.1f})")

    # --- durações por fala --------------------------------------------------
    falas = [{"plano": "p01", "em": 0.5, "ate": 5.5, "dur": 4.2, "voz": "narrador",
              "texto_sha256": "a" * 64},
             {"plano": "p02", "em": 6.0, "ate": 11.0, "dur": 3.1, "voz": "coruja",
              "texto_sha256": "b" * 64}]
    chk(prova.comparar_duracoes(falas, [dict(f) for f in falas]) == [],
        "durações idênticas por fala -> lista vazia (o verde)")
    com_dur_errada = [dict(f) for f in falas]
    com_dur_errada[1]["dur"] = 3.2
    dv = prova.comparar_duracoes(falas, com_dur_errada)
    chk(len(dv) == 1 and "p02" in dv[0] and "dur" in dv[0],
        f"duração divergente aponta a fala e o campo ({dv})")

    # --- filtro: a declaração mora no filme, não em lista de nomes --------
    try:
        _filme_fantasma(declara_audio=False)
        com_audio = list(filmes_com_audio())
        chk(FANTASMA not in com_audio,
            "filme SEM declaração de áudio -> fora da lista do job")
        chk("jornada-dado" in com_audio and "legitimo-interesse" in com_audio,
            f"filmes COM áudio -> dentro ({com_audio})")
        # dublar de filme mudo: recusa ANTES de qualquer síntese
        from estudio_suite import dublar as _dublar
        try:
            _dublar.dublar(FANTASMA)
            chk(False, "dublar de filme mudo devia recusar na entrada")
        except ErroDeDados as e:
            chk("nao declara audio" in str(e) and "audio: true" in str(e),
                f"dublar de filme mudo recusa nomeando a declaração ({str(e)[:60]}...)")
        # e o workflow não pode ter nome de filme escrito à mão
        wf = (RAIZ / ".github" / "workflows" / "dublador.yml").read_text(encoding="utf-8")
        chk("needs.planejar.outputs.filmes" in wf,
            "o job dubla a lista do planejar (lida dos filmes), não nomes fixos")
        chk("dublar.sh jornada-dado" not in wf and "dublar.sh legitimo" not in wf,
            "nenhum id de filme hardcoded no dublador.yml (lista de nomes é "
            "a segunda descrição que envelhece)")
    finally:
        shutil.rmtree(FILMES / FANTASMA, ignore_errors=True)

    # --- borda: lock sem classe_simd -> recusa nomeada ---------------------
    try:
        voz.conferir_classe({})
        chk(False, "lock sem classe_simd devia recusar")
    except ErroDeDados as e:
        chk("classe_simd" in str(e) and "INCOMPLETO" in str(e),
            f"lock sem classe_simd: recusa 'lock incompleto' ({str(e)[:60]}...)")
    try:
        voz.conferir_classe({"classe_simd": "avx2048"})
        chk(False, "classe desconhecida devia recusar")
    except ErroDeDados as e:
        chk("avx2048" in str(e) and "conhecida" in str(e),
            f"classe fora das conhecidas: recusa nomeada ({str(e)[:60]}...)")
    medida = voz.conferir_classe({"classe_simd": "avx512"})
    chk(medida in voz.CLASSES_SIMD,
        f"com ancora válida, devolve a classe MEDIDA da máquina ({medida}) — "
        f"a divergência não é recusa de síntese, é o gate que decide")

    # e o job recusa pela MESMA porta: pins_do_lock --classe-simd sem a linha
    import io
    from contextlib import redirect_stderr, redirect_stdout
    _spec_pins = importlib.util.spec_from_file_location(
        "pins_do_lock", RAIZ / "ci" / "pins_do_lock.py")
    pins = importlib.util.module_from_spec(_spec_pins)
    _spec_pins.loader.exec_module(pins)
    _lock_real = voz.LOCK
    with tempfile.TemporaryDirectory() as tmp:
        sem_classe = Path(tmp) / "voz.lock"
        sem_classe.write_text(
            _lock_real.read_text(encoding="utf-8").replace(
                "  classe_simd: avx512\n", ""),
            encoding="utf-8")
        voz.LOCK = sem_classe
        try:
            saida, erro = io.StringIO(), io.StringIO()
            with redirect_stdout(saida), redirect_stderr(erro):
                rc = pins.main(["--classe-simd"])
            chk(rc == 2 and "INCOMPLETO" in erro.getvalue(),
                f"job: pins --classe-simd com lock sem a linha -> saída 2 "
                f"nomeando o lock incompleto (rc {rc})")
        finally:
            voz.LOCK = _lock_real
    # o teto: sem bloco tolerancia, saída 2 nomeando (nunca tolerância sem número)
    saida, erro = io.StringIO(), io.StringIO()
    with redirect_stdout(saida), redirect_stderr(erro):
        rc = pins.main(["--teto-residuo"])
    tol = voz.tolerancia()
    if "residuo_max_dbfs" not in tol:
        chk(rc == 2 and "tolerancia" in erro.getvalue().lower(),
            f"sem bloco tolerancia: --teto-residuo sai 2 nomeando (rc {rc}) — "
            f"a tolerância nasce da medição, nunca antes dela")
    else:
        chk(rc == 0 and float(saida.getvalue().strip()) < -60.0,
            f"com tolerancia registrada: --teto-residuo imprime o teto do lock "
            f"({saida.getvalue().strip()} dBFS, abaixo de -60)")

    print(f"  {len(ok)} verificações da prova por classe.")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  a classe decide a prova; o teto decide a tolerância; e o número "
          "está sempre no veredito.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
