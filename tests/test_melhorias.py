#!/usr/bin/env python3
"""O modulo de automelhorias, provado nos dois sentidos.

Uma guarda que nunca reprovou nao provou nada, e um propositor que nunca
propos tambem nao. Cada caso aqui monta a evidencia, confirma que a proposta
nasce, e confirma que ela NAO nasce quando a evidencia e insuficiente.
"""
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite.melhorias import evidencias, propor   # noqa: E402

ok, bad = [], []


def chk(c, msg):
    (ok if c else bad).append(msg)


def com_locais(mapa):
    """Cria adereços locais temporarios e devolve os sinais de promocao."""
    criados = []
    try:
        for fid, nomes in mapa.items():
            d = RAIZ / "filmes" / fid / "local"
            d.mkdir(parents=True, exist_ok=True)
            for n in nomes:
                f = d / f"{n}.cenario.js"
                f.write_text(f"reg('{n}', 'o cenario de prova', '<g></g>');\n",
                             encoding="utf-8")
                criados.append(f)
        return evidencias.promocoes()
    finally:
        for f in criados:
            f.unlink(missing_ok=True)


def main():
    filmes = sorted(d.name for d in (RAIZ / "filmes").iterdir()
                    if d.is_dir() and (d / f"{d.name}.filme.js").exists())
    a, b = filmes[0], filmes[1]

    # --- a regra da segunda repeticao, nos dois sentidos -------------------
    um = com_locais({a: ["sala-audiencia"]})
    chk(not any(s["chave"] == "sala-audiencia" for s in um),
        f"um filme so NAO propoe promocao — uma historia nao e evidencia de que "
        f"algo e geral ({[s['chave'] for s in um]})")

    dois = com_locais({a: ["sala-audiencia"], b: ["sala-audiencia"]})
    achou = [s for s in dois if s["chave"] == "sala-audiencia"]
    chk(len(achou) == 1, f"o SEGUNDO uso propoe promocao ({[s['chave'] for s in dois]})")
    if achou:
        chk(set(achou[0]["filmes"]) == {a, b},
            f"a proposta nomeia os dois filmes que pediram ({achou[0]['filmes']})")
        chk("2 filmes" in achou[0]["evidencia"],
            f"a proposta carrega a evidencia que a produziu ({achou[0]['evidencia']})")

    # --- o modulo nunca escreve em caminho protegido -----------------------
    for p in ("motor/", "ci/", "tests/", "lei.lock", "harness/policies/"):
        chk(p in propor.PROTEGIDOS, f"'{p}' e caminho protegido")

    fonte = "\n".join(f.read_text(encoding="utf-8")
                      for f in sorted((RAIZ / "estudio_suite/melhorias").glob("*.py")))
    chk("motor/" not in fonte.split("PROTEGIDOS")[-1].split("]")[1] if "]" in fonte else True,
        "o modulo nao escreve caminho de motor fora da lista de protegidos")

    # --- proposta so nasce com evidencia, e nao se duplica -----------------
    antes = propor.gerar(escrever=False)
    de_novo = propor.gerar(escrever=False)
    chk(antes == de_novo, "gerar duas vezes da o mesmo — a proposta e idempotente")

    # --- aviso de orcamento NAO vira proposta ------------------------------
    avisos = [s for s in evidencias.orcamento_apertado() if s["fracao"] < 0.85]
    nomes = " ".join(antes)
    chk(all(s["chave"].split("/")[-1].replace(".", "-") not in nomes for s in avisos),
        f"arquivo em faixa de aviso nao gera proposta — fila que ninguem le "
        f"nao existe ({[s['chave'] for s in avisos]})")

    for m in ok:
        print("  ok  ", m)
    for m in bad:
        print("  FALHOU", m)
    print(f"\n  {len(ok)} passaram, {len(bad)} falharam")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
