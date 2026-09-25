# CLAUDE.md — doutrina operacional desta suíte

> **Acabou de clonar?** `python3 -m estudio_suite orientar`. Ele responde o que existe, o
> que está vermelho agora e qual é o próximo passo. Não presuma nada que ele possa dizer.

Duas frases explicam quase todas as decisões daqui:

> **A história é dado; o motor é o padrão. Quem escreve o filme não escreve JavaScript.**
>
> **Personagem novo não nasce de uma história — nasce da segunda história que pediu o mesmo.**

## Antes de encerrar qualquer tarefa

```bash
python3 ci/validar_tudo.py        # o gate único: lei, roteiros, orçamento, redublagem, derivados
python3 tests/test_*.py             # cada camada tem seu teste — o CI roda todos
python3 ci/portao_sonorizacao.py    # a trilha dublada, medida pela audio-suite (com ela instalada)
python3 tests/test_navegador.py     # o motor, quando você tocou em motor/ ou paginas/
```

O `validar_tudo` é o gate, não a íntegra do CI: os testes de cada camada e o
portão de sonorização são passos próprios do workflow — e o portão, no CI,
mede de verdade (a audio-suite é instalada isolada e pinada por SHA). O job
`dublador` (workflow próprio, disparado quando o que assina os bytes do áudio
muda) prova que a imagem `ferramentas/dublador/` reproduz o áudio commitado —
e o CI inteiro lê versões do `voz.lock`
(`ci/pins_do_lock.py`), nunca digitadas à mão. O que assina os bytes inclui o
**número de threads** da sessão do onnxruntime (CP-009) e a **classe de SIMD**
da CPU (CP-011: `classe_simd` no lock, lida de flags medidas — nunca do nome do
fabricante — e gravada como medido no `audio.json`).

**A prova do job dublador é POR AMOSTRAGEM DA FROTA (CP-013), em DUAS
ONDAS (CP-015)**, e só acorda para filmes que declaram `audio: true`
(lido do próprio `filme.js` — filme mudo não aciona o job nem entra
nele). A decisão do dono (24/09/2026, saída (e)) sobre a medição:
**"a prova decisiva é bytes do PCM mixado em cópia AVX-512 visível;
AVX2 é observação; sem amostra decisiva é vermelho nomeado"**; a do
25/09/2026 (CP-015) completou: **"N pela fração da janela móvel da
frota; segunda onda automática quando a primeira não tiver AVX-512;
rerun humano deixa de ser o caminho de volta"**. O job dispara **N
cópias por ONDA** cujo N nasce do `voz.lock` (bloco `frota`,
**recalculado da fração das últimas J execuções do registro
`harness/frota/execucoes-gate.json`** — o menor N com P(zero cópia
AVX-512) ≤ 2%; o teste recalcula e reprova **"N desatualizado"** se o
lock divergir; mudança de N é PR de manutenção, nunca commit
automático). Cada cópia **classifica primeiro** (classificador único de
`estudio_suite/voz.py`): `avx512` → build e prova completa da CP-012
(o **hash do PCM mixado** `mix.pcm_f32_sha256` do `audio.json` tem de
bater, o `.opus` decodificado fica sob o **teto do lock** — base medida
−80,9 + margem 6 = −74,9, abaixo de −60 — e o **controle do teto**
reprova citando o número); `avx2` → **sai cedo** (CP-014): publica
classe e identidade rotulada (campos de síntese
`nao_aplicavel:classe_avx2` — `medido:`/`falhou:`/`nao_aplicavel:`,
nunca texto com "ou") e termina **neutra**, sem build e **sem medir a
âncora** ("medir o mesmo arquivo em toda cópia não traz informação").
A observação de verdade — regenerado × âncora, fala a fala, com build
— é o **dispatch manual `observar_avx2`** ("observação, sem gate").
Se a **primeira onda** termina com ZERO cópias AVX-512, o **roteador**
(`ci/rotear_segunda_onda.py`) acorda uma **segunda onda automática**
de N cópias no MESMO run — ilegível não vira sorte, a segunda onda
não mascara cópia que não provou. O veredito do run é do **agregador**
sobre as DUAS ondas: verde com ≥1 cópia AVX-512 idêntica e zero
divergentes; `DIVERGENCIA_AVX512` nomeia **onda e cópia**;
`SEM_AMOSTRA_DECISIVA` **só nasce após duas ondas vazias** (P = 0,0315%
com N=13 e a fração da janela — 1 em 3178) e continua vermelho
nomeado; amostra ilegível reprova, **nunca conta como neutra**. Nenhum
teto de descritor é gate; o job segue obrigatório, sem
`continue-on-error`. `audio.json` sem o hash do PCM é dívida do fiscal
de redublagem. O registro das execuções (classe por cópia, ondas,
SEM_AMOSTRA) cresce por PR de manutenção —
`ci/atualizar_registro_frota.py` junta os agregados baixados; commit
automático no main, jamais.

