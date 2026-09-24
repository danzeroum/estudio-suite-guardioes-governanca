# Protótipo da CP-010 — pitch por guardião

Mede o que a CP-010 propõe, **sem** chamar o `dublar` e sem escrever em
`filmes/`: sintetiza as falas sozinho (piper com o modelo e a configuração
do `voz.lock`, ruído zero, ritmo do rig), desloca a F0 até o alvo de cada
guardião por duas técnicas (WORLD e TD-PSOLA), aplica o timbre do rig
(`estudio_suite.timbre`, só leitura) e mede a F0 antes e depois com o
descritor `pitch_f0` da audio-suite (danzeroum/audio-suite#44).

## Rodar do zero (um comando depois do venv)

```bash
python3 -m venv /tmp/venv-cp010
/tmp/venv-cp010/bin/pip install -r harness/prototipos/cp010/requisitos.txt
/tmp/venv-cp010/bin/python harness/prototipos/cp010/prototipo.py
```

- **Venv isolado, sempre.** Nunca instale isto no ambiente do estúdio: o
  `pyworld` é a dependência que a CP-006 deixou "a ser aprovada".
- Na primeira execução, o script baixa o modelo do `voz.lock` e as portadoras
  do `amostras.lock` e confere os dois por sha256 (diverge → para).
- `--sem-modelos-extra` pula a alternativa C (baixar outros modelos pt_BR).
- Tempo medido: ~2 min em CPU.

## O que sai (tudo em `workspace/cp010/`, gitignored e regerável)

| caminho | conteúdo |
|---|---|
| `resultado.json` | F0 atual/alvo/medida por guardião e técnica, erros em cents, distâncias entre guardiões, determinismo, modelos alternativos |
| `amostras/atual-<falante>.wav` | a voz de hoje (sem deslocamento) |
| `amostras/{world,psola}-<falante>.wav` | a voz no alvo, **para a escuta humana** que a CP pede |
| `modelos/`, `portadoras/` | âncoras baixadas e conferidas |

## Os alvos

`alvos.yaml` é dado: o **adjetivo** do rig dá a ordem e a **medição** dá a
magnitude. A derivação do passo (2,5 st) está no próprio arquivo e na CP.

## Ouvir (kit de audição, para a decisão humana)

1. Crie o venv: `python3 -m venv /tmp/venv-cp010 && /tmp/venv-cp010/bin/pip install -r harness/prototipos/cp010/requisitos.txt`
2. Gere tudo com um comando: `/tmp/venv-cp010/bin/python harness/prototipos/cp010/audicao.py` (~1 min em CPU).
3. Abra o endereço `file://…/workspace/cp010-audicao/index.html` que o comando imprime (um clique; funciona sem rede).
4. Ouça cada guardião em atual × alvo PSOLA × alvo WORLD e responda às duas perguntas da página (técnica e pares na mesma categoria).
5. Anote as respostas no PR #13. Nada é salvo nem commitado: os WAV moram em `workspace/` e se regeram.

## Estabilidade entre classes de SIMD

`estabilidade.py` roda só a etapa de pitch sobre PCM fixo em quatro níveis de CPU
(`NPY_DISABLE_CPU_FEATURES` e `GLIBC_TUNABLES`) × threads 1/2 × 2 repetições, e
grava `workspace/cp010-estabilidade/estabilidade.json`. O veredito por técnica está na CP-010.

## O que este protótipo não é

- Não é o `dublar`, não toca `filmes/*/audio` nem o `voz.lock`.
- Não decide a técnica: mede. A decisão é humana (pontos de decisão da CP).
- O TD-PSOLA usa o rastreador YIN da audio-suite por conveniência de
  protótipo. Na execução, a suíte precisa de rastreador próprio, porque a
  audio-suite é CLI externa e seu código não vira import do estúdio.
- As portadoras são decodificadas por libsndfile, não por ffmpeg como no
  estúdio. Os bytes do `.wav` podem diferir, mas o sha256 do mp3 é o do lock.
