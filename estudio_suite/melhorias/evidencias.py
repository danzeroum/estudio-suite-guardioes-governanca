"""Le o que as execucoes deixaram e devolve SINAIS -- nunca opinioes.

A diferenca importa. "Este codigo esta feio" nao e sinal; "o mesmo portao
reprovou em tres filmes" e. Um modulo de melhoria alimentado por gosto vira
uma fila de refactor que ninguem le; alimentado por contagem, ele so fala
quando ha um fato.

Cada sinal carrega a evidencia que o produziu, para quem le a proposta poder
discordar do numero em vez de discordar do autor.
"""
import json
import re
from collections import Counter, defaultdict

from .. import orcamento
from ..comum import FILMES, HARNESS, RAIZ, filmes_existentes

RUNS = HARNESS / "runs"


def _runs():
    if not RUNS.is_dir():
        return []
    out = []
    for f in sorted(RUNS.glob("run-*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue          # run ilegivel e ruido, nao motivo de parar
    return out


def _assinatura(caminho):
    """Identidade grosseira de um adereço local: o id que ele registra.

    Grosseira de proposito. Comparar bytes acharia so copias literais, e o
    caso que interessa e o oposto: duas historias pedindo A MESMA COISA e
    escrevendo-a um pouco diferente cada uma.
    """
    txt = caminho.read_text(encoding="utf-8")
    ids = re.findall(r"reg\('([a-z-]+)'|id:\s*'([a-z-]+)'", txt)
    achados = {a or b for a, b in ids}
    return sorted(achados) or [caminho.stem]


def promocoes():
    """Adereço local pedido por DOIS filmes = candidato ao elenco compartilhado.

    E a regra "abstracao so nasce na segunda repeticao", com o modulo contando
    as repeticoes em vez de alguem lembrar delas. No PRIMEIRO uso nao se
    propoe nada: uma historia nao e evidencia de que algo e geral.
    """
    onde = defaultdict(set)
    for fid in filmes_existentes():
        for p in sorted((FILMES / fid / "local").glob("*.js")):
            for a in _assinatura(p):
                onde[a].add(fid)
    return [{"tipo": "promocao", "chave": a, "filmes": sorted(fs),
             "evidencia": f"'{a}' foi pedido por {len(fs)} filmes: {', '.join(sorted(fs))}"}
            for a, fs in sorted(onde.items()) if len(fs) >= 2]


def portoes_teimosos(minimo=3):
    """O mesmo achado repetindo entre execucoes.

    Um portao que reprova em muitos alvos nao e um alvo ruim -- e um portao
    errado, ou uma ferramenta que falta. Isso nao da para descobrir a partir
    de "211 passaram".
    """
    c = Counter()
    for r in _runs():
        for a in r.get("achados") or []:
            # a parte estavel da mensagem, antes dos parenteses de detalhe
            c[re.split(r"\s*[(\[]", a)[0].strip()[:80]] += 1
    return [{"tipo": "portao-teimoso", "chave": k, "vezes": n,
             "evidencia": f"'{k}' reprovou em {n} execucoes"}
            for k, n in c.most_common() if n >= minimo]


def orcamento_apertado():
    """Arquivo perto do teto: proposta de divisao, nunca de afrouxar o teto."""
    return [{"tipo": "orcamento", "chave": l["arquivo"], "fracao": l["fracao"],
             "evidencia": f"{l['arquivo']} esta em {l['fracao']:.0%} do teto "
                          f"({l['bytes']}B de {l['limite']}B)"}
            for l in orcamento.medir() if l["estado"] in ("aviso", "congela")]


def sinais():
    return promocoes() + portoes_teimosos() + orcamento_apertado()


def resumo():
    s = sinais()
    if not s:
        return "  nenhum sinal: nada a propor a partir da evidencia de hoje."
    L = [f"  {len(s)} sinal(is) a partir de {len(_runs())} execucao(oes):"]
    for x in s:
        L.append(f"    [{x['tipo']}] {x['evidencia']}")
    return "\n".join(L)
