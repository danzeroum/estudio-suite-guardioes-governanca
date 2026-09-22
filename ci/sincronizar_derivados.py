#!/usr/bin/env python3
"""Gera os artefatos DERIVADOS: catalogo.js e os blocos do README.

A orientacao deriva; ela nao descreve. Um README que ENUMERA rigs, poses e
cenarios e uma segunda descricao do repositorio: deriva da primeira em
silencio, sem erro, e com a aparencia de documentacao cuidadosa. No dia em
que alguem acrescenta uma pose, o README passa a ensinar um repositorio que
nao existe mais -- e ensina com confianca.

Entao os blocos entre marcadores sao GERADOS daqui, e `--check` reprova no CI
quando o commitado diverge. E o mesmo passo "artefato gerado esta em dia" que
o repositorio de origem ja roda para guardioes.data.js: convencao da casa.

  python3 ci/sincronizar_derivados.py            # regrava
  python3 ci/sincronizar_derivados.py --check    # so confere (CI)
"""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import inventario as inv          # noqa: E402
from estudio_suite import lei as _lei                # noqa: E402
from estudio_suite.comum import ErroDeDados          # noqa: E402

README = RAIZ / "README.md"
CATALOGO = RAIZ / "catalogo.js"


def _tabela(cabecalho, linhas):
    out = ["| " + " | ".join(cabecalho) + " |",
           "|" + "|".join("---" for _ in cabecalho) + "|"]
    out += ["| " + " | ".join(str(c) for c in l) + " |" for l in linhas]
    return "\n".join(out)


def bloco_elenco():
    el = inv.elenco()
    pes = [r for r in el if r["tipo"] == "personagem"]
    pr = [r for r in el if r["tipo"] == "prop"]
    t = ["**Personagens** — todos partilham uma viewBox (200×320, pés em y=320), "
         "um vocabulário de partes e uma API.", ""]
    t.append(_tabela(
        ["rig", "quem é", "escala", "poses", "expressões"],
        [[f"`{r['id']}`", f"{r['nome']} — {r['epiteto']}" if r["epiteto"] else r["nome"],
          r["escala"], " · ".join(f"`{p}`" for p in r["poses"]),
          " · ".join(f"`{e}`" for e in r["expressoes"])] for r in pes]))
    t += ["", "**Props** — mesmo contrato dos personagens, para o roteiro não "
          "precisar saber a diferença.", ""]
    t.append(_tabela(["prop", "o que é", "poses"],
                     [[f"`{r['id']}`", r["nome"], " · ".join(f"`{p}`" for p in r["poses"])]
                      for r in pr]))
    return "\n".join(t)


def bloco_cenarios():
    cs = inv.cenarios()
    return (_tabela(["cenário", "onde é"], [[f"`{c['id']}`", c["nome"]] for c in cs])
            + f"\n\nSão {len(cs)}. Cenário que uma história pede e não existe nasce em "
              "`filmes/<id>/local/` — e só sobe para cá quando um **segundo** filme pedir o mesmo.")


def bloco_vocabulario():
    v = inv.vocabulario()
    return (_tabela(["campo", "valores aceitos"],
                    [["ação (verbo)", " · ".join(f"`{x}`" for x in v["acoes"])],
                     ["propriedade animável", " · ".join(f"`{x}`" for x in v["numericas"])],
                     ["evento", " · ".join(f"`{x}`" for x in v["eventos"])],
                     ["easing", " · ".join(f"`{x}`" for x in v["easings"])],
                     ["camada do palco", " · ".join(f"`{x}`" for x in v["camadas"])]])
            + "\n\nLido do motor em tempo de execução (`estudio_suite/comum.py`), nunca "
              "redigitado: duas cópias de um vocabulário divergem em silêncio.")


def bloco_catalogo():
    c = inv.catalogo()
    t = [_tabela(["filme", "planos", "duração", "falas", "artigos"],
                 [[f"[{f['titulo']}](paginas/player.html?filme={f['id']}) `{f['id']}`",
                   f["planos"], f"{f['duracao']} s", f["legendas"],
                   ", ".join(str(a) for a in f["arts"]) or "—"] for f in c["filmes"]])]
    t += ["", _tabela(["jogo", "artigo", "opções", "situações"],
                      [[f"[{j['titulo']}](paginas/jogo.html?jogo={j['id']}) `{j['id']}`",
                        f"Art. {j['artigo']}", j["direitos"], j["situacoes"]]
                       for j in c["jogos"]])]
    return "\n".join(t)


def bloco_lei():
    a = _lei.ancora()
    linhas = [[f"`{rel}`", f"`{sha[:12]}…`"] for rel, sha in sorted(a["arquivos"].items())]
    return (f"A lei vem de **[{a['repo']}]({a['url']})**, no commit "
            f"`{a['sha'][:12]}…`, e é conferida byte a byte a cada execução.\n\n"
            + _tabela(["arquivo ancorado", "sha256"], linhas)
            + "\n\nMaterializada em `workspace/lei/`, que o `.gitignore` recusa. "
              "Avançar a âncora é **change-proposal**: pode mudar o que um filme já "
              "publicado afirma.")


BLOCOS = {
    "elenco": bloco_elenco,
    "cenarios": bloco_cenarios,
    "vocabulario": bloco_vocabulario,
    "catalogo": bloco_catalogo,
    "lei": bloco_lei,
}


def catalogo_js():
    c = inv.catalogo()
    corpo = json.dumps(c, ensure_ascii=False, indent=1, sort_keys=True)
    return ("/* DERIVADO por ci/sincronizar_derivados.py -- nao edite a mao.\n"
            "   A capa descobre os filmes e jogos daqui; uma lista escrita a mao\n"
            "   em index.html envelheceria no primeiro filme novo. */\n"
            "window.ESTUDIO_CATALOGO=\n" + corpo + "\n")


def aplicar(texto: str) -> str:
    for nome, fn in BLOCOS.items():
        ini, fim = f"<!-- DERIVADO:{nome} -->", f"<!-- /DERIVADO:{nome} -->"
        if ini not in texto or fim not in texto:
            raise ErroDeDados(f"README.md nao tem o par de marcadores de '{nome}'.")
        a, b = texto.index(ini) + len(ini), texto.index(fim)
        texto = texto[:a] + "\n" + fn() + "\n" + texto[b:]
    return texto


def main():
    conferir = "--check" in sys.argv
    alvos = {README: aplicar(README.read_text(encoding="utf-8")),
             CATALOGO: catalogo_js()}
    divergem = []
    for caminho, novo in alvos.items():
        atual = caminho.read_text(encoding="utf-8") if caminho.exists() else None
        if atual == novo:
            continue
        if conferir:
            divergem.append(caminho.relative_to(RAIZ))
        else:
            caminho.write_text(novo, encoding="utf-8")
            print(f"  regravado: {caminho.relative_to(RAIZ)}")
    if conferir and divergem:
        print("  ERRO: artefato derivado fora de dia: "
              + ", ".join(str(d) for d in divergem), file=sys.stderr)
        print("  Rode: python3 ci/sincronizar_derivados.py", file=sys.stderr)
        return 1
    print("  derivados em dia." if conferir else "  derivados regravados.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ErroDeDados as e:
        print(f"  ERRO: {e}", file=sys.stderr)
        sys.exit(2)
