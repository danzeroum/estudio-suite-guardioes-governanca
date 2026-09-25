#!/usr/bin/env python3
"""O roteador da segunda onda automática (CP-015), provado com artefatos
sintéticos.

A decisão do dono (25/09/2026): "segunda onda automática quando a
primeira não tiver AVX-512; rerun humano deixa de ser o caminho de
volta". O roteador (ci/rotear_segunda_onda.py) é o job que olha a onda 1
e decide. A regra é UMA, e o teste a prova nos dois sentidos:

  - onda 1 com TODAS as cópias avx2 (legíveis, sem duplicatas) ->
    segunda_onda=TRUE (o sorteio não trouxe decisiva: tentar de novo NO
    MESMO RUN, sem humano)
  - qualquer outro estado -> FALSE: com AVX-512 (o agregador decide sobre
    o que existe), com artefato ausente/corrompido, com veredito
    impróprio, com classe indeterminada, com duplicata — a segunda onda
    NÃO existe para mascarar cópia ilegível
  - diretório de artefatos inteiro ausente -> saída 2 nomeada
    (ONDA_1_ILEGIVEL): sem rota, e o agregador reprovará as cópias
  - a saída vai ao $GITHUB_OUTPUT (é ela que acorda dublador-onda2) e ao
    rotear.json (artefato público)
  - artefatos da era CP-013/014 (sem campo onda) são lidos como onda 1
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ok, bad = [], []


def chk(c, msg):
    (ok if c else bad).append(msg)


def copia_veredito(copia, classe, veredito, onda=1,
                   cpu="AMD EPYC 9V74 80-Core Processor", detalhe="detalhe"):
    doc = {"copia": copia, "cpu": cpu, "classe": classe,
           "prova": ("bytes-pcm+codec-sob-teto" if classe == "avx512"
                     else "observacao-dispatch-manual"),
           "veredito": veredito, "detalhe": detalhe}
    if onda is not None:
        doc["onda"] = onda
    return doc


def montar(dir_raiz, docs):
    for i, doc in enumerate(docs):
        onda = doc.get("onda", 1)
        sub = dir_raiz / f"identidade-onda{onda}-{doc['copia']}-run1{i:03d}"
        sub.mkdir(parents=True, exist_ok=True)
        (sub / "veredito.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def rodar(artefatos, copias, com_output=False):
    import os
    env = dict(os.environ)
    outfile = None
    if com_output:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".out")
        f.close()
        env["GITHUB_OUTPUT"] = f.name
        outfile = Path(f.name)
    r = subprocess.run(
        [sys.executable, "ci/rotear_segunda_onda.py",
         "--artefatos", str(artefatos),
         "--copias", json.dumps(copias),
         "--saida", str(artefatos)],
        capture_output=True, text=True, cwd=RAIZ, env=env)
    gout = outfile.read_text() if outfile else None
    return r, gout


def caso(nome):
    return Path(tempfile.mkdtemp(prefix=f"rotear-{nome}-"))


def main():
    C8 = [f"copia-{i}" for i in range(1, 9)]

    # --- a aceite: sorteio limpo sem AVX-512 -> segunda onda ACORDA -----
    d = caso("r1")
    montar(d, [copia_veredito(f"copia-{i}", "avx2", "observacao")
               for i in range(1, 9)])
    r, gout = rodar(d, C8, com_output=True)
    chk(r.returncode == 0 and "ACORDA" in r.stdout,
        f"onda 1 com 8/8 avx2 -> segunda onda ACORDA (exit {r.returncode})")
    chk(gout is not None and gout.strip() == "segunda_onda=true",
        "a saída segunda_onda=true vai ao $GITHUB_OUTPUT — é ela que "
        "acorda dublador-onda2 no workflow")
    rot = json.loads((d / "rotear.json").read_text())
    chk(rot["segunda_onda"] is True and not rot["problemas"]
        and not rot["avx512_na_onda_1"],
        "o rotear.json declara a decisão (true), zero problemas e zero "
        "AVX-512 — o artefato público da rota")

    # --- com AVX-512 idêntica -> NÃO acorda (o agregador decide) --------
    d = caso("r2")
    docs = ([copia_veredito("copia-4", "avx512", "identica")] +
            [copia_veredito(f"copia-{i}", "avx2", "observacao")
             for i in range(1, 9) if i != 4])
    montar(d, docs)
    r, gout = rodar(d, C8, com_output=True)
    chk(r.returncode == 0 and "não acorda" in r.stdout,
        f"onda 1 com 1 AVX-512 -> segunda onda NÃO acorda (exit "
        f"{r.returncode}): não há falta de amostra")
    chk(gout.strip() == "segunda_onda=false",
        "a saída segunda_onda=false vai ao $GITHUB_OUTPUT")

    # --- avx512 que não provou -> NÃO acorda (ilegível não vira sorte) --
    d = caso("r3")
    docs = ([copia_veredito("copia-2", "avx512", "nao-provou",
                            detalhe="NAO MEDIDO — prova.json ausente")] +
            [copia_veredito(f"copia-{i}", "avx2", "observacao")
             for i in range(1, 9) if i != 2])
    montar(d, docs)
    r, _ = rodar(d, C8)
    rot = json.loads((d / "rotear.json").read_text())
    chk(r.returncode == 0 and rot["segunda_onda"] is False
        and "copia-2" in " ".join(rot["avx512_na_onda_1"])
        and "não há falta de amostra" in rot["motivo"],
        "avx512 nao-provou -> NÃO acorda: a cópia decisiva ESTÁ na onda "
        "(o agregador é quem nomeia o nao-provou — a segunda onda não "
        "existe para dar outra sorte a uma prova que não rodou)")

    # --- artefato ausente -> NÃO acorda ----------------------------------
    d = caso("r4")
    montar(d, [copia_veredito(f"copia-{i}", "avx2", "observacao")
               for i in range(1, 7)])
    r, _ = rodar(d, C8)
    rot = json.loads((d / "rotear.json").read_text())
    chk(r.returncode == 0 and rot["segunda_onda"] is False
        and any("SEM ARTEFATO" in p for p in rot["problemas"]),
        "cópia esperada sem artefato -> NÃO acorda (run que não entregou "
        "não é sorteio da frota)")

    # --- duplicada -> NÃO acorda -----------------------------------------
    d = caso("r5")
    doc1 = copia_veredito("copia-1", "avx2", "observacao")
    for nome in ("identidade-onda1-copia-1-run1",
                 "identidade-onda1-copia-1-run2-tentativa"):
        sub = d / nome
        sub.mkdir(parents=True)
        (sub / "veredito.json").write_text(
            json.dumps(doc1, ensure_ascii=False), encoding="utf-8")
    r, _ = rodar(d, ["copia-1"])
    rot = json.loads((d / "rotear.json").read_text())
    chk(r.returncode == 0 and rot["segunda_onda"] is False
        and any("DUPLICADO" in p for p in rot["problemas"]),
        "cópia com dois artefatos (retry) -> NÃO acorda, problema nomeado")

    # --- veredito impróprio de avx2 -> NÃO acorda ------------------------
    d = caso("r6")
    montar(d, [copia_veredito("copia-1", "avx2", "divergente")])
    r, _ = rodar(d, ["copia-1"])
    rot = json.loads((d / "rotear.json").read_text())
    chk(rot["segunda_onda"] is False
        and any("impróprio" in p for p in rot["problemas"]),
        "avx2 com veredito impróprio -> NÃO acorda, problema nomeado")

    # --- classe indeterminada -> NÃO acorda ------------------------------
    d = caso("r7")
    montar(d, [copia_veredito("copia-1", "indeterminada", "indeterminada")])
    r, _ = rodar(d, ["copia-1"])
    rot = json.loads((d / "rotear.json").read_text())
    chk(rot["segunda_onda"] is False
        and any("indeterminada" in p for p in rot["problemas"]),
        "classe indeterminada -> NÃO acorda")

    # --- corrompido -> NÃO acorda ----------------------------------------
    d = caso("r8")
    sub = d / "identidade-onda1-copia-1-run1"
    sub.mkdir(parents=True)
    (sub / "veredito.json").write_text("{não é json", encoding="utf-8")
    r, _ = rodar(d, ["copia-1"])
    rot = json.loads((d / "rotear.json").read_text())
    chk(rot["segunda_onda"] is False
        and any("corrompido" in p for p in rot["problemas"]),
        "veredito.json corrompido -> NÃO acorda, problema nomeado")

    # --- estrutural: nem ler a onda 1 -> saída 2 nomeada -----------------
    d = caso("r9") / "nao-existe"
    r, _ = rodar(d, C8)
    chk(r.returncode == 2 and "ONDA_1_ILEGIVEL" in r.stderr,
        f"diretório de artefatos ausente -> saída 2 nomeada (exit "
        f"{r.returncode}): sem rota, e o agregador reprovará SEM ARTEFATO")

    # --- legado: artefatos sem o campo onda -> onda 1 -------------------
    d = caso("r10")
    montar(d, [copia_veredito(f"copia-{i}", "avx2", "observacao",
                              onda=None) for i in range(1, 9)])
    r, gout = rodar(d, C8, com_output=True)
    chk(r.returncode == 0 and gout.strip() == "segunda_onda=true",
        "artefatos da era CP-013/014 (sem campo onda) são lidos como "
        "onda 1 e decidem normalmente")

    # --- o contrato estrutural no dublador.yml ---------------------------
    wf = (RAIZ / ".github" / "workflows" / "dublador.yml").read_text(
        encoding="utf-8")
    chk("ci/rotear_segunda_onda.py" in wf
        and "identidade-onda1-*" in wf,
        "o workflow chama o roteador baixando os artefatos da ONDA 1")
    chk("if: needs.rotear.outputs.segunda_onda == 'true'" in wf,
        "a onda 2 acorda PELA SAÍDA do roteador — a regra tem um só dono")
    chk("if: always() && needs.planejar.outputs.rodar == 'true'" in wf
        and "needs: [planejar, dublador-onda1]" in wf,
        "o roteador roda sempre que o job acordou (cópia vermelha também "
        "— ele roteia, o agregador sentencia)")
    trecho_rot = wf[wf.index("O roteador da segunda onda"):]
    trecho_rot = trecho_rot[:trecho_rot.index("Publicar a rota")]
    chk("mkdir -p /tmp/rotear" in trecho_rot
        and trecho_rot.index("mkdir -p /tmp/rotear")
        < trecho_rot.index("rotear.log"),
        "o passo do roteador cria o diretório ANTES do tee — a corrida do "
        "run 36101113176 (o tee abriu o log antes de o script criar o "
        "diretório e derrubou o passo com o roteador já decidido certo) "
        "não pode voltar")

    print(f"  {len(ok)} verificações do roteador da segunda onda (CP-015).")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  a segunda onda acorda SÓ para o sorteio limpo sem AVX-512: "
          "ilegível")
    print("  não vira sorte, e o caminho de volta automático mora no "
          "próprio run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
