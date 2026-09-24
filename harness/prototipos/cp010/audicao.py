"""CP-010 — kit de audição: o que número não decide, quem decide é o ouvido.

Um comando gera, em workspace/cp010-audicao/, a fala de cada guardião em
três versões — ATUAL (sem deslocamento), alvo por PSOLA e alvo por WORLD —
na cadeia real (piper -> pitch -> timbre do rig), e uma página HTML local
(abre por file://, sem fetch, sem nada de fora) com os players lado a lado,
a F0 medida pelo pitch_f0 da audio-suite e o alvo em semitons.

A página faz duas perguntas explícitas:
  1. a técnica: PSOLA soa aceitável onde o deslocamento é maior (Elefante,
     -5 st)? Se não, o WORLD vira a opção (ver estabilidade na CP-010);
  2. os pares que caem na MESMA categoria (a CP os deixa na mesma altura):
     dá para distingui-los pela voz, ou é preciso subdividir?

Uso (venv isolado do protótipo):
    python harness/prototipos/cp010/audicao.py
Nenhum áudio é commitado: tudo mora em workspace/ (gitignored) e se regera.
"""

from __future__ import annotations

import html
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import prototipo as p  # noqa: E402

DESTINO = p.RAIZ / "workspace" / "cp010-audicao"
VERSOES = (("atual", None), ("psola", "psola"), ("world", "world"))


