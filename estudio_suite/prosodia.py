"""A prosodia expressiva: a batida de expressao do filme vira voz (CP-006).

Os rigs declaram as expressoes desde a CP-004 (dado inerte, backlog B) e os
filmes datam cada batida como acao -- para o ROSTO. Este modulo liga o dado
a VOZ pelo caminho que o determinismo permite:

  - ritmo: delta no length_scale do Piper (parametro de SINTese, nativo --
    o mesmo caminho do ritmo de guardiao desde a CP-004; nao e time-stretch
    do audio renderizado, e a voz nascendo no ritmo);
  - ganho: envelope deterministico sobre o clipe (int16 -> float -> ganho ->
    clip -> int16), aplicado ANTES do timbre (ordem fixa da cadeia);
  - pitch: DECLARADO no mapa e no manifesto, NAO APLICADO enquanto pyworld
    nao for aprovado. Ressintese F0 com duracao preservada e a ferramenta
    certa; instalar dependencia sem discutir e proibicao da CP. O manifesto
    ja nasce com pitch_aplicado: false -- o dia da aprovacao, vira true.

A expressao de cada fala DERIVA do dado que ja existe: a acao de expressao
cujo alvo resolve para o MESMO rig do falante e cuja janela sobrepoe a da
legenda. O falante sem batida propria fala NEUTRO -- a expressao do OUTRO
na cena nao contagia a voz de quem fala.
"""
import re

import numpy as np

# Mapa expressao -> modulacao, como DADOS (CP-006). Os valores de partida:
# "levemente" virou +0.04 de ritmo e +1 dB; o envelope do preocupado fica no
# meio da faixa pedido (-2 a -3 dB). Mudar aqui muda a voz de filmes
# publicados -- e o fiscal de redublagem que cobra a redublagem.
EXPRESSOES = {
    "neutro":     {"ritmo": 0.0,  "ganho_db": 0.0,  "pitch_st": 0.0},
    "feliz":      {"ritmo": 0.04, "ganho_db": 1.0,  "pitch_st": 1.0},
    "preocupado": {"ritmo": -0.08, "ganho_db": -2.5, "pitch_st": 0.0},
    "surpreso":   {"ritmo": 0.0,  "ganho_db": 0.0,  "pitch_st": 2.0},
}

# pyworld ausente no ambiente e no CI. Aprovacao humana primeiro; enquanto
# isso, pitch e declaracao com nome, nunca alteracao silenciosa de voz.
PITCH_DISPONIVEL = False


def _sem_acento(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def expressao_da_fala(P: dict, L: dict, elenco: dict):
    """A expressao que o FALANTE mostra durante a propria fala, ou None.

    Regra deterministica, do dado que JA existe: acao {alvo, expressao, em,
    dur} cujo alvo resolve para o MESMO rig do falante (quem -> elenco;
    guardiao do plano como rig) e cuja janela [em, em+dur] sobrepoe a
    janela da legenda. Multiplas: a primeira na ordem do dado -- estavel.
    """
    quem = L.get("quem")
    if quem:
        fala_rig = (elenco.get(quem) or {}).get("rig") or ""
    else:
        fala_rig = P.get("guardiao") or ""
    if not fala_rig:
        return None
    em_abs, ate_abs = L["em"], L["ate"]
    for a in P.get("acoes") or []:
        if not a.get("expressao"):
            continue
        alvo_rig = (elenco.get(a.get("alvo"), {}) or {}).get("rig", a.get("alvo"))
        ini = a["em"]
        fim = a["em"] + (a.get("dur") or 0)
        if alvo_rig == fala_rig and ini < ate_abs and fim > em_abs:
            return a["expressao"]
    return None


def ritmo_total(ritmo_do_rig: float, expressao) -> float:
    """O ritmo da sintese: o do rig + o delta da expressao.

    E aqui que 'pausas mais longas' acontece SEM time-stretch: o length_scale
    do Piper alonga a SINTese (fonemas e pausas nascem mais longos), o
    mesmo caminho nativo que diferencia guardioes desde a CP-004.
    """
    if not expressao or expressao not in EXPRESSOES:
        return ritmo_do_rig
    return ritmo_do_rig + EXPRESSOES[expressao]["ritmo"]


def aplicar_ganho(pcm: bytes, ganho_db: float) -> bytes:
    """Envelope de ganho deterministico sobre o clipe PCM16 22050.

    0 dB devolve o pcm INTOCADO, byte a byte. Ganho nao toca numero de
    amostras: a duracao e preservada por construcao (o ganho nao e
    time-stretch). Int16 -> float64 -> ganho -> clip -> int16, sem sorte.
    """
    if ganho_db == 0:
        return pcm
    g = 10.0 ** (ganho_db / 20.0)
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
    y = np.round(np.clip(x * g, -32767.0, 32767.0)).astype(np.int16)
    return y.tobytes()


def manifesto(expressao) -> dict:
    """O que o audio.json grava por clipe: a prosodia declarada e aplicada.

    pitch_aplicado e false enquanto pyworld nao for aprovado -- e o manifesto
    ja nasce pronto para o dia em que vira true, sem mudanca de formato.
    """
    if not expressao or expressao not in EXPRESSOES:
        return None
    m = EXPRESSOES[expressao]
    return {
        "expressao": expressao,
        "ritmo": m["ritmo"],
        "ganho_db": m["ganho_db"],
        "pitch_st": m["pitch_st"],
        "pitch_aplicado": bool(PITCH_DISPONIVEL and m["pitch_st"] != 0),
    }
