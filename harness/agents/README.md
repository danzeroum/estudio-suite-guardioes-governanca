# harness/agents — os contratos

Cada subpasta é um papel que um agente assume sobre esta suíte. Um contrato tem três
arquivos: `AGENT.md` (identidade, o que pode, o que nunca pode), `inputs.md` (exatamente o
que lê) e `outputs.md` (exatamente o que escreve).

A regra transversal: **nenhum papel escreve em caminho protegido.** `motor/`, `lei.lock`,
`ci/`, `tests/`, `harness/policies/` e `.github/` mudam por change-proposal, declarada antes
de executada. Um agente que pode editar o próprio fiscal acaba editando o próprio fiscal.

| Papel | Escreve | Etapa |
|---|---|---|
| `roteirista` | `filmes/<id>/pedido.md`, `roteiro.md` | `recepcao`, `roteiro` |
| `diretor-de-arte` | `filmes/<id>/local/` | `storyboard` |
| `animador` | `filmes/<id>/<id>.filme.js`, `baseline/` | `storyboard`, `animacao` |
| `revisor` | comentários; nada no repositório | todas |
| `curador` | `harness/change-proposals/`, `harness/backlog.yaml` | nenhuma — vive das evidências |

O `curador` é o único que olha para a suíte em vez de para um filme, e o único cuja
matéria-prima é `harness/runs/`.