def gerar() -> dict:
    alvos = yaml.safe_load((AQUI / "alvos.yaml").read_text(encoding="utf-8"))
    cat = alvos["categoria"]
    st_de = {g: float(alvos["semitons"][c]) for g, c in cat.items()}
    DESTINO.mkdir(parents=True, exist_ok=True)
    ports = p.portadoras()
    voz = p.carregar_voz(p.modelo_travado())

    dados: dict = {"falantes": {}}
    atual = {}
    for g in p.FALANTES:
        x = p.falar(voz, g, 0.0, None, ports)
        p._gravar_wav(DESTINO / f"{g}-atual.wav", x)
        atual[g] = p.medir(x)["f0_mediana_hz"]
        print(f"  {g:10s} atual {atual[g]} Hz")
    ref = float(np.median(list(atual.values())))
    dados["referencia_hz"] = round(ref, 2)
    for g in p.FALANTES:
        _, tim, declarado = p.voz_do_falante(g)
        alvo_hz = ref * 2 ** (st_de[g] / 12)
        desloc = 12 * math.log2(alvo_hz / atual[g])
        f = {"categoria": cat[g], "declarado": declarado, "timbre": bool(tim), "alvo_st": st_de[g],
             "alvo_hz": round(alvo_hz, 2), "versoes": {"atual": {"arquivo": f"{g}-atual.wav",
                                                                "f0_hz": atual[g]}}}
        for nome, tec in VERSOES[1:]:
            x = p.falar(voz, g, desloc, tec, ports)
            p._gravar_wav(DESTINO / f"{g}-{nome}.wav", x)
            f0 = p.medir(x)["f0_mediana_hz"]
            f["versoes"][nome] = {"arquivo": f"{g}-{nome}.wav", "f0_hz": f0,
                                  "erro_cents": round(1200 * math.log2(f0 / alvo_hz), 1)}
            print(f"  {g:10s} {nome:5s} {f0} Hz (alvo {alvo_hz:.1f})")
        dados["falantes"][g] = f
    grupos: dict = {}
    for g, c in cat.items():
        grupos.setdefault(c, []).append(g)
    dados["mesma_categoria"] = {c: gs for c, gs in grupos.items() if len(gs) > 1}
    (DESTINO / "audicao.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    return dados


def _player(arquivo: str, rotulo: str) -> str:
    return (f'<figure><figcaption>{html.escape(rotulo)}</figcaption>'
            f'<audio controls preload="metadata" src="{html.escape(arquivo)}"></audio></figure>')


def pagina(d: dict) -> str:
    linhas = []
    ordem = sorted(d["falantes"], key=lambda g: d["falantes"][g]["alvo_st"])
    for g in ordem:
        f = d["falantes"][g]
        v = f["versoes"]
        celulas = "".join(
            f'<td>{_player(v[n]["arquivo"], f"{g} — {n}")}'
            f'<p class="num">F0 {v[n]["f0_hz"]} Hz'
            + (f' · erro {v[n]["erro_cents"]:+.0f} cents' if "erro_cents" in v[n] else "")
            + "</p></td>"
            for n, _ in VERSOES)
        linhas.append(
            f'<tr><th scope="row">{html.escape(g)}<br><span class="cat">{html.escape(f["categoria"])}'
            f' · alvo {f["alvo_st"]:+.1f} st ({f["alvo_hz"]} Hz)</span></th>{celulas}</tr>')
    pares = []
    for c, gs in d["mesma_categoria"].items():
        players = "".join(_player(d["falantes"][g]["versoes"]["psola"]["arquivo"], f"{g} — alvo (PSOLA)")
                          for g in gs)
        pares.append(
            f'<section class="pergunta"><h3>Mesma categoria ({html.escape(c)}): '
            f'{" e ".join(html.escape(g) for g in gs)}</h3>'
            f'<p><strong>Pergunta:</strong> a CP-010 põe {" e ".join(gs)} na <em>mesma altura</em>. '
            f'Ouvindo lado a lado, dá para saber quem é quem só pela voz (timbre e ritmo), '
            f'ou é preciso subdividir a categoria?</p><div class="lado">{players}</div>'
            f'<fieldset><legend>Sua resposta (anote no PR #13)</legend>'
            f'<label><input type="radio" name="{html.escape(c)}"> distinguem-se: manter</label> '
            f'<label><input type="radio" name="{html.escape(c)}"> confundem-se: subdividir</label></fieldset>'
            f'</section>')
    ele = d["falantes"].get("elefante", {})
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audição CP-010</title>
<style>
:root {{ --fundo:#faf8f3; --texto:#1f1d1a; --suave:#6b665e; --borda:#ddd6c8; --real:#7a4fa0; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fundo:#1c1b19; --texto:#eeeae2; --suave:#a8a296; --borda:#3a3732; --real:#c7a3ea; }} }}
body {{ background:var(--fundo); color:var(--texto); font:16px/1.5 system-ui,sans-serif; margin:0 auto; max-width:1180px; padding:16px; }}
h1 {{ font-size:1.5rem; margin:.2rem 0; }} h2 {{ font-size:1.15rem; margin-top:2rem; }} h3 {{ font-size:1rem; }}
.sub, .cat, .num {{ color:var(--suave); font-size:.85rem; margin:.2rem 0; }}
table {{ border-collapse:collapse; width:100%; }} th, td {{ border-top:1px solid var(--borda); padding:.5rem; vertical-align:top; text-align:left; }}
figure {{ margin:0; }} figcaption {{ font-size:.8rem; color:var(--suave); }} audio {{ width:100%; min-width:180px; }}
.pergunta {{ border:1px solid var(--borda); border-left:4px solid var(--real); padding:.2rem 1rem 1rem; margin:1rem 0; border-radius:6px; }}
.lado {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1rem; }}
fieldset {{ border:1px dashed var(--borda); margin-top:.8rem; }}
@media (max-width:720px) {{ table, tbody, tr, th, td {{ display:block; }} }}
</style></head><body>
<h1>Audição da CP-010 — pitch por guardião</h1>
<p class="sub">Arquivos locais gerados por <code>audicao.py</code> · referência medida {d["referencia_hz"]} Hz
(mediana das vozes atuais) · F0 pelo descritor <code>pitch_f0</code> da audio-suite · cadeia real: piper → pitch → timbre do rig.</p>

<h2>1. A técnica</h2>
<p><strong>Pergunta:</strong> o PSOLA (recomendado: sem dependência nova e estável entre classes de SIMD)
soa aceitável onde o deslocamento é maior — o Elefante, alvo {ele.get("alvo_st", 0):+.1f} st?
Se soar áspero, a alternativa é o WORLD (mais liso, mas com dependência compilada e folga menor entre máquinas).</p>
<table><thead><tr><th>guardião</th><th>atual</th><th>alvo · PSOLA</th><th>alvo · WORLD</th></tr></thead>
<tbody>{"".join(linhas)}</tbody></table>

<h2>2. Os pares na mesma categoria</h2>
{"".join(pares)}

<p class="sub">Nada aqui é commitado. Regenerar: <code>python harness/prototipos/cp010/audicao.py</code>.
As respostas não são salvas: anote a decisão no PR #13.</p>
</body></html>
"""


def main() -> int:
    d = gerar()
    (DESTINO / "index.html").write_text(pagina(d), encoding="utf-8")
    print(f"\n  abra no navegador: {(DESTINO / 'index.html').as_uri()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
