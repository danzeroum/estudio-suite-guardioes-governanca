#!/usr/bin/env python3
"""O fiscal do modulo de automelhorias.

Um modulo que pode editar o proprio fiscal acaba editando o proprio fiscal.
Este arquivo confere que isso nao aconteceu -- e ele NAO e escrito pelo
modulo, o que e exatamente o ponto.

Confere tres coisas:
  1. O modulo so escreve em harness/change-proposals/ e harness/backlog.yaml.
  2. Nenhum caminho protegido aparece na lista do que ele pode aplicar.
  3. Toda proposta com risco alto ou medio exige aval humano.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite.melhorias.propor import CP, PROTEGIDOS   # noqa: E402

PERMITIDOS_A_ESCREVER = ("harness/change-proposals/", "harness/backlog.yaml")


def main():
    achados = []

    # 1. O que o modulo escreve, lido do codigo dele.
    fonte = "\n".join(p.read_text(encoding="utf-8")
                      for p in sorted((RAIZ / "estudio_suite/melhorias").glob("*.py")))
    escritas = re.findall(r"write_text\(|open\([^)]*['\"]w", fonte)
    alvos = set(re.findall(r"\(CP / \w+\)|backlog", fonte))
    if escritas and not alvos:
        achados.append("o modulo escreve em disco sem alvo reconhecivel "
                       "(esperado: harness/change-proposals/ ou backlog.yaml)")

    # 2. Os protegidos estao declarados, e nenhum e um caminho que ele toca.
    if not PROTEGIDOS:
        achados.append("a lista de caminhos protegidos esta vazia")
    for p in ("motor/", "ci/", "tests/", "lei.lock"):
        if p not in PROTEGIDOS:
            achados.append(f"'{p}' deixou de ser caminho protegido")

    # 3. Proposta de risco nao-baixo sem aval humano.
    for f in sorted(CP.glob("CP-*.yaml")):
        txt = f.read_text(encoding="utf-8")
        risco = re.search(r"^\s*nivel:\s*(\w+)", txt, re.M)
        aval = re.search(r"^\s*aval_humano_necessario:\s*(\w+)", txt, re.M)
        if risco and risco.group(1) in ("medio", "alto", "critico"):
            if not aval or aval.group(1) != "true":
                achados.append(f"{f.name}: risco {risco.group(1)} sem aval humano")
        if not re.search(r"^\s*evidencia:", txt, re.M):
            achados.append(f"{f.name}: proposta sem evidencia — o modulo propoe "
                           f"a partir de fato, nunca de gosto")

    for a in achados:
        print(f"  ERRO: {a}", file=sys.stderr)
    n = len(list(CP.glob("CP-*.yaml")))
    print(f"  {n} proposta(s), {len(PROTEGIDOS)} caminho(s) protegido(s), "
          f"{len(achados)} achado(s).")
    return 1 if achados else 0


if __name__ == "__main__":
    sys.exit(main())
