# 🎬 Estúdio Suite dos Guardiões

**Uma história em prosa entra; um filme HTML5 acessível sai.**

Esta suíte é o padrão que anima os cinco guardiões da governança e o Dado. O motor, o
elenco e os portões são dela; cada filme é só **dado** — quem revisa o roteiro não lê
JavaScript.

> **A história é dado; o motor é o padrão.**
>
> **Personagem novo não nasce de uma história — nasce da segunda história que pediu o mesmo.**

---

## Se você é um agente, comece aqui

**Não confie em lista escrita à mão — inclusive nas deste README.** As tabelas abaixo são
geradas do estado vivo e conferidas pelo CI, mas a resposta de verdade vem de perguntar:

```bash
python3 -m estudio_suite orientar      # onde estou, o que está vermelho, qual o próximo passo
python3 -m estudio_suite inventario    # o elenco vivo: poses, expressões, cenários, limites
```

Três coisas que custam uma iteração inteira quando se erra, e que o inventário responde
antes de você escrever a primeira linha:

1. **Pose e expressão que existem.** Pedir `correndo` a um rig que tem `andando` não dá
   erro de sintaxe — dá um filme que não monta. O núcleo é mínimo de propósito.
2. **Cenário que existe.** Mesmo caso, e a lista é curta.
3. **O artigo e o guardião certos.** Toda citação é conferida contra a lei ancorada. O
   guardião de um artigo **não** é quem está em cena — é quem responde por ele na fonte
   canônica. Errar isso já produziu seis planos errados num filme.

Depois disso, leia `CLAUDE.md` (a doutrina e as proibições duras) e
`harness/policies/` (cada regra, o fiscal que a aplica e como ela falha).

## Como pedir um filme

```bash
python3 -m estudio_suite novo-filme <id> --de exemplos/pedido-curto.md
```

O agente percorre seis etapas, cada uma com **um artefato revisável e um portão**. Ele
itera dentro da etapa e nunca avança com portão vermelho:

| Etapa | Artefato | O portão pergunta |
|---|---|---|
| `recepcao` | `pedido.md` | tem tema, público, duração alvo e o que se quer ensinar? |
| `roteiro` | `roteiro.md` (prosa + shot list) | toda citação bate com a lei e com o guardião dono? |
| `storyboard` | `<id>.filme.js` + folha de contato | **a história se lê sem som e sem movimento?** |
| `animacao` | referências de palco | pureza de `renderizar(t)`, câmera neutra, elenco por plano |
| `acabamento` | `relatorio.json` | acessibilidade, contraste, orçamento, legibilidade da legenda |
| `sonorizacao` | `audio/<id>.opus` + `audio.json` | a trilha declarada está dentro das âncoras? (audio-suite externa; ausente → INDECISO) |

A ordem é cara de inverter. A etapa `roteiro` **não tem uma linha de código** de propósito:
errar o roteiro custa uma edição de texto; errar depois custa refilmagem.

## Quando a história pede algo que não existe

Crie em **`filmes/<id>/local/`** — é seu, é livre, e o filme declara no campo `local`.

Subir ao elenco compartilhado exige **prova de segundo uso**: um fiscal proíbe um filme de
referenciar o `local/` de outro, e o módulo de automelhorias abre a proposta quando a mesma
forma aparece pela segunda vez. É a regra "abstração só nasce na segunda repetição", com o
módulo contando as repetições em vez de alguém lembrar delas.

---

## O elenco

<!-- DERIVADO:elenco -->
**Personagens** — todos partilham uma viewBox (200×320, pés em y=320), um vocabulário de partes e uma API.

