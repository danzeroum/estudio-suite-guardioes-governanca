"""O comando dublar: da legenda ao arquivo de audio. Offline, travado, derivado.

A ordem das coisas neste comando e a doutrina em ordem de execucao -- a
CP-004 ate o mix, a CP-005 acrescentando o estagio de timbre:

1. A legenda e a UNICA fonte. Nao ha roteiro de audio: o texto e
   fala.normalizar(txt), e quem fala vem de `quem`/`plano.guardiao`/Narrador.
2. O modelo e o do voz.lock, conferido por sha256 ANTES de sintetizar.
3. Clipe que estoura o tempo da legenda REPROVA, apontando a legenda exata.
   Nao estica, nao reamostra para caber: encurta-se a legenda. (Converter a
   taxa 22050->48000 e mudanca de FORMATO, com duracao identica -- isso o
   alvo de 48 kHz da CP pede; o que a doutrina proibe e mexer na duracao.)
4. TIMBRE (CP-005): se o rig do quem-fala declara voz.timbre com portadora
   ancorada em amostras.lock, o clipe passa pelo vocoder de canais DEPOIS
   do piper e ANTES de posicionar -- fala -> piper -> timbre -> posicionar
   -> mixar. mistura 0 devolve o clipe intocado, byte a byte.
5. EARCONS do Dado (CP-005): os momentos do Dado que JA existem como dado
   no filme (pose aceso/retraido, evento citar, aceso visual via para.op=1)
   ganham carimbo sintetizado de sons/, a ~-10 dB sob a voz (ganho fixo),
   posicionados pelo `em` da acao. O Dado continua mudo: earcon nao e voz.
6. Um clipe por legenda, posicionado no seu `em` absoluto, mixado com
   loudness ancorado (-16 LUFS, true peak -2.0 dBTP) em <id>.opus 48 kHz mono.

Determinismo: piper 1.3 amostra ruido do prior (noise_scale / noise_w_scale).
Com os dois em zero, a saida e byte-identica entre execucoes -- medido
empiricamente (duas execucoes, bytes iguais), nao assumido. Foi isso, e nao
gosto, que fixou os parametros: com os defaults do piper, cada redublagem
mudaria TODOS os clips no diff, mesmo os de texto intocado, e o audio deixaria
de ser revisavel. A prosodia menos variada e o preco, e o timbre da CP-005
e o que devolve personagem sem reabrir o lock de ruido.
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
import wave
from pathlib import Path

from .comum import ErroDeDados, FILMES, RAIZ, dados_do_filme
from . import fala
from . import voz as _voz

# Loudness de ancora da CP-004 (calibrado no Sprint 5 contra a audio-suite:
# os dois filmes medidos ficaram a -16.19/-16.21 LUFS, centrados na ancora).
# O true peak alvo DEIXA 1.0 dB de folga sob o teto de -1 dBTP do perfil:
# medido no Sprint 5, o codificador opus devolve o pico ~0.48 dB ACIMA do
# alvo do loudnorm (target -1.5 decodificou como -1.02) -- sem a folga, a
# trilha passava no portao por 0.02 dB, que nao e margem, e coincidencia.
LOUDNESS_LUFS, TRUE_PEAK_DBTP = -16.0, -2.0
TAXA, CANAIS, BITRATE = 48000, 1, "40k"

# Earcons do Dado a ~-10 dB sob a voz (CP-005): ganho FIXO, sem parametro
# por filme -- o som do Dado e da suíte, e quem muda o nivel muda o lock.
GANHO_EARCON_DB = -10.0

# A tolerancia do orcamento de tempo e a quantizacao da amostra, nao margem
# de manobra: 10 ms em 22050 Hz e ~220 amostras, arredondamento de fim de
# clipe. Passou disso, estourou.
TOLERANCIA_S = 0.010


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


# ---- o bloco voz dos rigs -------------------------------------------------
def _bloco(txt: str, campo: str):
    """O texto de um objeto literal 'campo: {...}' -- sem executar JS."""
    m = re.search(rf"\b{campo}:\s*\{{", txt)
    if not m:
        return None
    i, nivel = m.end() - 1, 0
    for j in range(i, len(txt)):
        nivel += (txt[j] == "{") - (txt[j] == "}")
        if nivel == 0:
            return txt[i:j + 1]
    return None


def _pares_simples(bloco: str) -> dict:
    """Chaves de valor simples (string ou numero) de um bloco literal.

    As chaves nos rigs vem SEM aspas (objeto literal JS); os valores, entre
    aspas simples ou numericos. A versao da CP-004 so casava chave entre
    aspas -- chave que nenhum rig usa -- e o bloco voltava {}: o ritmo
    declarado de cada guardiao (Coruja -0.10, Elefante -0.15, Tartaruga
    -0.20, Raposa +0.05) era silenciosamente ignorado, e tudo sintetizava
    em length_scale 1.0. Descoberto ao estender a leitura para o sub-bloco
    timbre da CP-005; corrigido aqui, com teste de regressao que le os rigs
    REAIS em tests/test_amostras.py. O declarado e o real tem de ser a
    mesma coisa -- e isso que o lock existe para garantir.
    """
    out = {}
    for m in re.finditer(r"(?<![\w'-])([\w-]+):\s*('[^']*'|[-\d.]+)", bloco):
        v = m.group(2)
        out[m.group(1)] = v[1:-1] if v.startswith("'") else float(v)
    return out


def _tirar_subbloco(bloco: str, campo: str) -> str:
    """Apaga o par 'campo: {...}' de primeiro nivel do bloco.

    Sem isso, as chaves DENTRO do sub-bloco (ex.: o ritmo de um registro da
    Raposa) casariam como se fossem do nivel de cima, e a ultima ocorrencia
    no texto sobrescreveria o valor declarado no topo. O sub-bloco volta
    depois, lido separado.
    """
    m = re.search(rf"\b{campo}:\s*\{{", bloco)
    if not m:
        return bloco
    i, nivel = m.end() - 1, 0
    for j in range(i, len(bloco)):
        nivel += (bloco[j] == "{") - (bloco[j] == "}")
        if nivel == 0:
            return bloco[:m.start()] + bloco[j + 1:]
    return bloco


def voz_do_rig(rig_id: str) -> dict:
    """O bloco voz {...} de um *.rig.js. Voz e atributo do personagem.

    Sub-blocos conhecidos: registros (Raposa, por papel do elenco) e timbre
    (CP-005: portadora/mistura/bandas -- dado declarado, ainda sem logica
    de aplicacao nesta leitura).
    """
    f = RAIZ / "motor/js/rigs" / f"{rig_id}.rig.js"
    if not f.exists():
        return {}
    bloco = _bloco(f.read_text(encoding="utf-8"), "voz")
    if not bloco:
        return {}
    regs = _bloco(bloco, "registros")
    tim = _bloco(bloco, "timbre")
    raso = _tirar_subbloco(_tirar_subbloco(bloco, "registros"), "timbre")
    base = _pares_simples(raso)
    if regs:
        base["registros"] = {_sem_acento(k): _pares_simples(v)
                             for k, v in re.findall(
                                 r"(\w+):\s*(\{[^{}]*\})", regs)}
    if tim:
        base["timbre"] = _pares_simples(tim)
    return base


def parametros_de(ator_meta: dict) -> tuple:
    """(ritmo, rotulo) do ator: registro por papel quando o rig tem um."""
    rig = ator_meta.get("rig", "")
    v = voz_do_rig(rig)
    rotulo, ritmo = rig, float(v.get("ritmo", 0) or 0)
    reg = (v.get("registros") or {}).get(_sem_acento(ator_meta.get("papel", "")))
    if reg is not None:
        ritmo = float(reg.get("ritmo", ritmo))
        rotulo = f"{rig}/{_sem_acento(ator_meta.get('papel', ''))}"
    return ritmo, rotulo


def quem_fala(P: dict, L: dict, elenco: dict) -> tuple:
    """(texto, ritmo, rotulo, timbre) de uma legenda: quem, como e o que se fala.

    O timbre (CP-005) e do RIG -- o animal e do personagem, nao do papel: os
    dois registros da Raposa latem igual. mistura 0 ou sem portadora = None:
    a camada so existe quando declarada E medida.
    """
    texto = fala.normalizar(L["txt"])
    if L.get("quem"):
        ator = elenco[L["quem"]]
        ritmo, rotulo = parametros_de(ator)
        rig = ator.get("rig", "")
    elif P.get("guardiao"):
        ritmo, rotulo = parametros_de({"rig": P["guardiao"]})
        rig = P["guardiao"]
    else:
        return texto, fala.NARRADOR["ritmo"], "narrador", None
    tim = (voz_do_rig(rig) or {}).get("timbre") or None
    if tim and (not tim.get("portadora") or float(tim.get("mistura", 0) or 0) <= 0):
        tim = None
    return texto, ritmo, rotulo, tim


def _length_scale(ritmo: float) -> float:
    """ritmo +0.05 (5% mais rapido) -> 0.952; -0.20 -> 1.25."""
    return 1.0 / (1.0 + ritmo)


# ---- sintese --------------------------------------------------------------
def sintetizar(voice, texto: str, ritmo: float) -> tuple:
    """(bytes PCM16, duracao) — deterministico: noise zero nos dois eixos."""
    from piper import SynthesisConfig
    cfg = SynthesisConfig(length_scale=_length_scale(ritmo),
                          noise_scale=0.0, noise_w_scale=0.0)
    pcm = b"".join(c.audio_int16_bytes for c in voice.synthesize(texto, cfg))
    return pcm, len(pcm) / 2 / 22050


def _gravar_wav(caminho: Path, pcm: bytes) -> None:
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(pcm)


def mixar(clipes: list, duracao_filme: float, saida: Path, earcons=None) -> None:
    """Clipes [(pcm, em_abs, dur)] (+ earcons [(wav, em_abs)]) -> um .opus.

    O ffmpeg faz a mixagem porque ja e dependencia declarada do ambiente; um
    mixador em Python seria uma segunda implementacao de DSP para conferir
    ninguem. aresample muda o formato (22050->48000), nunca a duracao. Os
    earcons entram como entradas a mais com ganho FIXO de -10 dB -- sem
    earcons, o grafo e byte a byte o da CP-004 (a camada e aditiva).
    """
    earcons = earcons or []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        entradas, filtros, rotulos = [], [], []
        for i, (pcm, em, _dur) in enumerate(clipes):
            f = tmp / f"c{i:03d}.wav"
            _gravar_wav(f, pcm)
            entradas += ["-i", str(f)]
            ms = int(round(em * 1000))
            filtros.append(
                f"[{i}:a]aresample={TAXA},adelay={ms}:all=1[a{i}]")
            rotulos.append(f"[a{i}]")
        ganho = 10.0 ** (GANHO_EARCON_DB / 20.0)
        for j, (arquivo, em) in enumerate(earcons):
            entradas += ["-i", str(arquivo)]
            ms = int(round(em * 1000))
            filtros.append(
                f"[{len(clipes) + j}:a]aresample={TAXA},"
                f"volume={ganho:.6f},adelay={ms}:all=1[ae{j}]")
            rotulos.append(f"[ae{j}]")
        filtros.append(
            "".join(rotulos) +
            f"amix=inputs={len(rotulos)}:normalize=0,apad,atrim=0:{duracao_filme:.3f},"
            f"loudnorm=I={LOUDNESS_LUFS}:TP={TRUE_PEAK_DBTP}:LRA=7[aout]")
        cmd = (["ffmpeg", "-y", "-nostdin", "-fflags", "+bitexact"] + entradas +
               ["-filter_complex", ";".join(filtros), "-map", "[aout]",
                "-ac", str(CANAIS), "-ar", str(TAXA),
                "-c:a", "libopus", "-b:a", BITRATE,
                "-fflags", "+bitexact", str(saida)])
        # bitexact duas vezes (entrada e saida): o muxer Ogg sorteia o serial
        # da pagina, e sem isso dois dublar do MESMO audio davam bytes
        # diferentes -- o container mentia sobre o conteudo. Medido, nao
        # adivinhado: decodificados, os PCM ja eram identicos.
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"  ERRO: ffmpeg nao mixou:\n{r.stderr[-800:]}")


# ---- o comando ------------------------------------------------------------
def _earcons_do_filme(d: dict) -> list:
    """[(plano, em_abs, tipo)] — os momentos do Dado que JA existem como dado.

    Nada aqui inventa evento: pose 'aceso'/'retraido' e evento 'citar' vem
    das acoes do filme; o aceso VISUAL (para.op indo a 1, o dado acendendo)
    tambem e dado. O Dado continua mudo — earcon e carimbo, nao voz.
    """
    agenda, cursor = [], 0.0
    for P in d["planos"]:
        for a in P.get("acoes") or []:
            if a.get("alvo") != "dado":
                continue
            if a.get("pose") in ("aceso", "retraido"):
                agenda.append((P["id"], round(cursor + a["em"], 3), a["pose"]))
            elif a.get("evento") == "citar":
                agenda.append((P["id"], round(cursor + a["em"], 3), "citar"))
            elif (a.get("para") or {}).get("op") == 1:
                agenda.append((P["id"], round(cursor + a["em"], 3), "aceso"))
        cursor += P["dur"]
    return agenda


def dublar(fid: str) -> int:
    d = dados_do_filme(fid)
    base = _voz.materializar()
    a = _voz.ancora()
    onnx = base / f"{a['nome']}.onnx"

    try:
        from piper import PiperVoice
    except ImportError:
        raise ErroDeDados(
            "piper-tts nao esta instalado. O dublar e offline e local:\n"
            "  pip install piper-tts\n"
            "  (no CI ele nao roda: o portao de sonorizacao cai em INDECISO, "
            "nunca quebra o build)") from None
    voice = PiperVoice.load(onnx)

    elenco = d.get("elenco", {})
    # O timbre materializa as portadoras SO se algum rig do filme declara
    # timbre -- filme sem timbre nao toca na rede nem no lock de amostras.
    portadoras_necessarias = set()
    for P in d["planos"]:
        for L in P.get("legendas") or []:
            _t, _r, _rot, tim = quem_fala(P, L, elenco)
            if tim:
                portadoras_necessarias.add(tim["portadora"])
    earcons_agenda = _earcons_do_filme(d)
    necessarias = set(portadoras_necessarias)
    if earcons_agenda:
        necessarias |= {f"dado-{t}" for _, _, t in earcons_agenda}
    wavs_amostras = {}
    if necessarias:
        from . import amostras as _am
        wavs_amostras = _am.materializar(ids=necessarias)

    arquivos_earcon = {}
    if earcons_agenda:
        tipos = {tipo for _, _, tipo in earcons_agenda}
        arquivos_earcon = {t: wavs_amostras[f"dado-{t}"] for t in tipos
                           if f"dado-{t}" in wavs_amostras}
        faltam = tipos - set(arquivos_earcon)
        if faltam:
            raise ErroDeDados(
                f"o filme tem momentos do Dado ({', '.join(sorted(faltam))}) sem "
                f"earcon ancorado em amostras.lock -- o som do Dado e da suíte, "
                f"e mora no lock.")

    clipes, manifestos, excessos = [], [], []
    cursor = 0.0
    for P in d["planos"]:
        for L in P.get("legendas") or []:
            texto, ritmo, rotulo, tim = quem_fala(P, L, elenco)
            pcm, dur = sintetizar(voice, texto, ritmo)
            if tim:
                from . import timbre as _tim
                pcm = _tim.aplicar(pcm, wavs_amostras[tim["portadora"]],
                                   mistura=float(tim["mistura"]),
                                   bandas=int(tim.get("bandas", 16) or 16))
            em, ate = cursor + L["em"], cursor + L["ate"]
            orcamento = (L["ate"] - L["em"]) + TOLERANCIA_S
            if dur > orcamento:
                excessos.append(
                    f"{P['id']}: legenda {L['em']}-{L['ate']} ({rotulo}) falou "
                    f"{dur:.2f}s em {(L['ate'] - L['em']):.2f}s de tela -- "
                    f"excedeu {dur - (L['ate'] - L['em']):.2f}s. Encurte a "
                    f"legenda (teto de 15 caracteres/segundo): {L['txt']!r}")
                continue
            clipes.append((pcm, em, dur))
            mani = {
                "plano": P["id"], "em": round(em, 3), "ate": round(ate, 3),
                "dur": round(dur, 3), "voz": rotulo,
                "texto_sha256": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
            }
            if tim:
                from . import amostras as _am
                mani["timbre"] = {
                    "portadora": tim["portadora"],
                    "mistura": float(tim["mistura"]),
                    "bandas": int(tim.get("bandas", 16) or 16),
                    "portadora_sha256": _am.ancora()[tim["portadora"]]["sha256"],
                }
            manifestos.append(mani)
        cursor += P["dur"]

    if excessos:
        print("  REPROVADO — clipe estoura o tempo da legenda e audio nao se "
              "estica:", file=sys.stderr)
        for e in excessos:
            print(f"  ERRO: {e}", file=sys.stderr)
        print("\n  Time-stretch e proibido pela CP-004: o texto cede, nunca o "
              "tempo. Edite a legenda (dado e prosa) e rode dublar de novo.",
              file=sys.stderr)
        return 1

    dir_audio = FILMES / fid / "audio"
    dir_audio.mkdir(parents=True, exist_ok=True)
    opus = dir_audio / f"{fid}.opus"
    earcons_mix = [(arquivos_earcon[t], em) for _, em, t in earcons_agenda
                   if t in arquivos_earcon]
    mixar(clipes, d["duracao"], opus, earcons=earcons_mix)

    manifesto = {
        "filme": fid,
        "gerado_por": "python3 -m estudio_suite dublar",
        "modelo": {"nome": a["nome"],
                   "sha256_onnx": a["arquivos"][f"{a['nome']}.onnx"],
                   "sha256_json": a["arquivos"][f"{a['nome']}.onnx.json"]},
        "mix": {"arquivo": opus.name, "taxa_hz": TAXA, "canais": CANAIS,
                "loudness_alvo_lufs": LOUDNESS_LUFS,
                "true_peak_alvo_dbtp": TRUE_PEAK_DBTP},
        "earcons": [{"plano": p, "em": em, "tipo": t,
                     "arquivo": f"dado-{t}.wav", "ganho_db": GANHO_EARCON_DB}
                    for p, em, t in earcons_agenda],
        "clipes": manifestos,
    }
    (dir_audio / "audio.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")

    print(f"  {fid}: {len(clipes)} clipe(s) -> {opus.relative_to(RAIZ)}")
    por_voz = {}
    for c in manifestos:
        por_voz[c["voz"]] = por_voz.get(c["voz"], 0) + 1
    print("  vozes: " + ", ".join(f"{v} ({n})" for v, n in sorted(por_voz.items())))
    timbrados = sum(1 for c in manifestos if c.get("timbre"))
    if timbrados:
        print(f"  timbre: {timbrados} clipe(s) com portadora animal (vocoder de canais)")
    if earcons_agenda:
        print(f"  earcons do Dado: {len(earcons_agenda)} momento(s) a {GANHO_EARCON_DB} dB")
    print(f"  loudness ancorado em {LOUDNESS_LUFS} LUFS / true peak "
          f"{TRUE_PEAK_DBTP} dBTP; manifesto em audio/audio.json")
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("uso: dublar <id-do-filme>", file=sys.stderr)
        return 64
    try:
        return dublar(argv[0])
    except ErroDeDados as e:
        print(f"  ERRO: {e}", file=sys.stderr)
        return 2
