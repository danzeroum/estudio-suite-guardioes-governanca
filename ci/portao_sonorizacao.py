#!/usr/bin/env python3
"""O portao de sonorizacao, no formato que o CI aguenta (CP-004, CP-007, CP-008).

Diferenca de proposito em relacao aos outros fiscais: a audio-suite NAO e
dependencia da suite -- e uma CLI externa. O portao devolve INDECISO
quando ela falta, e INDECISO NAO quebra o build: so o VERMELHO (saida 1
da audio-suite, FINDING) reprova aqui. O estado e publicado por filme,
alto e claro -- porque "nao medido" tambem tem de aparecer como nao
medido, nao como aprovado.

CP-007: o job do CI INSTALA a audio-suite (isolada, pinada por SHA) e
promete isso no ambiente (ESTUDIO_EXIGIR_AUDIO_SUITE=1). Promessa feita,
ausencia vira VERMELHO -- tirar a ferramenta do job derruba o build. Na
maquina local sem a promessa, o INDECISO nomeado segue valendo.

CP-008: vermelho tem CAUSA, e a causa tem frase propria. O vermelho de
"promessa-quebrada" (ferramenta prometida e ausente) diz PROMESSA
QUEBRADA -- porque nada foi medido, e a correcao e de infraestrutura.
O vermelho de "trilha-reprovada" (FINDING da audio-suite) diz
DIVERGENCIA -- porque a trilha foi medida e reprovou, e a correcao e do
audio. Confundir os dois e mandar quem le o log corrigir o audio quando
o problema e o job -- ou comemorar o build verde de um gate cego.

Saidas: 0 conforme (ou indeciso documentado) · 1 qualquer vermelho --
promessa quebrada, trilha reprovada ou declaracao divergente do real.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite.comum import filmes_existentes       # noqa: E402
from estudio_suite.pipeline import portao_sonorizacao   # noqa: E402


def main() -> int:
    dublados, vermelhos = 0, []
    for fid in filmes_existentes():
        v = portao_sonorizacao(fid)
        if v.nota and "nada a medir" in v.nota:
            print(f"  mudo      {fid}: sem trilha declarada — o portao nao mede o que nao existe")
            continue
        dublados += 1
        marca = {"verde": "verde    ", "vermelho": "VERMELHO", "indeciso": "indeciso "}[v.estado]
        causa = f" [{v.causa}]" if v.causa else ""
        print(f"  {marca}  {fid}{causa}: {v.nota}")
        for a in v.achados:
            print(f"           · {a}")
        if v.estado == "vermelho":
            vermelhos.append((fid, v.causa))
    if not dublados:
        print("  nenhum filme declara trilha — nada medido, nada aprovado.")
        return 0
    if vermelhos:
        # A frase final e escolhida pela CAUSA estruturada (CP-008), nunca
        # por busca de texto na nota: cada vermelho diz o que de fato
        # aconteceu -- e "nao medi" nunca mais vira "reprovei".
        causas = {c for _, c in vermelhos}
        if "promessa-quebrada" in causas:
            print("\n  PROMESSA QUEBRADA: audio-suite ausente — nada foi medido.",
                  file=sys.stderr)
        elif "trilha-reprovada" in causas:
            print("\n  DIVERGENCIA: trilha reprovada pela audio-suite.",
                  file=sys.stderr)
        else:
            print("\n  DIVERGENCIA: a declaracao de audio diverge do que existe "
                  "no repositorio — nada foi medido.", file=sys.stderr)
        for fid, c in vermelhos:
            print(f"    {fid}: {c}", file=sys.stderr)
        return 1
    print(f"\n  {dublados} trilha(s) fiscalizada(s): verde ou indeciso documentado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