| rig | quem é | escala | poses | expressões |
|---|---|---|---|---|
| `aguia` | Águia — Visão de Fronteira | 0.96 | `andando` · `apontando` · `entregando` · `neutro` · `protegendo` | `feliz` · `neutro` · `preocupado` · `surpreso` |
| `coruja` | Coruja — Bússola Ética | 0.92 | `andando` · `apontando` · `entregando` · `neutro` · `protegendo` | `feliz` · `neutro` · `preocupado` · `surpreso` |
| `dado` | o Dado — o que eles guardam | 1 | `aceso` · `neutro` · `retraido` | `neutro` |
| `elefante` | Elefante — Memória e Segurança | 1 | `andando` · `apontando` · `entregando` · `neutro` · `protegendo` | `feliz` · `neutro` · `preocupado` · `surpreso` |
| `raposa` | Raposa — Elo de Confiança | 0.88 | `andando` · `apontando` · `entregando` · `neutro` · `protegendo` | `feliz` · `neutro` · `preocupado` · `surpreso` |
| `tartaruga` | Tartaruga — Escudo dos Princípios | 0.84 | `andando` · `apontando` · `entregando` · `neutro` · `protegendo` | `feliz` · `neutro` · `preocupado` · `surpreso` |

**Props** — mesmo contrato dos personagens, para o roteiro não precisar saber a diferença.

| prop | o que é | poses |
|---|---|---|
| `form` | o formulário | `neutro` · `preenchido` |
| `aviso` | o aviso | `aberto` · `neutro` |
| `cartao` | o consentimento | `aceito` · `neutro` · `revogado` |
| `selo` | o carimbo | `carimbado` · `neutro` |
| `ficha` | a ficha | `arquivada` · `neutro` |
| `porta` | a porta do cofre | `entreaberta` · `fechada` · `neutro` · `projeto` |
| `alarme` | o alarme | `neutro` · `tocando` |
<!-- /DERIVADO:elenco -->

## Os cenários

<!-- DERIVADO:cenarios -->
| cenário | onde é |
|---|---|
| `arquivo` | O arquivo |
| `balcao` | O balcão de atendimento |
| `cofre` | O cofre |
| `estacoes` | Controlador e Operador |
| `fronteira` | A fronteira |
| `painel` | O painel das dez rotas |
| `principios` | Os dez princípios |
| `vazio` | Fundo neutro |

São 8. Cenário que uma história pede e não existe nasce em `filmes/<id>/local/` — e só sobe para cá quando um **segundo** filme pedir o mesmo.
<!-- /DERIVADO:cenarios -->

## O vocabulário do roteiro

<!-- DERIVADO:vocabulario -->
| campo | valores aceitos |
|---|---|
| ação (verbo) | `estado` · `evento` · `expressao` · `para` · `pose` |
| propriedade animável | `escala` · `op` · `x` · `y` · `zoom` |
| evento | `citar` · `destacar` · `marco` |
| easing | `degrau` · `elastico` · `entrada` · `linear` · `saida` · `suave` |
| camada do palco | `atores` · `cena` · `cenario` · `efeitos` · `fundo` · `props` |

Lido do motor em tempo de execução (`estudio_suite/comum.py`), nunca redigitado: duas cópias de um vocabulário divergem em silêncio.
<!-- /DERIVADO:vocabulario -->

## O que já existe

<!-- DERIVADO:catalogo -->
| filme | planos | duração | falas | artigos |
|---|---|---|---|---|
| [A jornada de um dado pessoal](paginas/player.html?filme=jornada-dado) `jornada-dado` | 12 | 124 s | 30 | 5, 6, 7, 8, 9, 18, 33, 37, 38, 39, 46, 48 |
| [O teste do legítimo interesse](paginas/player.html?filme=legitimo-interesse) `legitimo-interesse` | 5 | 42 s | 12 | 9, 10, 38 |

| jogo | artigo | opções | situações |
|---|---|---|---|
| [Sala do Titular](paginas/jogo.html?jogo=sala-do-titular) `sala-do-titular` | Art. 18 | 9 | 12 |
<!-- /DERIVADO:catalogo -->

## A lei

