#!/usr/bin/env python3
"""A evidência e o veredito de determinismo da classe avx2 (CP-016,
proposta), provados com dados sintéticos — e, quando a evidência real
existe no repo, reconferidos do arquivo versionado.

A aceite da CP-016 é literal:
  - cópias avx2 de modelos e execuções DIFERENTES com o MESMO hash de
    PCM mixado por filme -> DETERMINISTICO_NA_CLASSE
  - um hash diferente -> NAO_DETERMINISTICO com a TABELA (run, cópia,
    modelo, hash — o ONDE, não só o que)
  - menos de 3 modelos distintos / menos de 5 execuções -> LIMITAÇÃO
    declarada, nunca escondida (a fronteira medida do pool é achado)
  - divergir da âNCORA commitada é o ESPERADO entre classes (CP-011) —
    o que se pergunta é a igualdade DENTRO da classe avx2
  - o coletor junta os artefatos por RUN (as cópias de um dispatch são
    uma execução), deduplica e cresce por PR
  - NADA disto é gate: o rótulo segue "observação, sem gate" e a CP
    segue estado PROPOSTA — a decisão de virar âncora é do dono
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ok, bad = [], []


def chk(c, msg):
    (ok if c else bad).append(msg)


def _spec(nome, caminho):
    s = importlib.util.spec_from_file_location(nome, RAIZ / "ci" / caminho)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


det = _spec("determinismo_avx2", "determinismo_avx2.py")
atu = _spec("atualizar_observacao_avx2", "atualizar_observacao_avx2.py")


def copia_doc(run, copia, cpu, hashes, status="ok"):
    """um observacao-avx2.json de cópia (o que o dispatch publica)."""
    return {"prova": "observacao-avx2", "rotulo": "observação, sem gate",
            "gate": False, "copia": copia, "classe": "avx2", "cpu": cpu,
            "run_id": str(run), "status": status,
            "filmes": [{"filme": fid, "hash_pcm_mixado": h}
                       for fid, h in hashes.items()]}


HASH_A = "a" * 64
HASH_B = "b" * 64
ANC_J = "j" * 64
ANC_L = "l" * 64


def hashes(j=HASH_A, l=HASH_B, anc_j=ANC_J, anc_l=ANC_L):
    return {"jornada-dado": {"regenerado_avx2": j,
                             "ancora_commitada": anc_j},
            "legitimo-interesse": {"regenerado_avx2": l,
                                   "ancora_commitada": anc_l}}


def main():
    # --- a aceite: mesmo hash entre modelos e execuções ---------------
    ev = {"execucoes": [
        {"run": "1", "copias": [
            {"copia": "copia-2", "cpu": "AMD EPYC 7763", "status": "ok",
             "filmes": hashes()},
            {"copia": "copia-5", "cpu": "AMD EPYC 9V74", "status": "ok",
             "filmes": hashes()}]},
        {"run": "2", "copias": [
            {"copia": "copia-1", "cpu": "AMD EPYC 7763", "status": "ok",
             "filmes": hashes()},
            {"copia": "copia-3", "cpu": "AMD EPYC 9V74", "status": "ok",
             "filmes": hashes()}]}]}
    calc = det.calcular(ev)
    chk(calc["veredito"] == "DETERMINISTICO_NA_CLASSE",
        "mesmo hash por filme entre cópias/modelos/execuções -> "
        "DETERMINISTICO_NA_CLASSE")
    chk(all(len(f["hashes_distintos"]) == 1 for f in calc["filmes"].values()),
        "cada filme tem UM hash distinto na classe")
    chk(calc["filmes"]["jornada-dado"]["diverge_da_ancora"] is True
        and calc["filmes"]["jornada-dado"]["ancora_commitada"] == ANC_J,
        "a âncora commitada é conferida junto — e divergir DELA é o "
        "esperado entre classes (CP-011), registrado como dado")
    chk(len(calc["modelos_de_cpu"]) == 2
        and any("2 modelos" in p for p in calc["limitacoes"]),
        "com 2 modelos a LIMITAÇÃO é declarada (a pergunta pede >= 3) — "
        "nunca escondida")
    chk(any("pede >= 5" in p for p in calc["limitacoes"]),
        "com 2 execuções a LIMITAÇÃO de execuções também é declarada")

    # --- a divergência: NAO_DETERMINISTICO com a tabela -----------------
    ev_div = {"execucoes": [
        {"run": "7", "copias": [
            {"copia": "copia-2", "cpu": "AMD EPYC 7763", "status": "ok",
             "filmes": hashes()},
            {"copia": "copia-6", "cpu": "AMD EPYC 9V74", "status": "ok",
             "filmes": hashes(j=HASH_A)},
            {"copia": "copia-8", "cpu": "Intel Xeon 8124M", "status": "ok",
             "filmes": hashes(j="c" * 64)}]}]}
    calc2 = det.calcular(ev_div)
    chk(calc2["veredito"] == "NAO_DETERMINISTICO",
        "um hash diferente no mesmo filme -> NAO_DETERMINISTICO")
    chk(any("copia-8" in d and "run 7" in d and "8124M" in d
            for d in calc2["divergencias"]),
        "a tabela nome run, cópia e modelo de quem divergiu (o ONDE)")
    chk(len(calc2["filmes"]["jornada-dado"]["hashes_distintos"]) == 2,
        "o filme divergente registra os DOIS hashes")
    chk(calc2["filmes"]["legitimo-interesse"]["hashes_distintos"] == [HASH_B],
        "o filme que não divergiu segue com UM hash — tabela por filme")

    # --- o coletor: junta por RUN, deduplica, dry-run -------------------
    tmp = Path(tempfile.mkdtemp(prefix="obs-"))
    evp = tmp / "observacao-avx2.json"
    arts = tmp / "arts"
    arts.mkdir()
    with zipfile.ZipFile(arts / "observacao-avx2-copia-2-run10.zip", "w") as z:
        z.writestr("observacao-avx2.json",
                   json.dumps(copia_doc(10, "copia-2", "AMD EPYC 7763",
                                        hashes())))
    with zipfile.ZipFile(arts / "observacao-avx2-copia-4-run10.zip", "w") as z:
        z.writestr("observacao-avx2.json",
                   json.dumps(copia_doc(10, "copia-4", "AMD EPYC 9V74",
                                        hashes())))
    r = subprocess.run(
        [sys.executable, "ci/atualizar_observacao_avx2.py",
         "--artefatos", str(arts), "--evidencia", str(evp), "--dry-run"],
        capture_output=True, text=True, cwd=RAIZ)
    chk(r.returncode == 0 and not evp.exists()
        and "cópias NOVAS: 2" in r.stdout,
        f"--dry-run calcula sem escrever (exit {r.returncode})")
    r = subprocess.run(
        [sys.executable, "ci/atualizar_observacao_avx2.py",
         "--artefatos", str(arts), "--evidencia", str(evp)],
        capture_output=True, text=True, cwd=RAIZ)
    doc = json.loads(evp.read_text())
    chk(r.returncode == 0 and len(doc["execucoes"]) == 1
        and len(doc["execucoes"][0]["copias"]) == 2,
        "as cópias do MESMO run formam UMA execução no coletor")
    chk(doc["execucoes"][0]["copias"][0]["cpu"] == "AMD EPYC 7763"
        and doc["execucoes"][0]["copias"][0]["filmes"]["jornada-dado"][
            "regenerado_avx2"] == HASH_A,
        "a cópia registra modelo e o sha256 por filme")
    r = subprocess.run(
        [sys.executable, "ci/atualizar_observacao_avx2.py",
         "--artefatos", str(arts), "--evidencia", str(evp)],
        capture_output=True, text=True, cwd=RAIZ)
    doc2 = json.loads(evp.read_text())
    chk(r.returncode == 0 and len(doc2["execucoes"]) == 1
        and "já registradas: 2" in r.stdout,
        "rodar de novo com os mesmos artefatos não duplica NADA")
    chk("por PR" in doc2["como_cresce"],
        "a evidência declara como cresce: por PR, sem commit automático")
    vazio = tmp / "vazio"
    vazio.mkdir()
    r = subprocess.run(
        [sys.executable, "ci/atualizar_observacao_avx2.py",
         "--artefatos", str(vazio), "--evidencia", str(evp)],
        capture_output=True, text=True, cwd=RAIZ)
    chk(r.returncode == 2 and "nenhum observacao" in r.stderr,
        f"sem artefato legível -> saída 2 nomeada (exit {r.returncode})")

    # --- o contrato estrutural: NADA disto é gate ------------------------
    obs = (RAIZ / "ci" / "observar_avx2.py").read_text(encoding="utf-8")
    chk("pcm_f32_sha256" in obs and "hash_pcm_mixado" in obs
        and "CPU_MODELO" in obs,
        "o ci/observar_avx2.py REGISTRA o sha256 do PCM mixado por filme e "
        "o modelo de CPU — o MESMO campo que o gate lê, como observação")
    chk("observação, sem gate" in obs,
        "o rótulo segue 'observação, sem gate' — nada reprova/valida")
    wfo = (RAIZ / ".github" / "workflows" / "observar-avx2.yml").read_text(
        encoding="utf-8")
    chk("workflow_dispatch" in wfo,
        "o dispatch manual seguir existe (a observação paga o build quando "
        "é pedida)")
    # a CP segue PROPOSTA e não toca o desenho do gate
    cp = (RAIZ / "harness" / "change-proposals" /
          "CP-016-ancora-avx2.yaml").read_text(encoding="utf-8")
    chk("estado: proposta" in cp and "REVISAO_NECESSARIA" in cp,
        "a CP-016 está em estado PROPOSTA com a parada de decisão do dono")
    # a regra dura: nada de gate/lock/audio.json muda NESTA branch — provado
    # pelo diff contra o main (merge-base), não por promessa
    import subprocess as _sp
    dif = _sp.run(["git", "diff", "--name-only", "origin/main...HEAD"],
                  capture_output=True, text=True, cwd=RAIZ)
    tocados = [l.strip() for l in (dif.stdout or "").splitlines() if l.strip()]
    proibidos = [p for p in tocados if (
        p in ("voz.lock", "amostras.lock",
              ".github/workflows/dublador.yml",
              ".github/workflows/dublador-onda.yml")
        or p.startswith(("estudio_suite/", "ferramentas/dublador/"))
        or (p.startswith("filmes/") and p.endswith("audio.json")))]
    chk(dif.returncode == 0 and not proibidos,
        f"o diff da CP-016 contra o main NÃO toca gate/lock/audio.json "
        f"({len(tocados)} arquivos, zero proibido) — a decisão de virar "
        f"âncora é do dono, e a regra está provada no diff, não prometida")

    # --- a evidência REAL (se commitada): reconferida --------------------
    real = RAIZ / "harness" / "frota" / "observacao-avx2.json"
    if real.exists():
        doc_real = json.loads(real.read_text(encoding="utf-8"))
        calc_real = det.calcular(doc_real)
        chk(doc_real.get("veredito") is None or
            doc_real.get("veredito", {}).get("veredito")
            == calc_real["veredito"],
            f"a evidência real ({calc_real['execucoes']} execuções, "
            f"{len(calc_real['modelos_de_cpu'])} modelos) reconferida: "
            f"veredito {calc_real['veredito']} — recalculável, nunca "
            f"afirmado")

    print(f"  {len(ok)} verificações do determinismo avx2 (CP-016, proposta).")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  a pergunta está medida com número e o veredito é recalculado;")
    print("  a decisão de virar âncora fica com o dono — proposta aberta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
