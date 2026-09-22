# 🎬 A jornada de um dado pessoal

**Filme 01 do Estúdio dos Guardiões** · 124 s · 12 planos · sem áudio obrigatório
**Tom:** jovem-adulto, divulgação — explicativo, não infantil e não corporativo.
**Protagonista:** o **Dado** — um objeto luminoso, mudo, que nasce no plano 2 e atravessa
o filme inteiro. Ele nunca fala. Quem explica são as legendas.

---

## ⚠️ Portão da Fase 0 — este arquivo precisa de assinatura

Nenhuma linha de código do estúdio será escrita antes de este roteiro ser aprovado.
Revisor, preencha e faça commit:

| Papel | Nome | Data | Veredito |
|---|---|---|---|
| Revisão de conteúdo / didática | _(pendente)_ | | |
| Revisão jurídica (citações) | _(pendente)_ | | |
| Revisão de acessibilidade | _(pendente)_ | | |

### Checklist de aprovação

Aplique item a item. Todo "não" precisa virar um comentário no PR.

1. [ ] Cada plano casa com **1–2 artigos**, e todos do **mesmo guardião**?
2. [ ] Cada plano tem **um guardião responsável** e só um?
3. [ ] Cada legenda cabe em **≤ 2 linhas de 42 caracteres** e **≤ 15 caracteres/segundo**?
4. [ ] Cada pose/expressão citada está no **núcleo mínimo** (4 poses, 3 expressões), ou é
       um pedido explícito de arte nova?
5. [ ] A transição entre planos tem **gancho claro**? (o plano 10 é o motor do engajamento)
6. [ ] O **modo quadrinhos** cobre todos os planos sem perda de sentido — cada plano se
       explica sozinho?
7. [ ] Os **quatro planos-chave** (p02, p04, p10, p12 — nascimento, decisão, risco,
       direito) somam **≥ 40 s**?

---

## Atribuição dos artigos — verificada contra a fonte canônica

Cada linha foi conferida em `docs/assets/data/lgpd-arts.json` (campo `guardiao`).
**Esta tabela é a fonte do campo `guardiao` de cada plano** e é o que
`tools/check-filme.py` vai reexecutar em cada PR.

| Artigo | Guardião canônico | Plano |
|---|---|---|
| 5º | 🦉 Coruja | p02 |
| 9º | 🦉 Coruja | p03 |
| 8º | 🦊 Raposa | p04 |
| 7º | 🦅 Águia | p05 |
| 6º | 🐢 Tartaruga | p06 |
| 39 | 🦊 Raposa | p07 |
| 37, 38 | 🐘 Elefante | p08 |
| 33 | 🦅 Águia | p09 |
| 46 | 🐘 Elefante | p10 |
| 48 | 🦅 Águia | p11 |
| 18 | 🦅 Águia | p12 |

**Cobertura:** Coruja 2 · Raposa 2 · Águia 4 · Tartaruga 1 · Elefante 2. Os cinco
aparecem — exigência do validador.

Duas assimetrias são deliberadas e vale explicá-las a quem revisar:

- **A Águia leva 4 planos** porque ela guarda 15 artigos, entre eles as bases legais
  (7º), a transferência internacional (33), a comunicação de incidente (48) e os direitos
  do titular (18). São quatro momentos diferentes da jornada, e todos são dela.
- **A Tartaruga leva 1 plano** porque ela guarda só dois artigos na lei inteira (6º e 10).
  Em compensação, o dela é o **plano mais longo do filme** (13 s): os dez princípios são o
  coração principiológico, e o filme dá tempo a eles.

> ⚠️ **Nota de revisão.** O rascunho anterior deste roteiro atribuía o Art. 7º à Raposa,
> o 39 à Tartaruga e o 18 à Raposa — seis dos doze planos estavam com o guardião errado.
> O erro veio de seguir a intuição narrativa (quem está em cena) em vez da fonte canônica
> (quem guarda o artigo). Os dois conceitos são diferentes e o segundo manda:
> **o campo `guardiao` diz de quem é o capítulo, não quem aparece no quadro.**

---

## Os 12 planos

