#!/usr/bin/env python3
"""Os pins do voz.lock, provados nos dois sentidos (CP-008).

O contrato do ci/pins_do_lock.py e curto e tenso: o voz.lock e a UNICA
fonte de versoes, e quem monta ambiente (workflow, imagem) nao digita
numero nenhum. Aqui se provam os tres modos -- pins pip, a serie do
python, e a conferencia do ambiente medido -- e as duas formas de o
pedido nao ter resposta: pacote sem ancora no lock (saida 2, nomeado) e
chave que nao e pacote pip (saida 2, nomeando a confusao). E a
divergencia: o ambiente medido que nao bate com a ancora derruba o passo
com nome e versao -- nunca em silencio.

CP-009: o quarto modo e o NUMERO DE THREADS (--threads), para o
--build-arg da imagem e o ENV do job. A resposta e o valor ancorado
(2 — mudanca de 1 para 2 medida nas 42 falas reais, registrada na
CP-009); valor digitado na chamada e recusado (o numero vem do lock);
threads nao e pin pip (e a sessao do onnxruntime); lock SEM threads e
pergunta sem resposta, saida 2 nomeando o lock incompleto.

CP-013: o quinto modo e a AMOSTRAGEM DA FROTA (--amostragem-n): o N
de copias de cada disparo, DERIVADO da fracao medida (o menor N com
P(nenhuma copia AVX-512) <= 2%). O calculo e REPRODUZIDO aqui a
partir do registro (harness/frota/execucoes.json — todas as execucoes
com lscpu das CPs 009/011/012) e conferido contra o valor do lock: o
numero e reproduzivel, nao afirmado. Lock sem o bloco frota e lock
INCOMPLETO (saida 2 nomeando) — o workflow nunca chuta o tamanho da
matrix. E o teste structura o mesmo contrato no dublador.yml: o N vem
do lock, nunca digitado no YAML.
"""
import importlib.util
import io
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# O modulo mora em ci/ (sem __init__): carregado por caminho, como o que
# ele e -- um executavel do gate, nao um pacote da suite.
_spec = importlib.util.spec_from_file_location(
    "pins_do_lock", RAIZ / "ci" / "pins_do_lock.py")
pins_do_lock = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pins_do_lock)

ok, bad = [], []


def chk(c, msg):
    (ok if c else bad).append(msg)


def _cli(*args):
    return subprocess.run([sys.executable, "ci/pins_do_lock.py", *args],
                          capture_output=True, text=True, cwd=RAIZ)


