#!/usr/bin/env python3
"""A prosodia expressiva, provada nos dois sentidos (CP-006, Sprint 9).

O contrato caro: a ordem da cadeia e FIXA (fala -> piper -> prosodia ->
timbre -> mix) e datada em snapshot; a duracao NUNCA muda com a modulacao de
ganho; NEUTRO (ou sem batida de expressao) e byte-identico a CP-005; pitch
e DECLARADO e NAO APLICADO enquanto pyworld nao for aprovado por humano.

O snapshot de ordem tem dois niveis, de proposito: o estagio de ganho
(puro numpy, aritmetica int16 -> float64 -> int16) tem sha ABSOLUTO pinado
-- versao de biblioteca nenhuma muda isso; o estagio scipy (vocoder) nao
tem sha absoluto porque versoes de scipy podem divergir no runner -- o que
se prova la e que a ordem IMPORTA e que e estavel entre execucoes.
"""
import hashlib
import json
import shutil
import sys
import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import dublar                         # noqa: E402
from estudio_suite import pipeline                       # noqa: E402
from estudio_suite import prosodia                       # noqa: E402
from estudio_suite import timbre                         # noqa: E402
from estudio_suite.comum import FILMES                   # noqa: E402

ok, bad = [], []
FANTASMA = "teste-prosodia-fantasma"

# Snapshot do estagio puro-numpy (ganho): muda SO se a aritmetica mudar.
GANHO_SHA_ESPERADO = "ceb168065ddc87597c722b54ddc4c7b4db25df9e01806afad39a1d25a7e5483d"


def chk(c, msg):
    (ok if c else bad).append(msg)


def _pcm_teste(n=22050):
    rng = np.random.default_rng(42)          # semente fixa: fixture, nao sorte
    x = (rng.standard_normal(n) * 8000).astype(np.int16)
    x[:200] = 0
    return x.tobytes()


def _portadora_teste(caminho: Path):
    t = np.arange(int(6.0 * 48000)) / 48000
    s = 0.6 * np.sin(2 * np.pi * 440.0 * t) + 0.2 * np.sin(2 * np.pi * 130.0 * t)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes((np.clip(s, -1, 1) * 32767).astype(np.int16).tobytes())


def _filme_fantasma(acoes=None):
    d = FILMES / FANTASMA
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    acoes = acoes if acoes is not None else [
        {"em": 1.0, "dur": 3.0, "alvo": "ana", "expressao": "feliz"},
    ]
    filme = {
        "id": FANTASMA, "titulo": "Fantasma da prosodia", "duracao": 8,
        "elenco": {"ana": {"rig": "raposa", "papel": "Titular"}},
        "planos": [{
            "id": "p01", "titulo": "Teste", "dur": 8, "guardiao": "coruja",
            "cenario": "vazio", "poster": 3, "arts": [],
            "entra": {"ana": {"x": 300, "y": 620}},
            "acoes": acoes,
            "legendas": [{"em": 0.5, "ate": 4.5, "txt": "Uma legenda que fala."},
                         {"em": 5.0, "ate": 7.5, "txt": "Outra, sem batida."}],
        }],
    }
    (d / f"{FANTASMA}.filme.js").write_text(
        "window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};"
        "window.ESTUDIO_FILMES[\"" + FANTASMA + "\"]=\n" +
        json.dumps(filme, ensure_ascii=False, indent=1) + "\n;\n", encoding="utf-8")
    return d, filme


