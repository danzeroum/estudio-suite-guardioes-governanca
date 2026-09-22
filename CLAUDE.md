# CLAUDE.md — doutrina operacional desta suíte

> **Acabou de clonar?** `python3 -m estudio_suite orientar`. Ele responde o que existe, o
> que está vermelho agora e qual é o próximo passo. Não presuma nada que ele possa dizer.

Duas frases explicam quase todas as decisões daqui:

> **A história é dado; o motor é o padrão. Quem escreve o filme não escreve JavaScript.**
>
> **Personagem novo não nasce de uma história — nasce da segunda história que pediu o mesmo.**

## Antes de encerrar qualquer tarefa

```bash
python3 ci/validar_tudo.py        # exatamente o que o CI roda
python3 tests/test_navegador.py   # o motor, quando você tocou em motor/ ou paginas/
```

Códigos: `0` conforme · `1` divergência entre o declarado e o real · `2` algum fiscal
**não conseguiu** fiscalizar. Os dois últimos são estados diferentes de propósito.

## As três fronteiras de confiança

| Camada | Onde vive | Dona da verdade |
|---|---|---|
| **A lei** | `danzeroum/guardioes-governanca`, fixada em `lei.lock` | o texto da LGPD e o guardião de cada artigo |
| **O padrão** | esta suíte (`motor/`, `estudio_suite/`, `tests/`) | como se anima, e o que reprova |
| **O filme** | `filmes/<id>/` | a história: prosa, dado, adereços locais |

## Proibições duras

- **Não versionar a lei aqui.** `workspace/lei/` é materializado e conferido por hash.
  Uma cópia com uma linha removida faria o validador dizer "nenhum achado" — sem erro, sem
  aviso, indistinguível de um roteiro correto.
- **Não editar artefato derivado à mão.** Os blocos `<!-- DERIVADO:… -->` do README e o
  `catalogo.js` são gerados. Regerar é a correção: `python3 ci/sincronizar_derivados.py`.
- **Não usar `fetch` nem `type="module"`.** Sob `file://` os dois morrem, e a suíte tem de
  abrir sem servidor. Há teste que reprova quem introduzir um dos dois.
- **Não escrever `hex` no markup de um rig.** A cor vem por `var(--p-*)`, senão o tema
  escuro não alcança a arte.
- **Não afrouxar um fiscal para o CI passar.** Se um fiscal acusa, ou o repositório está
  errado, ou a decisão precisa mudar explicitamente. Editar o fiscal é a terceira opção, e
  é a errada.
- **Não acrescentar método público sem cliente real.** O contrato está travado item a item
  em `tests/test_navegador.py:CONTRATO`; entrar lá obriga a declarar quem chama.
- **Não referenciar o `local/` de outro filme.** É o que força promoção em vez de cópia.

## Caminhos protegidos

`motor/`, `lei.lock`, `ci/`, `tests/`, `harness/policies/`, `.github/`, `CLAUDE.md`.

Mudança neles começa por uma **change-proposal** em `harness/change-proposals/`, declarada
antes de executada. O que uma história precisa e não existe nasce em `filmes/<id>/local/`,
e sobe ao elenco compartilhado só com prova de segundo uso.

## As quatro coisas que se erra aqui

**Pedir pose que não existe.** Não dá erro de sintaxe — dá filme que não monta. O núcleo é
mínimo de propósito. `python3 -m estudio_suite inventario` responde antes.

**Errar o guardião de um artigo.** O guardião não é quem está em cena; é quem responde por
ele na fonte canônica. Seguir a intuição narrativa já produziu seis planos errados.

**Afirmar número sobre a lei.** "Os onze direitos do Art. 18" chegou a ser publicado, e o
artigo tem nove. Toda afirmação contável de uma legenda é conferida contra os incisos do
caput — e a guarda existe porque o erro passou.

**Editar o filme sem regravar a referência.** As referências de palco em
`filmes/<id>/baseline/` pegam regressão de enquadramento. Regravar é comando separado
(`--gravar`), e o diff vai no PR: referência que se atualiza sozinha não é referência, é o
registro do último acidente.