def main():
    # --- os pins pip: exatamente o que o lock ancora ---------------------
    r = _cli("--so", "numpy,scipy")
    chk(r.returncode == 0 and r.stdout.strip() == "numpy==2.1.3 scipy==1.14.1",
        f"--so numpy,scipy -> 'numpy==2.1.3 scipy==1.14.1' "
        f"(exit {r.returncode}, {r.stdout.strip()!r})")
    r = _cli("--so", "piper-tts,onnxruntime,numpy,scipy")
    chk(r.returncode == 0 and "piper-tts==1.8.0" in r.stdout
        and "onnxruntime==1.30.0" in r.stdout,
        f"--so estendido serve a imagem dubladora ({r.stdout.strip()!r})")

    # --- pacote ausente no lock: saida 2, nomeado ------------------------
    r = _cli("--so", "inexistente")
    chk(r.returncode == 2 and "inexistente" in r.stderr,
        f"pacote ausente no lock: saida 2 nomeando o pedido "
        f"(exit {r.returncode}, {r.stderr.strip()[:80]!r})")

    # --- chave que nao e pacote pip: saida 2, nomeando a confusao --------
    r = _cli("--so", "espeak-ng")
    chk(r.returncode == 2 and "espeak-ng" in r.stderr and "pip" in r.stderr,
        f"espeak-ng nao e pin pip (vem embutido no wheel): "
        f"saida 2 nomeando ({r.stderr.strip()[:80]!r})")

    # --- a serie do python do lock, para o setup-python ------------------
    r = _cli("--python")
    chk(r.returncode == 0 and r.stdout.strip() == "3.12",
        f"--python -> 3.12 (exit {r.returncode}, {r.stdout.strip()!r})")

    # --- CP-009: o numero de threads da ancora, para o build-arg da imagem --
    # Quem monta a imagem pergunta AQUI, nao decora do lock; a resposta e o
    # valor ancorado (2, o regime da maquina que sintetizou os publicados --
    # medido nas 42 falas reais, mudanca de 1 para 2 registrada na CP-009).
    from estudio_suite import voz as _voz
    r = _cli("--threads")
    _ancora = _voz.ancora()["ambiente"]["threads"]
    chk(r.returncode == 0 and r.stdout.strip() == "2" and r.stdout.strip() == str(_ancora),
        f"--threads -> 2 == ancora do lock (exit {r.returncode}, "
        f"{r.stdout.strip()!r})")

    # --threads nao aceita valor digitado: o numero vem do lock, de nenhum
    # outro lugar -- passar valor e exatamente o defeito que a CP-009 fecha
    r = _cli("--threads", "4")
    chk(r.returncode == 64 and "nao recebe valor" in r.stderr,
        f"--threads com valor e recusado (exit {r.returncode}, {r.stderr.strip()[:60]!r})")

    # threads nao e pacote pip: pedir pin e a confusao nomeada
    r = _cli("--so", "threads")
    chk(r.returncode == 2 and "threads" in r.stderr and "pip" in r.stderr,
        f"threads nao e pin pip (e a sessao do onnxruntime): "
        f"saida 2 nomeando ({r.stderr.strip()[:80]!r})")

    # --- lock sem threads: o pedido nao tem resposta, e a falta e nomeada --
    # In process, com o LOCK trocado: a CLI roda num subprocess que so ve o
    # lock real -- aqui o modulo carregado e quem pergunta.
    import tempfile as _tf
    _lock_real = _voz.LOCK
    with _tf.TemporaryDirectory() as _tmp:
        sem_threads = Path(_tmp) / "voz.lock"
        sem_threads.write_text(
            _lock_real.read_text(encoding="utf-8").replace("  threads: 2\n", ""),
            encoding="utf-8")
        _voz.LOCK = sem_threads
        try:
            saida, erro = io.StringIO(), io.StringIO()
            with redirect_stdout(saida), redirect_stderr(erro):
                rc = pins_do_lock.main(["--threads"])
            chk(rc == 2 and "threads" in erro.getvalue()
                and "INCOMPLETO" in erro.getvalue(),
                f"lock sem threads: saida 2 nomeando o lock incompleto "
                f"(rc {rc}, {erro.getvalue().strip()[:80]!r})")
        finally:
            _voz.LOCK = _lock_real

    # --- CP-013: a amostragem da frota — o N do lock --------------------
    # O job dublador dispara N copias por disparo; o N vem do bloco frota
    # do lock (derivado da fracao medida). A chamada aqui so pergunta.
    from estudio_suite import voz as _voz_frota
    r = _cli("--amostragem-n")
    _n_lock = int(_voz_frota.frota()["amostragem"])
    chk(r.returncode == 0 and r.stdout.strip() == str(_n_lock),
        f"--amostragem-n -> {_n_lock} == frota.amostragem do lock "
        f"(exit {r.returncode}, {r.stdout.strip()!r})")

    # --amostragem-n com valor e recusado: o N vem do lock, de nenhum outro
    # lugar — o workflow montar matrix com numero proprio e o defeito que
    # a CP-013 fecha (o chute substituiria a medicao da frota)
    r = _cli("--amostragem-n", "12")
    chk(r.returncode == 64 and "nao recebe valor" in r.stderr,
        f"--amostragem-n com valor e recusado (exit {r.returncode}, "
        f"{r.stderr.strip()[:60]!r})")

    # --- o calculo de N reproduz o valor do lock a partir do registro ---
    # A aceite da CP-013: "o calculo de N reproduz o valor do lock a partir
    # das execucoes registradas" — fracao medida, menor N com P(zero
    # avx512) <= 2%, tudo lido de harness/frota/execucoes.json.
    import json as _json
    _frota = _json.loads((RAIZ / "harness" / "frota" / "execucoes.json")
                         .read_text(encoding="utf-8"))["execucoes"]
    _teto = float(_voz_frota.frota().get("p_zero_2pct", "0.02"))

    def _n_minimo(regs):
        p = sum(1 for x in regs if x["avx512f"]) / len(regs)
        n = 1
        while (1 - p) ** n > _teto:
            n += 1
        return n, p

    _n_calc, _p = _n_minimo(_frota)
    _fracao = _voz_frota.frota()["fracao_avx512f"]
    chk(_n_calc == _n_lock,
        f"o N recalculado do registro ({_n_calc}, p={_p:.5f} = "
        f"{sum(1 for x in _frota if x['avx512f'])}/{len(_frota)}) == o do "
        f"lock ({_n_lock}) — P(zero)={((1 - _p) ** _n_calc):.5f} <= {_teto}")
    chk(_fracao == f"{sum(1 for x in _frota if x['avx512f'])}/{len(_frota)}",
        f"a fracao do lock ({_fracao}) e a do registro "
        f"({sum(1 for x in _frota if x['avx512f'])}/{len(_frota)})")
    _sem_canceladas = [x for x in _frota if not x.get("cancelada")]
    _n_alt, _ = _n_minimo(_sem_canceladas)
    chk(_n_alt == _n_lock,
        f"sem as 25 copias canceladas o N continua {_n_alt} == lock — a "
        f"decisao de inclui-las nao move o numero ( registrado na CP-013)")
    chk(len(_frota) >= 90,
        f"o registro carrega a frota inteira ({len(_frota)} execucoes — "
        f"CP-009 8 + CP-011 28 + CP-012 61, canceladas inclusas)")

    # --- lock sem o bloco frota: pergunta sem resposta, falta nomeada -----
    _lock_real2 = _voz_frota.LOCK
    with _tf.TemporaryDirectory() as _tmp2:
        sem_frota = Path(_tmp2) / "voz.lock"
        sem_frota.write_text(
            _lock_real2.read_text(encoding="utf-8").replace("frota:\n", "frota-removido:\n"),
            encoding="utf-8")
        _voz_frota.LOCK = sem_frota
        try:
            saida, erro = io.StringIO(), io.StringIO()
            with redirect_stdout(saida), redirect_stderr(erro):
                rc = pins_do_lock.main(["--amostragem-n"])
            chk(rc == 2 and "frota" in erro.getvalue()
                and "INCOMPLETO" in erro.getvalue(),
                f"lock sem frota: saida 2 nomeando o lock incompleto "
                f"(rc {rc}, {erro.getvalue().strip()[:80]!r})")
        finally:
            _voz_frota.LOCK = _lock_real2

    # --- o dublador.yml nao digita o N: pergunta ao lock -----------------
    wf_dub = (RAIZ / ".github" / "workflows" / "dublador.yml").read_text(
        encoding="utf-8")
    import re as _re2
    chk("--amostragem-n" in wf_dub,
        "o dublador.yml le o N do lock (pins_do_lock.py --amostragem-n)")
    chk(not _re2.search(r"inputs\.rodadas|RODADAS", wf_dub)
        and "inputs:\n      rodadas:" not in wf_dub,
        "nenhum input/env de rodadas no dublador.yml — a matrix nasce do "
        "lock (as 'rodadas' de DUBLAGEM internas, 1 e 2, seguem existindo)")

    # --- a conferencia do ambiente: conforme -----------------------------
    r = _cli("--conferir", "python,numpy,scipy")
    chk(r.returncode == 0 and r.stdout.count("[ok]") == 3
        and "fora desta conferencia" in r.stdout,
        f"ambiente conforme: tres [ok] e o que ficou fora, nomeado "
        f"(exit {r.returncode})")

    # --- a conferencia divergente: derruba com nome e versao -------------
    # O ambiente_instalado e trocado IN PROCESS (o mesmo caminho que o
    # dublar conferiria): numpy mentindo 9.9.9 contra a ancora 2.1.3.
    from estudio_suite import voz as _voz
    _instalado_real = _voz.ambiente_instalado

    def _mentindo():
        return dict(_instalado_real(), numpy="9.9.9")

    _voz.ambiente_instalado = _mentindo
    try:
        saida, erro = io.StringIO(), io.StringIO()
        with redirect_stdout(saida), redirect_stderr(erro):
            rc = pins_do_lock.conferir(["python", "numpy", "scipy"])
        chk(rc == 1 and "numpy" in erro.getvalue()
            and "2.1.3" in erro.getvalue() and "9.9.9" in erro.getvalue(),
            f"ambiente divergente: saida 1 nomeando chave, ancora e medido "
            f"(rc {rc}, {erro.getvalue().strip()[:80]!r})")
        chk("[ok]" in saida.getvalue() and "DIVERGE" in saida.getvalue(),
            "e a tabela imprime o que esta ok e o que divergia, junto")
    finally:
        _voz.ambiente_instalado = _instalado_real

    # --- chave pedida que o lock nao ancora: saida 2 ----------------------
    saida, erro = io.StringIO(), io.StringIO()
    with redirect_stdout(saida), redirect_stderr(erro):
        rc = pins_do_lock.conferir(["nao-existe-no-lock"])
    chk(rc == 2 and "nao-existe-no-lock" in erro.getvalue(),
        f"conferir chave sem ancora: saida 2 nomeando (rc {rc})")

    # --- o lock e a unica fonte: nada de versao no workflow --------------
    # O contrato maior: se alguem digitar versao no suite.yml, este teste
    # acusa -- o workflow tem de perguntar ao lock, nao decorar dele.
    wf = (RAIZ / ".github" / "workflows" / "suite.yml").read_text(encoding="utf-8")
    digitadas = []
    for padrao, nome in ((r"python-version:\s*'?\d", "python-version"),
                         (r"pip install[^\n]*numpy[=><~\d]", "numpy"),
                         (r"pip install[^\n]*scipy[=><~\d]", "scipy")):
        import re as _re
        if _re.search(padrao, wf):
            digitadas.append(nome)
    chk(not digitadas,
        f"nenhuma versao de python/numpy/scipy digitada a mao no suite.yml ({digitadas})")

    print(f"  {len(ok)} verificacoes dos pins do lock.")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  o lock e a unica fonte: CI e imagem perguntam, nao decoram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
