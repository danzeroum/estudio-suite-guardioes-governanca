---
name: fazer-filme
description: Transforma uma história em prosa num filme HTML5 dos Guardiões da Governança, percorrendo as seis etapas com portões (a última, sonorização, é opcional e derivada). Use SEMPRE ao receber um pedido de filme, animação ou vídeo sobre LGPD/governança nesta suíte; ao continuar um filme que já começou; e antes de criar qualquer cenário, prop ou pose nova. Use também quando um portão reprovar e você não souber por quê.
---

# Fazer um filme nesta suíte

Esta página **não lista** poses, cenários, artigos nem etapas. Ela manda você perguntar —
porque uma lista escrita aqui derivaria do repositório em silêncio e passaria a ensinar um
estúdio que não existe mais.

## 1. Antes de qualquer coisa

```bash
python3 -m estudio_suite orientar
python3 -m estudio_suite inventario
```

O primeiro diz onde você está e o que falta. O segundo diz **o que dá para pedir ao motor**:
as poses, expressões, cenários e props que existem, e o vocabulário do roteiro.

Pedir uma pose que não existe não dá erro de sintaxe — dá um filme que não monta, e você
descobre três etapas depois. O núcleo é mínimo de propósito.

## 2. As seis etapas

```bash
python3 -m estudio_suite novo-filme <id> --de <pedido.md>   # começa
python3 -m estudio_suite etapas <id>                        # onde parei, e o que falta
```

Cada etapa tem um artefato e um portão. **Não avance no vermelho** — o portão está dizendo
que o custo de continuar é maior que o de voltar. Um portão `indeciso` também não é verde:
ele está dizendo que não conseguiu medir.

A ordem importa e é cara de inverter. A etapa `roteiro` não tem uma linha de código porque
é onde a citação errada custa uma edição de texto.

## 3. As três coisas que se erra aqui

**O guardião de um artigo não é quem está em cena.** É quem responde por ele na fonte
canônica. Seguir a intuição narrativa já produziu seis planos errados de uma vez, num
filme que parecia certo.

**Número sobre a lei se conta, não se lembra.** "Os onze direitos do Art. 18" chegou a ser
publicado; o artigo tem nove. Toda afirmação contável de uma legenda é conferida contra os
incisos do caput.

**A legenda é o filme; o áudio é camada derivada.** Toda a informação mora na legenda — o
modo quadrinhos entrega o filme inteiro em texto. Existe uma camada de áudio **opcional**
(dublagem sintética, ancorada em `voz.lock`, botão **Som** desligado por padrão): quem
edita legenda — texto, tempo ou o campo `quem` — deixa dívida até redublar. O filme que
não declara `audio: true` no próprio `filme.js` é **mudo por declaração**: o job dublador
do CI não o aciona nem o processa, e o `dublar` recusa dublá-lo (trilha sem declaração é
a dívida que o portão de sonorização aponta). O caminho
portátil é `ferramentas/dublador/dublar.sh <id>` (imagem Docker que materializa o `voz.lock`:
funciona em qualquer host); dublar direto só funciona se o ambiente da máquina bater com o
lock — e o próprio dublar confere e recusa na divergência (incluindo a classe de SIMD,
lida de flags medidas e gravada no `audio.json`). Desde a CP-012 o `audio.json` também
carrega o **hash do PCM mixado** (`mix.pcm_f32_sha256`) — o contrato que o job dublador
prova (CP-013): cópias **AVX-512 visíveis** exigem o hash bater com o codec sob teto
decodificado; cópias **avx2 saem cedo** (sem gate, sem build, sem medir a âncora —
a decisão do dono de 24/09/2026; a observação de verdade é o dispatch manual
`observar_avx2`, "observação, sem gate"). Sem o hash, o fiscal de redublagem aponta a dívida. As vozes e poses não se listam aqui:
`orientar` e `inventario` respondem.

## 4. Quando a história pede algo que não existe

Crie em `filmes/<id>/local/` e declare no campo `local` do arquivo do filme. É livre.

**Não** mexa em `motor/`. Subir um adereço ao elenco compartilhado exige prova de **segundo
uso**, e quem abre essa proposta é o módulo de automelhorias — não você, no meio de um
filme. Um fiscal proíbe um filme de referenciar o `local/` de outro, e é isso que força
promoção em vez de cópia.

## 5. Antes de encerrar

```bash
python3 ci/validar_tudo.py            # o gate único (fiscais, derivados, redublagem)
python3 tests/test_*.py               # cada camada tem seu teste; o CI roda todos
python3 ci/portao_sonorizacao.py      # a trilha, medida pela audio-suite (se dublado)
python3 tests/test_navegador.py       # se tocou em motor/ ou paginas/
```

Mexeu no filme? As referências de palco precisam ser regravadas — `--gravar` — e o **diff
vai no PR**. Referência que se atualiza sozinha não é referência, é o registro do último
acidente.

Mexeu em **legenda** de filme dublado? `ferramentas/dublador/dublar.sh <id>` regenera a
dublagem na imagem que materializa o `voz.lock` (ou `python3 -m estudio_suite dublar <id>`
se o ambiente da máquina já bater com o lock), e `vozes compare <id> --gravar` regrava a
carteira de voz quando a voz mudou — os diffs vão no PR. Editar legenda sem redublar é a
mesma dívida de editar o filme sem regravar a referência, e o fiscal acusa as duas.

## Onde ler mais

`CLAUDE.md` (doutrina e proibições duras) · `harness/agents/` (o contrato de cada papel) ·
`harness/policies/` (cada regra, seu fiscal, e como ela falha) · `README.md` (o elenco e o
catálogo, em blocos derivados).
