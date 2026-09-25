#!/usr/bin/env python3
"""O veredito de determinismo da classe avx2, RECALCULADO da evidência
versionada (CP-016, proposta — passo 2 do plano).

A pergunta da CP-016: "a síntese na classe avx2 é byte-determinística
entre modelos de CPU e execuções, a ponto de o audio.json carregar um
segundo hash de PCM (avx2) e tornar TODA cópia decisiva?"

Este script lê harness/frota/observacao-avx2.json (a evidência que
ci/atualizar_observacao_avx2.py mantém: por execução, por cópia, o
modelo de CPU e o sha256 do PCM mixado por filme — o MESMO campo
mix.pcm_f32_sha256 que o gate lê na classe avx512) e responde:

  DETERMINISTICO_NA_CLASSE   todos os hashes regenerado_avx2 de um
                             MESMO filme são IGUAIS entre cópias,
                             modelos e execuções (com pelo menos 2
                             modelos distintos observados — se só um
                             modelo foi sorteado, o veredito declara a
                             LIMITAÇÃO: determinístico no que se mediu)
  NAO_DETERMINISTICO         algum filme com hashes diferentes entre
                             cópias — com a TABELA: qual run, qual
                             cópia, qual modelo, qual hash, ao lado de
                             quem divergiu (o ONDE, não só o que)

A âncora commitada (síntese avx512) é CONFERENCE junto: divergir DELA é
o esperado (a classe muda os kernels do MLAS — CP-011); o que se pergunta
é a igualdade DENTRO da classe avx2. Sem gate, sem teto, sem decisão: o
veredito alimenta a proposta ABERTA — virar âncora é validação do dono.

Uso: ci/determinismo_avx2.py [--evidencia harness/frota/observacao-avx2.json]
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

EVIDENCIA_DEFAULT = RAIZ / "harness" / "frota" / "observacao-avx2.json"


def calcular(doc: dict) -> dict:
    """O cálculo inteiro, da evidência ao veredito — função pura, o teste
    refaz tudo e confere o bloco 'veredito' gravado na evidência."""
    execs = doc.get("execucoes", [])
    copias = []
    for e in execs:
        for c in e.get("copias", []):
            copias.append({"run": str(e["run"]), **c})

    por_filme = {}
    for c in copias:
        for fid, hashes in (c.get("filmes") or {}).items():
            h = hashes.get("regenerado_avx2")
            por_filme.setdefault(fid, []).append(
                {"run": c["run"], "copia": c.get("copia"),
                 "cpu": c.get("cpu"), "hash": h})
    # a âncora vista pela evidência (deve ser UMA só — é o commitado)
    ancoras = {}
    for c in copias:
        for fid, hashes in (c.get("filmes") or {}).items():
            a = hashes.get("ancora_commitada")
            if a and a.startswith(("falhou:", "nao-registrado")) is False:
                ancoras.setdefault(fid, set()).add(a)

    filmes_doc = {}
    divergencias = []
    for fid, obs in sorted(por_filme.items()):
        hashes = sorted({o["hash"] for o in obs if o["hash"]})
        validos = [o for o in obs if o["hash"]
                   and not str(o["hash"]).startswith(("falhou:", "nao-"))]
        medidos = {o["hash"] for o in validos}
        filme = {
            "copias_medidas": len(obs),
            "hashes_distintos": sorted(medidos),
            "modelos_distintos": sorted({o["cpu"] for o in validos}),
            "execucoes_distintas": sorted({o["run"] for o in validos}),
        }
        if len(ancoras.get(fid, set())) == 1:
            filme["ancora_commitada"] = sorted(ancoras[fid])[0]
            filme["diverge_da_ancora"] = (
                len(medidos) == 1 and next(iter(medidos))
                != next(iter(ancoras[fid])))
        if len(medidos) > 1:
            filme["divergentes"] = [o for o in validos
                                    if o["hash"] != sorted(medidos)[0]]
            divergencias.extend(
                f"{fid}: run {o['run']} {o['copia']} ({o['cpu']}) = "
                f"{o['hash'][:16]}…" for o in filme["divergentes"])
        filmes_doc[fid] = filme

    modelos = sorted({c.get("cpu") for c in copias})
    execucoes = sorted({str(e["run"]) for e in execs})
    problemas = []
    if divergencias:
        veredito = "NAO_DETERMINISTICO"
        nota = ("hashes de PCM mixado DIFERENTES dentro da classe avx2 — a "
                "âncora avx2 não existe: o desenho CP-013/015 segue (prova "
                "em avx512, observação em avx2, N pela janela)")
    else:
        veredito = "DETERMINISTICO_NA_CLASSE"
        nota = ("todos os hashes regenerado_avx2 de cada filme são IGUAIS "
                "entre cópias, modelos e execuções")
        if len(modelos) < 2:
            problemas.append(
                f"só {len(modelos)} modelo(s) de CPU avx2 na evidência — "
                f"o veredito é determinístico NO QUE SE MEDIU; a pergunta "
                f"pede >= 3 modelos distintos")
        elif len(modelos) < 3:
            problemas.append(
                f"{len(modelos)} modelos distintos observados — a pergunta "
                f"pede >= 3: registrou-se a fronteira medida do pool")
    if len(execs) < 5:
        problemas.append(f"{len(execs)} execuções na evidência — a pergunta "
                         f"pede >= 5")

    return {
        "execucoes": len(execs),
        "copias_avx2": len(copias),
        "modelos_de_cpu": modelos,
        "filmes": filmes_doc,
        "veredito": veredito,
        "divergencias": divergencias,
        "limitacoes": problemas,
        "nota": nota,
        "cp": "CP-016 (proposta — a decisão de virar âncora é do dono)",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--evidencia", default=str(EVIDENCIA_DEFAULT))
    args = ap.parse_args()
    doc = json.loads(Path(args.evidencia).read_text(encoding="utf-8"))

    calc = calcular(doc)
    print("== DETERMINISMO DA CLASSE AVX2 (CP-016, proposta — da evidência "
          f"{Path(args.evidencia).name})")
    print(f"   execuções: {calc['execucoes']} | cópias avx2: "
          f"{calc['copias_avx2']} | modelos de CPU: "
          f"{len(calc['modelos_de_cpu'])}")
    for m in calc["modelos_de_cpu"]:
        print(f"     - {m}")
    for fid, f in calc["filmes"].items():
        hashes = ", ".join(h[:16] + "…" for h in f["hashes_distintos"])
        print(f"   {fid}: {f['copias_medidas']} cópias | {len(f['modelos_distintos'])} "
              f"modelos | hashes: {hashes}")
        if "ancora_commitada" in f:
            print(f"     âncora commitada: {f['ancora_commitada'][:16]}… | "
                  f"diverge da âncora (esperado entre classes): "
                  f"{'sim' if f['diverge_da_ancora'] else 'não'}")
        for d in f.get("divergentes", []):
            print(f"     DIVERGE: run {d['run']} {d['copia']} ({d['cpu']}) "
                  f"= {str(d['hash'])[:16]}…")
    print(f"   VEREDITO: {calc['veredito']}")
    print(f"   {calc['nota']}")
    for p in calc["limitacoes"]:
        print(f"   LIMITAÇÃO: {p}")
    print("   rótulo: 'observação, sem gate' — o gate segue sendo bytes do "
          "PCM em AVX-512; virar âncora é decisão do dono")
    return 0


if __name__ == "__main__":
    sys.exit(main())
