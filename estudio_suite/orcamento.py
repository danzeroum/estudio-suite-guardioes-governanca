"""Orcamento de tamanho: teto, nao meta.

O ponto de um teto nao e o numero -- e a conversa que ele forca quando alguem
se aproxima. player.js bateu 91% uma vez, e a resposta certa nao foi negociar
o limite: foi separar o que roda por quadro do que roda uma vez no boot. O
arquivo encolheu para 80% e ficou melhor de ler. Um teto que se afrouxa na
primeira pressao nunca teria provocado essa pergunta.

Avisa em 70%, reprova em 85%. A faixa entre os dois e de proposito: e onde da
para pensar sem pressa.
"""
import gzip
import re
from pathlib import Path

from .comum import RAIZ


def _conf():
    txt = (RAIZ / "suite.yaml").read_text(encoding="utf-8")
    aviso = float(re.search(r"^\s*aviso:\s*([\d.]+)", txt, re.M).group(1))
    congela = float(re.search(r"^\s*congela:\s*([\d.]+)", txt, re.M).group(1))
    bloco = txt[txt.index("arquivos:"):]
    limites = {m.group(1): int(m.group(2))
               for m in re.finditer(r"^    (\S+):\s*(\d+)\s*$", bloco, re.M)}
    fixos = {k: v for k, v in limites.items() if "*" not in k}
    padroes = {k: v for k, v in limites.items() if "*" in k}
    return aviso, congela, fixos, padroes


def medir():
    aviso, congela, fixos, padroes = _conf()
    alvos = dict(fixos)
    for padrao, lim in padroes.items():
        for p in sorted(RAIZ.glob(padrao)):
            alvos[str(p.relative_to(RAIZ))] = lim
    saida = []
    for rel, lim in sorted(alvos.items()):
        f = RAIZ / rel
        if not f.exists():
            saida.append({"arquivo": rel, "estado": "ausente", "bytes": 0,
                          "limite": lim, "fracao": 0.0})
            continue
        n = len(gzip.compress(f.read_bytes(), 9))
        fr = n / lim
        estado = "congela" if fr > congela else ("aviso" if fr > aviso else "ok")
        saida.append({"arquivo": rel, "estado": estado, "bytes": n,
                      "limite": lim, "fracao": round(fr, 3)})
    return saida


def main():
    linhas = medir()
    ruins = [l for l in linhas if l["estado"] in ("congela", "ausente")]
    for l in linhas:
        if l["estado"] != "ok":
            print(f"  {l['estado']:<8} {l['arquivo']} = {l['bytes']}B gzip "
                  f"({l['fracao']:.0%} de {l['limite']}B)")
    print(f"  {len(linhas)} arquivo(s) medidos, {len(ruins)} acima do teto.")
    return 1 if ruins else 0
