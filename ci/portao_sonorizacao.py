#!/usr/bin/env python3
"""O portao de sonorizacao, no formato que o CI aguenta (CP-004, CP-007).

Diferenca de proposito em relacao aos outros fiscais: a audio-suite NAO e
dependencia da suite -- e uma CLI externa. O portao devolve INDECISO
quando ela falta, e INDECISO NAO quebra o build: so o VERMELHO (saida 1
da audio-suite, FINDING) reprova aqui. O estado e publicado por filme,
alto e claro -- porque "nao medido" tambem tem de aparecer como nao
medido, nao como aprovado.

CP-007: o job do CI agora INSTALA a audio-suite (isolada, pinada por SHA)
e promete isso no ambiente (ESTUDIO_EXIGIR_AUDIO_SUITE=1). Promessa feita,
ausencia vira VERMELHO -- tirar a ferramenta do job derruba o build. Na
maquina local sem a promessa, o INDECISO nomeado segue valendo.

Saidas: 0 conforme (ou indeciso documentado) · 1 trilha reprovada -- ou
audio-suite prometida e ausente.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite.comum import filmes_existentes       # noqa: E402
from estudio_suite.pipeline import portao_sonorizacao   # noqa: E402


def main() -> int:
    dublados, pior = 0, 0
    for fid in filmes_existentes():
        v = portao_sonorizacao(fid)
        if v.nota and "nada a medir" in v.nota:
            print(f"  mudo      {fid}: sem trilha declarada — o portao nao mede o que nao existe")
            continue
        dublados += 1
        marca = {"verde": "verde    ", "vermelho": "VERMELHO", "indeciso": "indeciso "}[v.estado]
        print(f"  {marca}  {fid}: {v.nota}")
        for a in v.achados:
            print(f"           · {a}")
        if v.estado == "vermelho":
            pior = 1
    if not dublados:
        print("  nenhum filme declara trilha — nada medido, nada aprovado.")
        return 0
    if pior:
        print("\n  DIVERGENCIA: trilha reprovada pela audio-suite.", file=sys.stderr)
        return 1
    print(f"\n  {dublados} trilha(s) fiscalizada(s): verde ou indeciso documentado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
