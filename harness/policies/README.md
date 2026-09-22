# harness/policies — uma regra, um fiscal, um "falha como"

Cada política responde três coisas, e uma política que não responde as três não é política:
**qual é a regra**, **quem a aplica** e **como ela falha**. Regra que precisa morder ganha
schema, passo de CI ou gate — nunca um parágrafo.

| Política | A regra, em uma frase | Fiscal |
|---|---|---|
| [`lei-ancorada`](lei-ancorada.md) | A lei tem um dono, e não é esta suíte | `estudio_suite/lei.py` |
| [`orientacao-derivada`](orientacao-derivada.md) | A orientação deriva; ela não descreve | `ci/sincronizar_derivados.py --check` |
| [`segunda-repeticao`](segunda-repeticao.md) | Adereço sobe ao elenco no segundo uso, não no primeiro | `estudio_suite/melhorias/`, `tests/test_melhorias.py` |
| [`portoes`](portoes.md) | Não se avança com portão vermelho, e indeciso não é verde | `estudio_suite/pipeline.py` |
| [`automelhorias`](automelhorias.md) | Quem propõe não aplica no que morde | `ci/auditar_melhorias.py` |
