---
name: fazer-filme
description: Transforma uma história em prosa num filme HTML5 dos Guardiões da Governança, percorrendo as cinco etapas com portões. Use SEMPRE ao receber um pedido de filme, animação ou vídeo sobre LGPD/governança nesta suíte; ao continuar um filme que já começou; e antes de criar qualquer cenário, prop ou pose nova. Use também quando um portão reprovar e você não souber por quê.
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

## 2. As cinco etapas

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

**A legenda é o filme.** Não há áudio. Se a informação não está na legenda, ela não existe
para quem assiste — e o modo quadrinhos entrega o filme inteiro em texto, para quem pede
movimento reduzido.

## 4. Quando a história pede algo que não existe

Crie em `filmes/<id>/local/` e declare no campo `local` do arquivo do filme. É livre.

**Não** mexa em `motor/`. Subir um adereço ao elenco compartilhado exige prova de **segundo
uso**, e quem abre essa proposta é o módulo de automelhorias — não você, no meio de um
filme. Um fiscal proíbe um filme de referenciar o `local/` de outro, e é isso que força
promoção em vez de cópia.

## 5. Antes de encerrar

```bash
python3 ci/validar_tudo.py            # exatamente o que o CI roda
python3 tests/test_navegador.py       # se tocou em motor/ ou paginas/
```

Mexeu no filme? As referências de palco precisam ser regravadas — `--gravar` — e o **diff
vai no PR**. Referência que se atualiza sozinha não é referência, é o registro do último
acidente.

## Onde ler mais

`CLAUDE.md` (doutrina e proibições duras) · `harness/agents/` (o contrato de cada papel) ·
`harness/policies/` (cada regra, seu fiscal, e como ela falha) · `README.md` (o elenco e o
catálogo, em blocos derivados).
