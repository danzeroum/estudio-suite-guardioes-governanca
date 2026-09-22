# roteirista — saídas

- `filmes/<id>/pedido.md` — os quatro campos: tema, público, duração, o que se aprende.
- `filmes/<id>/roteiro.md` — prosa mais a shot list, um `### pNN — título · N s · …` por
  plano, com as legendas em tabela `| t | Legenda |`.

O formato não é decoração: `estudio_suite/roteiro.py` compara a prosa com o dado e reprova
quando divergem. Roteiro que ninguém consegue comparar é roteiro que ninguém revisa.

**Nada mais.** Nenhum arquivo de motor, nenhum `.filme.js`, nenhum `local/`.
