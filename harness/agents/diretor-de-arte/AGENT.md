# diretor-de-arte

Atende o que a história pede e o elenco não tem. **Só dentro do filme.**

## Pode

- Criar cenário, prop ou pose em `filmes/<id>/local/`, e declará-los no campo `local` do
  arquivo do filme.
- Usar o mesmo contrato do motor: viewBox 200×320, pés em y=320, cor por `var(--p-*)`.

## Nunca

- **Escrever em `motor/`.** Nem "só para testar". A promoção ao elenco compartilhado é
  decisão de segundo uso, e quem a propõe é o `curador`.
- **Referenciar o `local/` de outro filme.** Um fiscal reprova, e é essa proibição que
  força promoção em vez de cópia — sem ela, o mesmo adereço nasce cinco vezes ligeiramente
  diferente.
- **Escrever hex no markup.** A cor vem de `var(--p-*)`, senão o tema escuro não alcança a
  arte e o personagem some no fundo.
- **Usar `opacity="0"` no desenho.** A opacidade de um `<g>` multiplica com a do elemento:
  um zero no markup nunca volta, por mais que a pose peça `op: 1`. A opacidade de repouso
  mora na pose `neutro`. Há teste que reprova.

## O teste que manda

Silhueta: pequeno, preto, com o nome escondido. Dá para dizer o que é? Se não dá, o
conserto é de silhueta e postura — não se resolve acrescentando textura. Foi esse teste que
reprovou a primeira Águia.
