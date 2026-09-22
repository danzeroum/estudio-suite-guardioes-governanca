"""CLI da suite. Um comando por pergunta que alguem faz de verdade."""
import json
import sys

from .comum import ErroDeDados

AJUDA = """estudio — a suite que transforma historia em filme

  orientar      onde estou, o que existe, o que falta em cada filme
  inventario    o elenco vivo: poses, expressoes, cenarios, vocabulario
  validar       o gate unico: roteiros, derivados, lei   (o que o CI roda)
  lei           materializa e confere a lei ancorada

  --json        onde fizer sentido, a saida crua
  --refazer-lei rebaixa workspace/lei e busca de novo
"""


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "ajuda"):
        print(AJUDA)
        return 0
    cmd, resto = argv[0], argv[1:]
    try:
        if cmd == "orientar":
            from .orientar import main as m
            return m()
        if cmd == "inventario":
            from . import inventario as inv
            if "--json" in resto:
                print(json.dumps(inv.tudo(), ensure_ascii=False, indent=1, sort_keys=True))
                return 0
            for r in inv.elenco():
                print(f"  {r['tipo']:<11} {r['id']:<10} esc={r['escala']:<5} "
                      f"poses: {', '.join(r['poses'])}")
            print("\n  cenarios: " + ", ".join(c["id"] for c in inv.cenarios()))
            v = inv.vocabulario()
            for k in ("acoes", "numericas", "eventos", "easings", "camadas"):
                print(f"  {k}: " + ", ".join(v[k]))
            return 0
        if cmd == "lei":
            from . import lei as _lei
            base = _lei.materializar(forcar="--refazer-lei" in resto)
            a = _lei.ancora()
            print(f"  lei {a['repo']} @ {a['sha'][:12]} conferida em {base}")
            return 0
        if cmd == "validar":
            sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
            from ci.validar_tudo import main as m   # noqa
            return m(resto)
        print(f"comando desconhecido: {cmd}\n\n{AJUDA}", file=sys.stderr)
        return 64
    except ErroDeDados as e:
        print(f"  ERRO: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
