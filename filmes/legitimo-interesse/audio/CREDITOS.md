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
