#!/usr/bin/env python3
"""O atualizador do registro da frota (CP-015, passo 5), provado com
agregados sintéticos.

A aceite é literal:
  - o script JUNTA os agregados baixados no registro versionado:
    entradas novas são acrescentadas, com o cp da era e a fonte declarada
  - deduplicação por run+tentativa: o mesmo run baixado duas vezes não
    entra duas vezes; o rerun de um run vira TENTATIVA nova, entrada própria
  - entrada inválida (n != len(copias), avx512 != contado, sem_amostra
    incoerente) é REJEITADA nomeada — o registro não cresce com lixo
  - a ordem do registro é CRONOLÓGICA (por quando)
  - o bloco "calculo" é REGRAVADO pelo mesmo caminho do teste
    (ci/independencia.calcular_do_registro) — o número é recalculável
  - --dry-run calcula e imprime SEM escrever
  - zip baixado da API (agregado-frota-runX.zip) é lido direto
  - sem nenhum agregado legível: saída 2 e o registro intocado
"""
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


def entrada(run, tent, quando, n, avx, ondas=1, sem=None, pref=""):
    copias = {}
    for i in range(n):
        chave = f"{pref}copia-{i+1}"
        copias[chave] = ("avx512" if i < avx else "avx2")
    return {"run": str(run), "tentativa": tent, "head": "abc12345",
            "evento": "pull_request", "quando": quando, "n": n,
            "ondas": ondas, "copias": copias, "avx512": avx,
            "sem_amostra_decisiva": (avx == 0 if sem is None else sem),
            "fonte": "agregado.json de teste"}


def agregado(reg, veredito="verde — teste"):
    return {"prova": "agregador-frota", "cp": "CP-013",
            "veredito": veredito, "registro": reg}


def registro_base(execs):
    return {"$schema": "estudio-suite/frota-gate@1",
            "descricao": "registro de teste",
            "como_cresce": "por PR de manutenção, sem commit automático",
            "execucoes": execs,
            "calculo": {}}


def rodar(artefatos, registro, dry=False, cp="CP-015"):
    cmd = [sys.executable, "ci/atualizar_registro_frota.py",
           "--artefatos", str(artefatos), "--cp", cp,
           "--registro", str(registro)]
    if dry:
        cmd.append("--dry-run")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ)


