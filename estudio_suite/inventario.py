"""O inventario: o que a suite SABE fazer, lido do estado vivo.

Nenhuma lista escrita a mao entra aqui. Rigs, poses, expressoes, cenarios,
props, filmes e jogos sao descobertos dos proprios arquivos, e o vocabulario
do roteiro vem do motor JS (ver comum.py). Uma lista em markdown ou YAML seria
uma segunda descricao do repositorio -- deriva da primeira em silencio, sem
erro, e com a aparencia de documentacao cuidadosa.

E disto que o agente precisa ANTES de escrever um roteiro: pedir uma pose que
nao existe custa uma iteracao inteira, e o custo nao aparece como erro de
codigo, aparece como filme que nao monta.
"""
import json
import re

from .comum import (ACOES, CAMADAS, EASES, EVENTOS, MOTOR, NUMERICAS, RAIZ,
                    ErroDeDados,
                    dados_do_filme, dados_do_jogo, filmes_existentes,
                    jogos_existentes)
from .roteiro import bloco_chaves, rigs_de_js


def elenco():
    """Os personagens e os props, com poses e expressoes REAIS.

    A fonte e motor/baseline/rigs/*.json, que o proprio motor produz e que o
    teste de navegador confere contra o motor vivo a cada execucao. Ler do JS
    a olho ja foi tentado aqui e dava lista errada: um extrator de chaves nao
    sabe a diferenca entre o nome de uma pose e o nome de uma parte dentro
    dela, e devolvia 'braco-l' como se fosse pose. Lista plausivel e errada e
    pior do que lista faltando -- o agente teria pedido a pose 'cabeca'.
    """
    base = RAIZ / "motor" / "baseline" / "rigs"
    saida = []
    for caminho in sorted((MOTOR / "rigs").glob("*.rig.js")):
        rid = caminho.name.replace(".rig.js", "")
        txt = caminho.read_text(encoding="utf-8")
        ref = base / f"{rid}.json"
        if not ref.exists():
            raise ErroDeDados(
                f"falta a referencia de arte de '{rid}'. Rode: "
                f"python3 tests/test_navegador.py --gravar"
            )
        d = json.loads(ref.read_text(encoding="utf-8"))
        nome = re.search(r"nome:\s*'([^']+)'", txt)
        epiteto = re.search(r"epiteto:\s*'([^']+)'", txt)
        saida.append({
            "id": rid, "tipo": "personagem",
            "nome": nome.group(1) if nome else rid,
            "epiteto": epiteto.group(1) if epiteto else "",
            "escala": d.get("escalaNatural", 1.0),
            "poses": sorted(d.get("poses") or {}),
            "expressoes": sorted(d.get("expressoes") or {}),
            "estados": sorted(d.get("estados") or {}),
            "partes": len(d.get("origens") or {}),
        })
    for r in rigs_de_js(MOTOR / "props.js"):
        txt = (MOTOR / "props.js").read_text(encoding="utf-8")
        m = re.search(r"id: '" + r["id"] + r"', nome: '([^']+)', epiteto: '([^']*)'", txt)
        saida.append({
            "id": r["id"], "tipo": "prop",
            "nome": m.group(1) if m else r["id"],
            "epiteto": m.group(2) if m else "",
            "escala": 1.0,
            "poses": sorted(r["poses"] - r["partes"]),
            "expressoes": ["neutro"], "estados": ["normal", "apagado"],
            "partes": len(r["partes"]),
        })
    return saida


def cenarios():
    """Os cenarios registrados em cenarios.js, pela chamada reg(id, nome, ...)."""
    txt = (MOTOR / "cenarios.js").read_text(encoding="utf-8")
    return [{"id": i, "nome": n}
            for i, n in sorted(re.findall(r"reg\('([a-z-]+)',\s*'([^']*)'", txt))]


def vocabulario():
    return {"acoes": sorted(ACOES), "numericas": sorted(NUMERICAS),
            "eventos": sorted(EVENTOS), "easings": sorted(EASES),
            "camadas": list(CAMADAS) and sorted(CAMADAS)}


def catalogo():
    """Os filmes e jogos que existem, com o que se sabe deles sem navegador."""
    fs = []
    for fid in filmes_existentes():
        d = dados_do_filme(fid)
        fs.append({
            "id": fid, "titulo": d["titulo"], "duracao": d["duracao"],
            "planos": len(d["planos"]),
            "legendas": sum(len(P.get("legendas") or []) for P in d["planos"]),
            "arts": sorted({a for P in d["planos"] for a in (P.get("arts") or [])}),
            "local": sorted((RAIZ / "filmes" / fid / "local").glob("*.js")) and
                     sorted(f.name for f in (RAIZ / "filmes" / fid / "local").glob("*.js")),
        })
    js = []
    for jid in jogos_existentes():
        d = dados_do_jogo(jid)
        js.append({
            "id": jid, "titulo": d["titulo"], "subtitulo": d.get("subtitulo", ""),
            "artigo": d.get("artigo"), "direitos": len(d.get("direitos") or []),
            "situacoes": len(d.get("situacoes") or []),
        })
    return {"filmes": fs, "jogos": js}


def tudo():
    return {"elenco": elenco(), "cenarios": cenarios(),
            "vocabulario": vocabulario(), **catalogo()}
