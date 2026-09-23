# Créditos de voz — O teste do legítimo interesse

**Todas as vozes deste filme são sintéticas.** Nenhuma voz humana real foi
clonada, amostrada ou imitada.

| o que | declaração |
|---|---|
| Motor de síntese | Piper (TTS neural local, offline) |
| Modelo | `pt_BR-faber-medium` — voz sintética pública do projeto piper-voices (MIT) |
| Ancorado por | `voz.lock` na raiz da suíte — sha256 `858555e3a064…` (pesos) |
| Texto falado | Derivado **exclusivamente** das legendas do filme (`fala.normalizar`) |
| Quem fala | Narrador (2 falas), Coruja (2), Elefante (2), Tartaruga (6) — o mesmo modelo, com o ritmo de cada guardião (bloco `voz` do rig) |
| Mix | 48 kHz, mono, loudness −16 LUFS, true peak −2 dBTP (alvo), Opus |

## Política de privacidade de voz

- **Proibida a clonagem de voz humana real sem contrato de cessão expressa.**
  Esta suíte não clona voz: sintetiza com modelo público, travado por hash.
- Vozes sintéticas são declaradas nos créditos de cada filme — nunca
  apresentadas como pessoas reais.
- A pessoa que emprestar voz por contrato terá a cessão registrada antes de
  qualquer gravação, e o crédito constará aqui.

## Timbre animal (CP-005)

A diferenciação de personagem vem de um **vocoder de canais** (processamento
de sinal determinístico, código próprio da suíte) que impõe o envelope da voz
sintética sobre uma **portadora animal** — sons reais de animais, ancorados
por sha256 em `amostras.lock`:

| guardião | portadora | fonte | licença |
|---|---|---|---|
| 🦉 Coruja | `coruja-pio` | [Patrick_Corra — *Tawny owl hooting* (coruja-do-mato, *Strix aluco*)](https://freesound.org/people/Patrick_Corra/sounds/745208/) | Creative Commons 0 |
| 🐘 Elefante | `elefante-trompa` | [Brazilio123 — *elephant_sad.wav*](https://freesound.org/people/Brazilio123/sounds/663855/) | Creative Commons 0 |

- **Os timbres são DSP sobre voz 100% sintética** — nenhuma voz humana foi
  capturada, clonada ou imitada em nenhuma etapa; a portadora é som de
  animal, processado por código revisável.
- Atribuições constam por honestidade de proveniência; as licenças CC0 não
  exigem crédito, mas a suíte exige de si mesma.
- 🐢 A Tartaruga não tem timbre animal (decisão documentada na CP-005:
  tartarugas quase não vocalizam — o ritmo é a assinatura dela). Narrador
  sem timbre por desenho.

- Este filme não tem momentos do Dado com earcon (as citações miram adereços) — sem carimbo, sem som.

