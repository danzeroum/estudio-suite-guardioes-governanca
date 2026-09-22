# Política: quem propõe não aplica no que morde

**A regra.** O módulo de automelhorias propõe sempre e aplica sozinho **só o aditivo e
reversível**: regravar referência depois de mudança aprovada, ressincronizar bloco derivado,
abrir issue. Motor, contrato público, fiscais, `lei.lock` e as próprias políticas são
caminhos protegidos.

**Por quê.** Uma trava que o vigiado pode desligar em silêncio não é uma trava. Um módulo
que pode editar o próprio fiscal acaba editando o próprio fiscal — não por má-fé, mas
porque é o caminho mais curto para o verde.

**Evidência, nunca gosto.** Todo sinal carrega o fato que o produziu, para quem lê a
proposta poder discordar do número em vez de discordar do autor.

**Aviso não é proposta.** Um arquivo a 71% do teto não precisa de ninguém agora. Abrir
proposta para ele encheria a fila de coisas que não são para fazer — e fila que ninguém lê
é fila que não existe.

---
Fiscalizado por: `ci/auditar_melhorias.py`, que **não é escrito pelo módulo**.
Falha como: **exit 1**, nomeando a proposta de risco não-baixo sem aval humano, ou o
caminho protegido que saiu da lista.
