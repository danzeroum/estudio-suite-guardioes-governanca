"""CLI da suite. Um comando por pergunta que alguem faz de verdade."""
import json
import pathlib
import sys

from .comum import ErroDeDados

AJUDA = """estudio — a suite que transforma historia em filme

  orientar      onde estou, o que existe, o que falta em cada filme
  inventario    o elenco vivo: poses, expressoes, cenarios, vocabulario
  validar       o gate unico: roteiros, derivados, lei   (o que o CI roda)
  etapas <id>   onde este filme esta nas cinco etapas, e o que falta
  novo-filme <id> [--de <pedido.md>]   cria o esqueleto e mostra a proxima etapa
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
        if cmd == "etapas":
            from .pipeline import rodar
            if not resto:
                print("uso: etapas <id-do-filme>", file=sys.stderr)
                return 64
            fid = resto[0]
            marca = {"verde": "ok      ", "vermelho": "VERMELHO", "indeciso": "indeciso"}
            pior = 0
            for v in rodar(fid):
                print(f"  {marca[v.estado]} {v.etapa:<12} {v.nota}")
                for a in v.achados:
                    print(f"           · {a}")
                pior = max(pior, {"verde": 0, "vermelho": 1, "indeciso": 2}[v.estado])
            return pior

        if cmd == "novo-filme":
            from .pipeline import ETAPAS, rodar
            if not resto:
                print("uso: novo-filme <id> [--de <pedido.md>]", file=sys.stderr)
                return 64
            fid = resto[0]
            from .comum import FILMES
            d = FILMES / fid
            if d.exists():
                print(f"  {fid} ja existe. Veja: python3 -m estudio_suite etapas {fid}",
                      file=sys.stderr)
                return 1
            (d / "local").mkdir(parents=True)
            (d / "baseline").mkdir()
            origem = None
            if "--de" in resto:
                origem = pathlib.Path(resto[resto.index("--de") + 1])
                (d / "pedido.md").write_text(origem.read_text(encoding="utf-8"),
                                             encoding="utf-8")
            else:
                (d / "pedido.md").write_text(MOLDE_PEDIDO.format(id=fid), encoding="utf-8")
            print(f"  criado filmes/{fid}/ — pedido.md, local/, baseline/")
            if origem:
                print(f"  pedido copiado de {origem}")
            print("\n  as cinco etapas, em ordem: " + " → ".join(ETAPAS))
            print("  o portao de cada uma para o agente na primeira que nao fechar.\n")
            for v in rodar(fid):
                m = {"verde": "ok      ", "vermelho": "VERMELHO", "indeciso": "indeciso"}
                print(f"  {m[v.estado]} {v.etapa:<12} {v.nota}")
                for a in v.achados:
                    print(f"           · {a}")
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


MOLDE_PEDIDO = """# Pedido — {id}

Preencha os quatro campos. Sem eles o roteiro vira chute, e o chute so aparece
no fim, quando ja custa refilmagem.

- **Tema:** o que o filme conta.
- **Público:** para quem, e o que essa pessoa ja sabe.
- **Duração:** alvo em segundos ou minutos.
- **O que se aprende:** a frase que quem assistiu tem de conseguir repetir.

## Restrições

O que o filme nao pode fazer, e o que ele tem de exercitar.

## Como saber que deu certo

A pergunta que decide, e nao uma lista de desejos.
"""