def main():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    pcm = _pcm_teste()

    # --- ganho 0 dB: o clipe volta INTOCADO ------------------------------
    chk(prosodia.aplicar_ganho(pcm, 0.0) == pcm,
        "ganho 0 dB devolve o pcm identico — neutro e a CP-005, byte a byte")

    # --- snapshot do estagio puro-numpy (aritmetica fixa) ----------------
    com_ganho = prosodia.aplicar_ganho(pcm, -2.5)
    sha = hashlib.sha256(com_ganho).hexdigest()
    chk(sha == GANHO_SHA_ESPERADO,
        f"snapshot do ganho estavel (sha {sha[:12]}...) — aritmetica int16/float64 pinada")
    chk(com_ganho != pcm and len(com_ganho) == len(pcm),
        "ganho -2.5 dB muda a energia e NUNCA o numero de amostras (duracao preservada)")
    chk(prosodia.aplicar_ganho(pcm, -2.5) == com_ganho,
        "ganho deterministico: mesma entrada, mesmos bytes")

    # --- pitch: declarado, NAO aplicado (pyworld exige aprovacao) --------
    chk(prosodia.PITCH_DISPONIVEL is False,
        "pyworld ausente: pitch declarado, nunca aplicado por conta propria")
    m = prosodia.manifesto("feliz")
    chk(m == {"expressao": "feliz", "ritmo": 0.04, "ganho_db": 1.0,
              "pitch_st": 1.0, "pitch_aplicado": False},
        f"manifesto da prosodia declara a intencao inteira ({m})")
    chk(prosodia.manifesto(None) is None and prosodia.manifesto("neutro")["ritmo"] == 0.0,
        "sem batida: nada gravado; neutro: modulo zero, controle datado")

    # --- ritmo: soma o delta ao do rig (sintese, nao time-stretch) ------
    chk(abs(prosodia.ritmo_total(-0.15, "preocupado") + 0.23) < 1e-9
        and abs(prosodia.ritmo_total(0.05, "feliz") - 0.09) < 1e-9
        and prosodia.ritmo_total(-0.15, None) == -0.15,
        "ritmo total = ritmo do rig + delta da expressao (length_scale nativo)")

    # --- a ordem da cadeia IMPORTA e e estavel ---------------------------
    port = tmp / "portadora.wav"
    _portadora_teste(port)
    canonical = timbre.aplicar(prosodia.aplicar_ganho(pcm, 1.0), port, 0.35, 16)
    invertida = prosodia.aplicar_ganho(timbre.aplicar(pcm, port, 0.35, 16), 1.0)
    chk(canonical == timbre.aplicar(prosodia.aplicar_ganho(pcm, 1.0), port, 0.35, 16),
        "cadeia canonica (prosodia ANTES do timbre) deterministica entre execucoes")
    chk(canonical != invertida,
        "a ordem importa: prosodia->timbre != timbre->prosodia (snapshot da ordem)")
    chk(len(canonical) == len(pcm),
        "a cadeia inteira preserva o numero de amostras (time-stretch proibido)")

    # --- derivacao: a batida do falante, com janela sobreposta ----------
    d, filme = _filme_fantasma()
    P, elenco = filme["planos"][0], filme["elenco"]
    L1, L2 = P["legendas"]
    chk(prosodia.expressao_da_fala(P, L1, elenco) is None,
        "batida na ANA nao contagia a CORUJA que fala (guardiao do plano)")
    # agora um filme onde QUEM fala e a ana com batida sobreposta
    L1a = dict(L1, quem="ana")
    chk(prosodia.expressao_da_fala(P, L1a, elenco) == "feliz",
        "batida do proprio falante, janela sobreposta: expressao derivada")
    L2a = dict(L2, quem="ana")
    chk(prosodia.expressao_da_fala(P, L2a, elenco) is None,
        "janela nao sobreposta: sem expressao (a batida acabou antes)")
    # multiplas: a primeira na ordem do dado
    d, filme = _filme_fantasma(acoes=[
        {"em": 1.0, "dur": 1.0, "alvo": "ana", "expressao": "surpreso"},
        {"em": 2.0, "dur": 2.0, "alvo": "ana", "expressao": "feliz"},
    ])
    chk(prosodia.expressao_da_fala(filme["planos"][0], L1a, elenco) == "surpreso",
        "batidas multiplas: a primeira na ordem do dado ganha (estavel)")

    # --- fiscal: prosodia divergente e divida apontada -------------------
    # O fantasma fala pela TARTARUGA (rig sem timbre): o caso isola a
    # prosodia sem ruido da camada de timbre, com os DOIS clipes em dia.
    d, filme = _filme_fantasma(acoes=[
        {"em": 1.0, "dur": 1.0, "alvo": "opa", "expressao": "surpreso"},
        {"em": 2.0, "dur": 2.0, "alvo": "opa", "expressao": "feliz"},
    ])
    filme = json.loads(json.dumps(filme))
    filme["elenco"] = {"opa": {"rig": "tartaruga", "papel": "Operador"}}
    for P in filme["planos"]:
        P["guardiao"] = "tartaruga"
        for L in P["legendas"]:
            L["quem"] = "opa"
    (d / f"{FANTASMA}.filme.js").write_text(
        "window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};"
        "window.ESTUDIO_FILMES[\"" + FANTASMA + "\"]=\n" +
        json.dumps(filme, ensure_ascii=False, indent=1) + "\n;\n", encoding="utf-8")
    P = filme["planos"][0]

    def _clipes(prosodia_por_legenda):
        out = []
        for L, pros in zip(P["legendas"], prosodia_por_legenda):
            c = {"plano": "p01", "em": L["em"], "ate": L["ate"], "dur": 2.0,
                 "voz": "tartaruga/operador",
                 "texto_sha256": hashlib.sha256(
                     dublar.fala.normalizar(L["txt"]).encode()).hexdigest()}
            if pros:
                c["prosodia"] = pros
            out.append(c)
        return out

    dir_a = d / "audio"
    dir_a.mkdir()
    ambiente = __import__("estudio_suite.voz", fromlist=["voz"]).ancora()["ambiente"]
    (dir_a / "audio.json").write_text(
        json.dumps({"filme": FANTASMA, "clipes": _clipes([None, None]),
                    "ambiente": ambiente,
                    "mix": {"pcm_f32_sha256": "f" * 64}}, indent=1) + "\n",
        encoding="utf-8")
    a = pipeline.fiscal_redublagem(FANTASMA)
    chk(len(a) == 1 and "ganhou expressao" in a[0] and "surpreso" in a[0],
        f"expressao nova no filme sem redublar e divida ({a})")
    (dir_a / "audio.json").write_text(
        json.dumps({"filme": FANTASMA, "ambiente": ambiente,
                    "clipes": _clipes([prosodia.manifesto("surpreso"), None]),
                    "mix": {"pcm_f32_sha256": "f" * 64}}, indent=1) + "\n",
        encoding="utf-8")
    a = pipeline.fiscal_redublagem(FANTASMA)
    chk(a == [], f"prosodia gravada em sincronia: fiscal cala ({a})")
    (dir_a / "audio.json").write_text(
        json.dumps({"filme": FANTASMA, "ambiente": ambiente,
                    "clipes": _clipes([prosodia.manifesto("feliz"), None]),
                    "mix": {"pcm_f32_sha256": "f" * 64}}, indent=1) + "\n",
        encoding="utf-8")
    a = pipeline.fiscal_redublagem(FANTASMA)
    chk(len(a) == 1 and "prosodia divergente" in a[0],
        f"expressao que mudou sem redublar e divida ({a})")
    shutil.rmtree(d, ignore_errors=True)
    # --- os filmes reais: dublagens commitadas em dia -------------------
    for fid in ("jornada-dado", "legitimo-interesse"):
        a = pipeline.fiscal_redublagem(fid)
        chk(a == [], f"{fid}: dublagem commitada em dia com prosodia ({a})")
    m = json.loads((FILMES / "legitimo-interesse" / "audio" / "audio.json")
                   .read_text(encoding="utf-8"))
    chk(not any(c.get("prosodia") for c in m["clipes"]),
        "legitimo-interesse: nenhum clipe com prosodia — e o opus ficou "
        "byte-identico ao da CP-005 (a prova viva da camada aditiva)")
    m = json.loads((FILMES / "jornada-dado" / "audio" / "audio.json")
                   .read_text(encoding="utf-8"))
    com = [c["prosodia"]["expressao"] for c in m["clipes"] if c.get("prosodia")]
    chk(sorted(com) == ["feliz", "feliz", "neutro", "neutro", "preocupado"],
        f"jornada-dado: prosodia derivada como projetado ({com})")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"  {len(ok)} verificacoes da prosodia expressiva.")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  a expressao vira voz pelo caminho que o determinismo permite.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
