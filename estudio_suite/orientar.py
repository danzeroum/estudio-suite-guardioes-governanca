"""Orientacao: o estado vivo, derivado. Nao descreve, nao reprova, nao escreve.

Um orientador que tambem reprovasse viraria mais um fiscal -- com regras
proprias, sem politica e sem teste -- e seria o primeiro lugar onde alguem
tentaria afrouxar algo, justamente por nao parecer um fiscal. Quem reprova e
`ci/validar_tudo.py`. Este aqui sai sempre 0.

Ele tambem nao carrega lista nenhuma: tudo que responde vem de ler o
repositorio agora. E por isso que ele continua certo sem manutencao.
"""
import subprocess

from . import inventario as inv
from . import lei as _lei
from .comum import ErroDeDados, FILMES, RAIZ, filmes_existentes, jogos_existentes


def _lei_em_dia():
    """A distancia entre a ancora e o main da origem -- em commits, se der.

    Saber que a ancora ficou para tras e util; avanca-la e change-proposal.
    Sem rede, a resposta honesta e 'nao sei', nunca 'esta em dia'.
    """
    try:
        a = _lei.ancora()
    except ErroDeDados as e:
        return f"sem ancora legivel ({e})"
    repo = RAIZ / "workspace" / "lei-git"
    if not (repo / ".git").exists():
        vizinho = RAIZ.parent / a["repo"].split("/")[-1]
        repo = vizinho if (vizinho / ".git").exists() else None
    if repo is None:
        return f"{a['sha'][:12]} (sem checkout para comparar com a origem)"
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "origin/main"],
                       capture_output=True, text=True)
    topo = r.stdout.strip()
    if not topo:
        return f"{a['sha'][:12]} (nao consegui ler o main da origem)"
    if topo == a["sha"]:
        return f"{a['sha'][:12]} — na ponta do main da origem"
    c = subprocess.run(["git", "-C", str(repo), "rev-list", "--count",
                        f"{a['sha']}..{topo}"], capture_output=True, text=True)
    n = c.stdout.strip()
    return (f"{a['sha'][:12]} — {n} commit(s) atras do main da origem"
            if n.isdigit() else f"{a['sha'][:12]} (distancia desconhecida)")


def _etapas_do_filme(fid):
    """Que artefatos deste filme ja existem. A etapa seguinte e o primeiro que falta."""
    d = FILMES / fid
    return [("pedido", (d / "pedido.md").exists()),
            ("roteiro", (d / "roteiro.md").exists()),
            ("storyboard", (d / f"{fid}.filme.js").exists()),
            ("animacao", any((d / "baseline").glob("*.txt"))),
            ("acabamento", (d / "relatorio.json").exists())]


def texto() -> str:
    L = ["Estudio Suite dos Guardioes", ""]
    L.append(f"  lei ancorada   {_lei_em_dia()}")
    try:
        el = inv.elenco()
        pes = [r for r in el if r["tipo"] == "personagem"]
        L.append(f"  elenco         {len(pes)} personagens, {len(el) - len(pes)} props, "
                 f"{len(inv.cenarios())} cenarios")
    except ErroDeDados as e:
        L.append(f"  elenco         INDISPONIVEL: {e}")
    L.append(f"  conteudo       {len(filmes_existentes())} filme(s), "
             f"{len(jogos_existentes())} jogo(s)")
    L.append("")
    L.append("  filme                 pedido roteiro storyb anima acaba   proxima etapa")
    for fid in filmes_existentes():
        et = _etapas_do_filme(fid)
        marcas = "  ".join(" ok  " if ok else " --  " for _, ok in et)
        prox = next((n for n, ok in et if not ok), "completo")
        L.append(f"  {fid:<20}  {marcas}  {prox}")
    L.append("")
    locais = {fid: sorted(p.name for p in (FILMES / fid / "local").glob("*.js"))
              for fid in filmes_existentes()}
    locais = {k: v for k, v in locais.items() if v}
    if locais:
        L.append("  adereços locais (candidatos a promocao no SEGUNDO uso):")
        for fid, arqs in locais.items():
            L.append(f"    {fid}: {', '.join(arqs)}")
    else:
        L.append("  nenhum adereço local: todo filme usa so o elenco compartilhado.")
    L += ["", "  proximo passo:",
          "    python3 -m estudio_suite inventario     # o que da para pedir ao motor",
          "    python3 -m estudio_suite validar        # o que esta vermelho agora"]
    return "\n".join(L)


def main() -> int:
    print(texto())
    return 0          # orientar nunca reprova