def main():
    # --- a base: 2 execuções registradas --------------------------------
    base = [entrada(111, 1, "2026-09-24T10:00:00Z", 8, 2),
            entrada(222, 1, "2026-09-24T11:00:00Z", 8, 0)]
    tmp = Path(tempfile.mkdtemp(prefix="atual-"))
    regp = tmp / "execucoes-gate.json"
    regp.write_text(json.dumps(registro_base(base), indent=1),
                    encoding="utf-8")

    # --- o agregado novo (zip, como a API entrega) + um já registrado ---
    arts = tmp / "arts"
    arts.mkdir()
    with zipfile.ZipFile(arts / "agregado-frota-run333.zip", "w") as z:
        z.writestr("agregado.json",
                   json.dumps(agregado(entrada(333, 1, "2026-09-25T09:00:00Z",
                                               8, 3))))
    (arts / "agregado-frota-run111").mkdir()
    (arts / "agregado-frota-run111" / "agregado.json").write_text(
        json.dumps(agregado(entrada(111, 1, "2026-09-24T10:00:00Z", 8, 2))),
        encoding="utf-8")

    # dry-run: não escreve
    antes = regp.read_text()
    r = rodar(arts, regp, dry=True)
    chk(r.returncode == 0 and regp.read_text() == antes,
        f"--dry-run calcula sem escrever (exit {r.returncode})")
    chk("run 333 t1" in r.stdout and "entradas NOVAS: 1" in r.stdout,
        "o dry-run imprime o que entraria: run 333 t1")

    # real: acrescenta 333, ignora 111 (já registrado)
    r = rodar(arts, regp)
    doc = json.loads(regp.read_text())
    chk(r.returncode == 0 and len(doc["execucoes"]) == 3,
        f"o registro cresce de 2 para 3 entradas (exit {r.returncode})")
    chk([e["run"] for e in doc["execucoes"]] == ["111", "222", "333"]
        and doc["execucoes"][2]["cp"] == "CP-015",
        "a entrada nova entra em ordem cronológica com o cp da era")
    chk(any("já registradas" in r.stdout for _ in [1]) and
        "run 111 t1" in r.stdout,
        "o run 111 (já registrado) é apontado como ignorado — sem duplicar")
    chk(doc["execucoes"][2]["fonte"].startswith("agregado.json de"),
        "a fonte da entrada nova declara de onde veio")

    # o bloco calculo foi regravado pelo caminho único
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "independencia", RAIZ / "ci" / "independencia.py")
    ind = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(ind)
    calc = ind.calcular_do_registro(doc)
    chk(doc["calculo"] == calc,
        "o bloco calculo regravado == o recalculado por "
        "calcular_do_registro (o mesmo caminho do teste)")
    ja = doc["calculo"]["janela"]
    chk(ja["execucoes_na_janela"] == 3 and ja["janela_incompleta"] is True,
        "com 3 execuções e J do lock, a janela declara INCOMPLETA e usa "
        "todas — nunca inventa fração")
    frac = ja["fracao"]
    chk(frac == round((2 + 0 + 3) / 24, 5),
        f"a fração da janela soma as cópias das 3 execuções ({frac})")

    # --- deduplicação: o mesmo 333 de novo -> nada muda ------------------
    r = rodar(arts, regp)
    doc2 = json.loads(regp.read_text())
    chk(r.returncode == 0 and len(doc2["execucoes"]) == 3,
        "rodar de novo com o mesmo agregado não duplica NADA")

    # --- rerun vira tentativa nova --------------------------------------
    with zipfile.ZipFile(arts / "agregado-frota-run222.zip", "w") as z:
        z.writestr("agregado.json",
                   json.dumps(agregado(entrada(222, 2, "2026-09-24T11:30:00Z",
                                               8, 4))))
    r = rodar(arts, regp)
    doc3 = json.loads(regp.read_text())
    chk(len(doc3["execucoes"]) == 4
        and any(e["run"] == "222" and e["tentativa"] == 2
                for e in doc3["execucoes"]),
        "o rerun do run 222 entra como TENTATIVA 2 — entrada própria")

    # --- entrada inválida é rejeitada nomeada ---------------------------
    inv = tmp / "invalidos"
    inv.mkdir()
    ruim = entrada(999, 1, "2026-09-25T12:00:00Z", 8, 3)
    ruim["copias"]["copia-9"] = "avx2"     # n=8 mas 9 cópias
    (inv / "um").mkdir()
    (inv / "um" / "agregado.json").write_text(json.dumps(agregado(ruim)),
                                                encoding="utf-8")
    ruim2 = entrada(998, 1, "2026-09-25T12:30:00Z", 8, 3)
    ruim2["sem_amostra_decisiva"] = True    # avx512=3 com SEM_AMOSTRA
    (inv / "dois").mkdir()
    (inv / "dois" / "agregado.json").write_text(json.dumps(agregado(ruim2)),
                                                 encoding="utf-8")
    r = rodar(inv, regp)
    doc4 = json.loads(regp.read_text())
    chk(len(doc4["execucoes"]) == 4
        and "n=8 != 9" in r.stdout and "incoerente" in r.stdout,
        "entradas inválidas são rejeitadas com o motivo nomeado e o "
        "registro não cresce com lixo")

    # --- entrada com DUAS ondas (o formato CP-015) -----------------------
    dup = tmp / "ondas2"
    dup.mkdir()
    reg2 = entrada(777, 1, "2026-09-25T13:00:00Z", 8, 0)   # onda 1: 8 avx2
    copias2 = {f"onda-1/{k}": v for k, v in reg2["copias"].items()}
    copias2["onda-2/copia-1"] = "avx512"                   # onda 2: 1 avx512
    for i in range(2, 9):
        copias2[f"onda-2/copia-{i}"] = "avx2"
    reg2.update({"copias": copias2, "n": 16, "ondas": 2, "avx512": 1,
                 "sem_amostra_decisiva": False})
    (dup / "agregado.json").write_text(json.dumps(agregado(reg2)),
                                        encoding="utf-8")
    r = rodar(dup, regp)
    doc5 = json.loads(regp.read_text())
    chk(len(doc5["execucoes"]) == 5
        and doc5["execucoes"][-1]["ondas"] == 2
        and doc5["execucoes"][-1]["n"] == 16
        and "onda-2/copia-1" in doc5["execucoes"][-1]["copias"],
        "a entrada com 2 ondas entra inteira: n=16, ondas=2, cópias "
        "prefixadas por onda")

    # --- sem nenhum agregado legível -> saída 2, registro intocado ------
    vazio = tmp / "vazio"
    vazio.mkdir()
    antes = regp.read_text()
    r = rodar(vazio, regp)
    chk(r.returncode == 2 and "nenhum agregado" in r.stderr
        and regp.read_text() == antes,
        f"diretório sem agregados -> saída 2 nomeada e o registro "
        f"INTOCADO (exit {r.returncode})")

    # --- o registro real do repo segue CONSISTENTE com o seu calculo ----
    real = json.loads((RAIZ / "harness" / "frota" /
                       "execucoes-gate.json").read_text(encoding="utf-8"))
    calc_real = ind.calcular_do_registro(real)
    chk(real["calculo"] == calc_real,
        f"o registro REAL do repo ({len(real['execucoes'])} execuções) "
        f"bate com o recalculo do calculo — nada é afirmado")
    chk("commit automático" in real["como_cresce"].lower(),
        "o registro real declara como cresce: por PR de manutenção")

    print(f"  {len(ok)} verificações do atualizador do registro (CP-015).")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  o registro cresce por PR de manutenção: deduplicado, "
          "ordenado,")
    print("  validado e com o calculo regravável pelo caminho único.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