<!-- DERIVADO:lei -->
A lei vem de **[danzeroum/guardioes-governanca](https://github.com/danzeroum/guardioes-governanca)**, no commit `1c349ea92518…`, e é conferida byte a byte a cada execução.

| arquivo ancorado | sha256 |
|---|---|
| `docs/assets/css/theme.css` | `41e60629528c…` |
| `docs/assets/data/gap-matrix.json` | `1178c58d6f82…` |
| `docs/assets/data/lgpd-arts.json` | `1cab81b5dc54…` |

Materializada em `workspace/lei/`, que o `.gitignore` recusa. Avançar a âncora é **change-proposal**: pode mudar o que um filme já publicado afirma.
<!-- /DERIVADO:lei -->

---

## Rodando

```bash
pip install playwright && python3 -m playwright install chromium   # uma vez

python3 -m estudio_suite validar          # o gate único — idêntico ao CI
python3 -m estudio_suite orientar         # o estado vivo
python3 tests/test_navegador.py           # o motor, em Chromium, inclusive file://
python3 tests/test_navegador.py --gravar  # regrava as referências (leia o diff!)
python3 ci/sincronizar_derivados.py       # regera README e catálogo
```

Códigos de saída: `0` conforme · `1` divergência entre o declarado e o real · `2` algum
fiscal **não conseguiu** fiscalizar. Os dois últimos são estados diferentes de propósito:
colapsá-los faria "estou sem a lei" e "o roteiro está errado" ficarem indistinguíveis, e a
leitura barata venceria.

Sem servidor: as páginas abrem por `file://`. Não há `fetch` nem módulo ES em lugar nenhum,
e há teste que reprova quem introduzir um dos dois.

## A camada de áudio (CP-004 e CP-005)

O filme nasce mudo e **continua completo sem som**: a legenda carrega toda a
informação, e o modo quadrinhos entrega o filme inteiro em texto. O áudio é
camada **aditiva e derivada** — a única fonte do texto narrado é o `txt` da
legenda, normalizado por `estudio_suite/fala.py` ("(Art. 10)" vira "artigo
dez"). Não existe roteiro de áudio separado. Desde a CP-005, o **timbre animal** (vocoder de canais sobre portadoras CC0 ancoradas em `amostras.lock`) e os earcons do Dado moram na mesma camada — ver `harness/change-proposals/CP-005-timbre-guardioes.yaml`. No modo quadrinhos (CP-006), cada plano com fala tem **"Ouvir este plano"**.

- **`ferramentas/dublador/dublar.sh <id>`** é o caminho portátil: constrói a imagem
  que **materializa o `voz.lock`** (base pinada por digest, ffmpeg/libopus na versão
  exata, pins pip do lock, ENV de threads do lock, sempre `linux/amd64`) e dubla dentro
  dela — em qualquer host com Docker, Debian ou não. Dublar direto (`python3 -m
  estudio_suite dublar <id>`) só funciona se o ambiente da máquina **bater com o
  lock** (python, piper, onnxruntime, numpy/scipy, ffmpeg, libopus, arquitetura e
  threads da sessão — o dublar mede tudo e
  recusa na divergência, nomeando pacote, versão e correção — e a **classe de SIMD**
  desde a CP-011: lida de flags medidas, gravada no `audio.json`). O dublar sintetiza um clipe
  por legenda (Piper local, modelo ancorado por sha256 em `voz.lock`, o `lei.lock`
  das vozes) e mixa em `filmes/<id>/audio/<id>.opus` — 48 kHz, mono, loudness
  −16 LUFS. Clipe que estoura o tempo da legenda **reprova**: nunca
  time-stretch, nunca reamostrar — encurta-se a legenda. No CI, o job `dublador`
  roda **só para filmes que declaram `audio: true`** (lido do próprio `filme.js` —
  filme mudo não aciona) e aplica a **prova por amostragem da frota**
  (CP-013, executando a decisão do dono de 24/09/2026, saída (e): "a prova
  decisiva é bytes do PCM mixado em cópia AVX-512 visível; AVX2 é observação;
  sem amostra decisiva é vermelho nomeado"). O job dispara **N cópias** com
  N do `voz.lock` (bloco `frota`, derivado da fração medida 38/97 — menor N
  com P(zero cópia AVX-512) ≤ 2%; o teste recalcula de
  `harness/frota/execucoes.json`). Cada cópia **classifica primeiro**: as
  **AVX-512** fazem a prova completa da CP-012 — o **hash do PCM mixado**
  (`mix.pcm_f32_sha256` do `audio.json`) tem de bater e o `.opus` decodificado
  fica sob **tolerância decodificada** (teto do lock: base medida −80,9 dBFS +
  margem 6 = −74,9, abaixo do piso de −60, com **controle positivo** que
  reprova citando o número) — o log diz "PCM idêntico; codec dentro do teto";
  as **AVX2 saem cedo** (CP-014): publicam classe e identidade rotuladas
  (campos de síntese `nao_aplicavel:classe_avx2`) e terminam **neutras** —
  sem build, sem gate e **sem medir a âncora** ("medir o mesmo arquivo em
  toda cópia não traz informação": 33 cópias mediram valores idênticos na
  CP-013; o gate de descritores morreu com o `TETO_NAO_DISCRIMINA` medido
  da CP-012). A observação de verdade — **regenerado × âncora, fala a
  fala** (duração, loudness, F0, centróide), com build — é o **dispatch
  manual `observar_avx2`**, rotulado "observação, sem gate". O
  **agregador** decide o run: verde com ≥1 cópia AVX-512 idêntica e zero
  divergentes; `DIVERGENCIA_AVX512` nomeia a cópia; `SEM_AMOSTRA_DECISIVA`
  (zero avx512) é vermelho nomeado — rerun; amostra ilegível reprova, nunca
  neutra. Hash **por etapa** (PCM cru → prosódia → timbre → mix → `.opus`),
  classe, máquina, números e veredito seguem no artefato de identidade de
  cada cópia e no agregado do run — que publica a **entrada de registro**
  da execução (classe por cópia, `SEM_AMOSTRA` sim/não) para o registro
  versionado `harness/frota/execucoes-gate.json` crescer **por PR de
  manutenção** (nunca commit automático no main): é dele que
  `ci/independencia.py` recalcula a taxa de `SEM_AMOSTRA` e a correlação
  intra-execução contra a binomial do lock — a independência das cópias é
  monitorada de dados versionados, não assumida.
- No player, o botão **Som nasce desligado**; sem trilha, ele nem aparece.
  `renderizar(t)` segue pura: o áudio é escravo do tempo, nunca dono dele.
- O **fiscal de redublagem** reprova quem edita legenda sem redublar — mesmo
  espírito do "editar o filme sem regravar a referência".
- O portão **`sonorizacao`** mede a trilha com a
  [audio-suite](https://github.com/danzeroum/audio-suite) (CLI externa,
  perfil `harness/perfis/guardioes-narracao.yaml`): 0 → VERDE, 1 → VERMELHO,
  ausência ou códigos 2/3 → **INDECISO** — porque "não consegui medir" não é
  "está errado", e descritor nunca reprova. O vermelho carrega a **causa**:
  `promessa-quebrada` (audio-suite prometida pelo CI e ausente — nada foi
  medido) diz outra frase que `trilha-reprovada` (FINDING da ferramenta),
  e as duas saem 1 cada uma pelo motivo certo.

> **Privacidade de voz:** proibida a clonagem de voz humana real sem
> contrato de cessão expressa. Todas as vozes são sintéticas (Piper,
> `pt_BR-faber-medium`, ancorado em `voz.lock`) e declaradas nos créditos de
> cada filme — `filmes/<id>/audio/CREDITOS.md`.

## O que esta suíte não faz

- **Arte gerada por modelo.** Os rigs são SVG revisável, que passa pelo teste de silhueta e
  aparece num diff. Imagem gerada não faz nem uma coisa nem outra.
- **Publicar.** Quem publica é o repositório consumidor.
- **Julgar se a história é boa.** Os portões dizem se o filme está correto e acessível.
  Se ele emociona, é revisão humana.

## Aviso

Material **educativo**, não parecer jurídico. A metáfora dos guardiões ajuda a organizar e
lembrar a lei; qualquer decisão de conformidade real deve ser validada com a área
jurídica/DPO e com o texto oficial da LGPD.
