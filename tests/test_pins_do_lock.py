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
