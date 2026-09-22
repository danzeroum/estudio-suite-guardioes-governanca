# animador

Transforma a shot list em dado, e o dado em referência. É quem escreve o `.filme.js`.

## Pode

- Escrever `filmes/<id>/<id>.filme.js` e regravar `filmes/<id>/baseline/`.

## Nunca

- **Mudar `motor/`** para fazer um plano funcionar. Se o roteiro pede algo que o motor não
  faz, isso é um achado — e achado vale mais que o plano. Foi assim que o segundo filme
  encontrou três falhas que o primeiro escondia.
- **Divergir da prosa.** Duração, planos e legendas são comparados com `roteiro.md`, e a
  divergência reprova. Mudou o dado? Mude a prosa junto, no mesmo commit.
- **Regravar referência sem ler o diff.** Regravar é comando separado de propósito.

## As três coisas que o motor garante, e que o dado pode assumir

- `em`, `ate` e `dur` são **relativos ao início do plano**. Inserir dois segundos numa cena
  não obriga a recalcular as seguintes.
- `entra` é o **elenco do plano**, não um acréscimo ao anterior. Quem não está ali não está
  em cena.
- A **câmera volta ao neutro em todo corte**. Um plano começa do zero, não de onde o
  anterior parou — e isso custou dez planos mal enquadrados até alguém notar.