Legenda dos campos de cada plano, obrigatórios em todos (regra "uma cena, uma mensagem
verificável"):

- **Objetivo pedagógico** — o que o espectador passa a saber
- **Afirmação jurídica principal** — a única afirmação normativa do plano
- **Artigo(s) canônico(s)** — conferidos na tabela acima
- **Pergunta** — o que o espectador deve conseguir responder ao fim do plano

---

### p01 — Abertura · 6 s · sem artigo

**Cenário:** fundo neutro, o pentágono do site.
**Ação:** o pentágono dos cinco guardiões gira e se desmonta; cada vértice vira um
personagem de corpo inteiro, que sai de quadro. Sobra o vazio e um ponto de luz.

- **Objetivo pedagógico:** anunciar que a lei vai ser contada por cinco personagens.
- **Afirmação jurídica principal:** nenhuma.
- **Artigo(s):** nenhum.
- **Pergunta:** "quem são os cinco?"

| t | Legenda |
|---|---|
| 0,5 – 5,5 | Todo dia, você deixa um rastro. |

---

### p02 — O dado nasce · 9 s · 🦉 Coruja · **Art. 5º** · ⭐ plano-chave

**Cenário:** balcão de atendimento.
**Ação:** Ana (rig da Raposa, papel Titular) preenche um formulário. O **Dado** nasce
sobre o papel — pequeno, opaco — e acende. A Coruja entra e o nomeia; a câmera aproxima.
**Poses:** Ana `neutro` → `apontando`; Coruja `apontando`. **Expressões:** Ana `surpreso`.

- **Objetivo pedagógico:** um dado pessoal é qualquer informação que identifique alguém;
  a lei já vale a partir da coleta.
- **Afirmação jurídica principal:** a lei define o que é dado pessoal, e a definição é o
  que liga a proteção.
- **Artigo(s):** Art. 5º.
- **Pergunta:** "a partir de que momento a LGPD passa a valer sobre esse número?"

| t | Legenda |
|---|---|
| 0,3 – 4,0 | Ana digita o CPF num formulário. |
| 4,3 – 8,7 | A lei dá nome a isso: dado pessoal.<br>(Art. 5º) |

---

### p03 — O que te contam · 9 s · 🦉 Coruja · **Art. 9º**

**Cenário:** balcão; o formulário vira um painel de informação.
**Ação:** a Coruja abre o painel e aponta os itens: finalidade, duração, com quem será
compartilhado. Ana lê. O Dado pulsa devagar, esperando.
**Poses:** Coruja `apontando`; Ana `neutro`. **Expressões:** Ana `neutro`.

- **Objetivo pedagógico:** transparência é ativa e prévia — o titular tem direito de
  saber antes, não depois.
- **Afirmação jurídica principal:** o titular tem direito a informação clara sobre a
  finalidade e a forma do tratamento.
- **Artigo(s):** Art. 9º.
- **Pergunta:** "o que a empresa é obrigada a te contar antes de usar o dado?"

| t | Legenda |
|---|---|
| 0,3 – 4,3 | Ana tem direito de saber o que farão |
| 4,5 – 8,7 | com o dado dela — antes, não depois.<br>(Art. 9º) |

---

### p04 — O consentimento · 11 s · 🦊 Raposa · **Art. 8º** · ⭐ plano-chave

**Cenário:** balcão; um cartão de consentimento se destaca, separado do resto.
**Ação:** a Raposa (papel Encarregado, paleta alternativa) apresenta o cartão **isolado**
dos outros textos. Ana aceita. Em seguida a Raposa mostra o mesmo cartão com um botão de
volta: consentimento se revoga.
**Poses:** Raposa `entregando` → `apontando`. **Expressões:** Raposa `neutro` → `feliz`.

- **Objetivo pedagógico:** consentimento válido é destacado, específico e revogável — não
  é uma cláusula escondida.
- **Afirmação jurídica principal:** o consentimento precisa ser destacado das demais
  cláusulas e pode ser revogado a qualquer momento.
- **Artigo(s):** Art. 8º.
- **Pergunta:** "o que faz um consentimento valer — e como ele se desfaz?"

| t | Legenda |
|---|---|
| 0,3 – 4,5 | A Raposa pede permissão em destaque, |
| 4,7 – 8,0 | separada de qualquer outro texto. |
| 8,2 – 10,8 | E ela pode ser revogada. (Art. 8º) |

---

### p05 — A rota legal · 11 s · 🦅 Águia · **Art. 7º**

**Cenário:** um painel com dez rotas partindo do Dado.
**Ação:** a Águia sobrevoa, examina as dez rotas e **carimba uma**. As outras nove apagam.
O consentimento do plano anterior acende como uma delas — não a única.
**Poses:** Águia `andando` (voo) → `apontando`. **Expressões:** Águia `neutro`.

- **Objetivo pedagógico:** consentimento é uma das dez bases legais, não a regra geral;
  todo tratamento precisa declarar a sua.
- **Afirmação jurídica principal:** a lei enumera as hipóteses em que o tratamento é
  permitido, e uma delas precisa ser escolhida.
- **Artigo(s):** Art. 7º.
- **Pergunta:** "qual é a base legal deste tratamento?"

| t | Legenda |
|---|---|
| 0,3 – 4,0 | Consentimento é só uma das dez rotas |
| 4,2 – 7,8 | que a lei permite para tratar dados. |
| 8,0 – 10,8 | A Águia carimba a escolhida. (Art. 7º) |

---

### p06 — Os dez princípios · 13 s · 🐢 Tartaruga · **Art. 6º**

**Cenário:** o casco da Tartaruga em primeiro plano.
**Ação:** a Tartaruga se interpõe entre o Dado e o resto da cena e ergue o casco. Dez
lâminas acendem uma a uma, cada uma com o nome de um princípio, lido de
`lgpd-arts.json` — **nenhum nome é digitado no roteiro**.
**Poses:** Tartaruga `protegendo`. **Expressões:** Tartaruga `neutro`.

- **Objetivo pedagógico:** ter base legal não basta; dez princípios valem para todo
  tratamento, sempre, ao mesmo tempo.
- **Afirmação jurídica principal:** todo tratamento observa a boa-fé e os dez princípios,
  independentemente da base legal escolhida.
- **Artigo(s):** Art. 6º.
- **Pergunta:** "escolhida a base legal, o que ainda continua obrigatório?"

| t | Legenda |
|---|---|
| 0,3 – 4,2 | Escolher a rota não basta. |
| 4,4 – 8,6 | Dez princípios valem para todo tratamento |
| 8,8 – 12,8 | — da finalidade à prestação de contas.<br>(Art. 6º) |

---

### p07 — Quem manda, quem executa · 10 s · 🦊 Raposa · **Art. 39**

**Cenário:** duas estações ligadas por uma linha — Controlador e Operador.
**Ação:** a Coruja (Controlador) entrega uma instrução ao Operador (rig da Tartaruga). O
Operador executa exatamente aquilo. Quando a linha é ultrapassada, ela fica vermelha e as
duas figuras passam a dividir o mesmo contorno de responsabilidade.
**Poses:** Coruja `entregando`; Operador `neutro`. **Expressões:** Operador `preocupado`
no momento em que a linha acende.

- **Objetivo pedagógico:** operador não decide; sair da instrução o equipara ao
  controlador em responsabilidade.
- **Afirmação jurídica principal:** o operador que descumpre as instruções lícitas do
  controlador responde como controlador.
- **Artigo(s):** Art. 39.
- **Pergunta:** "quem responde quando o fornecedor faz mais do que foi contratado?"

| t | Legenda |
|---|---|
| 0,3 – 4,5 | O operador só faz o que foi instruído. |
| 4,7 – 9,8 | Sair da instrução o torna responsável<br>junto. (Art. 39) |

---

### p08 — O registro · 11 s · 🐘 Elefante · **Arts. 37 e 38**

**Cenário:** arquivo; estantes de fichas.
**Ação:** o Elefante carimba cada passagem do Dado numa ficha e arquiva. Em seguida abre
um caderno maior — o relatório de impacto — e desenha o risco antes de ele acontecer.
**Poses:** Elefante `entregando` → `apontando`. **Expressões:** Elefante `neutro`.

- **Objetivo pedagógico:** registro e relatório de impacto são o que transforma prática em
  prova.
- **Afirmação jurídica principal:** controlador e operador mantêm registro das operações,
  e a ANPD pode exigir o relatório de impacto.
- **Artigo(s):** Arts. 37 e 38.
- **Pergunta:** "como você prova, amanhã, o que fez com o dado hoje?"

| t | Legenda |
|---|---|
| 0,3 – 4,4 | O Elefante registra cada operação. |
| 4,6 – 8,4 | Sem registro, não há como provar nada. |
| 8,6 – 10,8 | (Arts. 37 e 38) |

---

### p09 — A fronteira · 11 s · 🦅 Águia · **Art. 33**

**Cenário:** uma linha de fronteira; céu de um lado, céu de outro.
**Ação:** o Dado avança para a fronteira. A Águia o intercepta, confere as condições e só
então libera. A fronteira se abre com um carimbo.
**Poses:** Águia `protegendo` → `apontando`. **Expressões:** Águia `neutro`.

- **Objetivo pedagógico:** enviar dado para fora do país não é movimentação neutra;
  depende de hipótese prevista.
- **Afirmação jurídica principal:** a transferência internacional só é permitida nas
  hipóteses que a lei enumera.
- **Artigo(s):** Art. 33.
- **Pergunta:** "antes de o dado atravessar a fronteira, quem confere as condições?"

| t | Legenda |
|---|---|
| 0,3 – 4,4 | O dado quer atravessar a fronteira. |
| 4,6 – 8,2 | Nove hipóteses permitem isso — |
| 8,4 – 11,0 | e alguém precisa conferir. (Art. 33) |

---

### p10 — A segurança · 12 s · 🐘 Elefante · **Art. 46** · ⭐ plano-chave · **o susto**

**Cenário:** cofre; corredor de servidores.
**Ação:** **o plano de maior tensão do filme.** Uma porta do cofre fica destrancada e o
Dado escorrega para fora. O Elefante fecha a porta a tempo. Recuo: a mesma porta aparece
sendo desenhada na prancheta do projeto, com a tranca já prevista — a segurança não foi
remendo, foi concepção.
**Poses:** Elefante `protegendo`; Dado se retrai (composição de escala e opacidade, sem
pose nova). **Expressões:** Elefante `preocupado` → `neutro`.

- **Objetivo pedagógico:** segurança é decisão de projeto, tomada antes de existir
  incidente.
- **Afirmação jurídica principal:** as medidas de segurança devem ser adotadas desde a
  fase de concepção do produto.
- **Artigo(s):** Art. 46.
- **Pergunta:** "em que momento se decide a segurança de um sistema?"

| t | Legenda |
|---|---|
| 0,3 – 3,6 | Uma porta fica destrancada. |
| 3,8 – 7,6 | Segurança não é remendo do fim: |
| 7,8 – 11,8 | ela nasce com o produto. (Art. 46) |

---

### p11 — O alarme · 10 s · 🦅 Águia · **Art. 48**

**Cenário:** a sala do cofre; ao fundo, a ANPD.
**Ação:** o quase-incidente do plano anterior aciona um alarme. A Raposa avisa Ana; a
Águia recebe a comunicação. Ninguém esconde nada — e é isso que o plano mostra.
**Poses:** Raposa `entregando`; Águia `apontando`. **Expressões:** Raposa `preocupado`.

- **Objetivo pedagógico:** incidente relevante gera dever de comunicar, e o dever é duplo
  — autoridade e titular.
- **Afirmação jurídica principal:** o controlador comunica à ANPD e ao titular a ocorrência
  de incidente de segurança que possa acarretar risco relevante.
- **Artigo(s):** Art. 48.
- **Pergunta:** "quando algo dá errado, quem precisa ser avisado?"

| t | Legenda |
|---|---|
| 0,3 – 4,2 | Incidente relevante não se esconde. |
| 4,4 – 9,8 | A ANPD e o titular precisam ser<br>avisados. (Art. 48) |

---

### p12 — O titular volta · 11 s · 🦅 Águia · **Art. 18** · ⭐ plano-chave · **fecho**

**Cenário:** de volta ao balcão do plano 2 — o círculo se fecha.
**Ação:** Ana volta e pede seus dados de volta. O pedido percorre a cadeia ao contrário:
Raposa recebe, Coruja autoriza, Tartaruga executa, Elefante registra a eliminação. O Dado
se apaga por vontade de quem sempre foi seu dono. Os cinco ficam de pé em volta do lugar
onde ele estava; o pentágono se remonta.
**Poses:** todos `neutro`, em pé. **Expressões:** Ana `feliz`.

- **Objetivo pedagógico:** os direitos do titular são exercíveis na prática, com prazo, e
  fecham o ciclo que a coleta abriu.
- **Afirmação jurídica principal:** o titular tem direito a obter do controlador, entre
  outros, o acesso e a eliminação dos seus dados.
- **Artigo(s):** Art. 18.
- **Pergunta:** "o dado é de quem?"

| t | Legenda |
|---|---|
| 0,3 – 4,2 | Ana pede seus dados de volta. |
| 4,4 – 8,0 | São nove direitos, e o relógio corre. |
| 8,2 – 10,8 | O dado sempre teve dono. (Art. 18) |

---

## Transcrição corrida

O texto abaixo é o que o leitor de tela recebe e o que vai no `<details>` do player.
É a **mesma** trilha de legendas, na ordem — nenhuma informação do filme existe só na
imagem.

> Todo dia, você deixa um rastro. Ana digita o CPF num formulário. A lei dá nome a isso:
> dado pessoal (Art. 5º). Ana tem direito de saber o que farão com o dado dela — antes,
> não depois (Art. 9º). A Raposa pede permissão em destaque, separada de qualquer outro
> texto. E ela pode ser revogada (Art. 8º). Consentimento é só uma das dez rotas que a lei
> permite para tratar dados. A Águia carimba a escolhida (Art. 7º). Escolher a rota não
> basta. Dez princípios valem para todo tratamento — da finalidade à prestação de contas
> (Art. 6º). O operador só faz o que foi instruído. Sair da instrução o torna responsável
> junto (Art. 39). O Elefante registra cada operação. Sem registro, não há como provar
> nada (Arts. 37 e 38). O dado quer atravessar a fronteira. Nove hipóteses permitem isso —
> e alguém precisa conferir (Art. 33). Uma porta fica destrancada. Segurança não é remendo
> do fim: ela nasce com o produto (Art. 46). Incidente relevante não se esconde. A ANPD e
> o titular precisam ser avisados (Art. 48). Ana pede seus dados de volta. São onze
> direitos, e o relógio corre. O dado sempre teve dono (Art. 18).

---

## Elenco e o que a Fase 1 precisa desenhar

| Papel no filme | Rig | Aparece em |
|---|---|---|
| **o Dado** (protagonista mudo) | `dado` (prop, não personagem) | todos |
| Ana — Titular | `raposa` | p02, p03, p04, p12 |
| Encarregado / DPO | `raposa`, paleta alternativa | p04, p11, p12 |
| Controlador | `coruja` | p02, p03, p07, p12 |
| Operador | `tartaruga` | p06, p07, p12 |
| Registro / Segurança | `elefante` | p08, p10, p12 |
| ANPD | `aguia` | p05, p09, p11, p12 |

**Ordem de desenho da Fase 1** — primeiro o **Dado**, depois **Raposa** e **Coruja** (os
dois de maior tempo de tela). Validação visual nesses três; só então Águia, Tartaruga e
Elefante. A Fase 2 roda com os três primeiros reais e o resto como boneco de teste.

**Núcleo mínimo exigido por este roteiro** — nada além disto é necessário para filmar:

- **Poses (4):** `neutro`, `apontando`, `entregando`, `protegendo`
  (`andando` só para o voo da Águia em p05)
- **Expressões (3):** `neutro`, `preocupado`, `feliz` (`surpreso` só para Ana em p02)

O Dado não precisa de pose: "retrair-se" em p10 é composição de escala e opacidade.

---

## O que este roteiro deliberadamente **não** faz

- **Não cita texto literal da lei.** Só números de artigo. O texto vem de
  `lgpd-arts.json` em tempo de execução.
- **Não põe informação só na imagem.** Pose, expressão e adereço reforçam a legenda,
  nunca substituem — é o que faz o modo quadrinhos e o leitor de tela funcionarem por
  construção.
- **Não usa áudio.** O filme é mudo por padrão. Se houver trilha um dia, ela é opcional e
  não carrega informação exclusiva.
- **Não esgota a lei.** São 11 artigos de 65. O filme é a porta de entrada; as páginas dos
  guardiões em `docs/` são a casa.