**Prova de bytes é contra o HEAD, nunca cópia contra cópia**:
`git diff --exit-code -- '*.opus'`. Uma "prova" que comparou arquivos
regenerados com arquivos que o próprio comando reescreveu já mentiu nesta
suíte — o `sed` de um diagnóstico reescreveu os caminhos e a comparação ficou
consigo mesma; o `git status` desmentiu. O HEAD é testemunha que não participou
da geração: só ele fecha o circuito. E o veredito de CI que importa é o que
está no **artefato** (identidade, hash por etapa, resíduos, prova aplicada) —
o log verde sem artefato já mentiu uma vez (pipe engolindo exit, CP-011).

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

`motor/`, `lei.lock`, `voz.lock`, `amostras.lock`, `ci/`, `tests/`,
`harness/policies/`, `.github/`, `ferramentas/dublador/`, `CLAUDE.md`.

Mudança neles começa por uma **change-proposal** em `harness/change-proposals/`, declarada
antes de executada. Os três locks (`lei.lock`, `voz.lock`, `amostras.lock`) são âncoras
por hash — avançar qualquer delas muda o que o repositório reproduz, e é CP sempre. A
imagem dubladora (`ferramentas/dublador/`) materializa o `voz.lock` em container: mudar
nela é mudar o que dubla, o mesmo critério. O que uma história precisa e não existe
nasce em `filmes/<id>/local/`, e sobe ao elenco compartilhado só com prova de segundo uso.

## As cinco coisas que se erra aqui

**Pedir pose que não existe.** Não dá erro de sintaxe — dá filme que não monta. O núcleo é
mínimo de propósito. `python3 -m estudio_suite inventario` responde antes.

**Errar o guardião de um artigo.** O guardião não é quem está em cena; é quem responde por
ele na fonte canônica. Seguir a intuição narrativa já produziu seis planos errados.

**Afirmar número sobre a lei.** "Os onze direitos do Art. 18" chegou a ser publicado, e o
artigo tem nove. Toda afirmação contável de uma legenda é conferida contra os incisos do
caput — e a guarda existe porque o erro passou.

**Editar legenda sem redublar.** O áudio é derivado da legenda (texto, tempo, campo
`quem`, timbre do rig, ambiente do `voz.lock`): a dublagem gravada continua sendo a do
texto anterior, e o fiscal acusa no portão storyboard. A dívida só aparece quando alguém
OUVE — rodar `ferramentas/dublador/dublar.sh <id>` custa minutos (a imagem que
materializa o lock), refilmagem custa o filme.

**Editar o filme sem regravar a referência.** As referências de palco em
`filmes/<id>/baseline/` pegam regressão de enquadramento. Regravar é comando separado
(`--gravar`), e o diff vai no PR: referência que se atualiza sozinha não é referência, é o
registro do último acidente.
