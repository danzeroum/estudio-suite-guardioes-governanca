#!/usr/bin/env python3
"""A prova por classe do job dublador (CP-012) — roda DENTRO da imagem.

A decisao do dono (24/09/2026) definiu a prova certa POR ETAPA:

  "prova de bytes no PCM mixado; codec por tolerancia decodificada;
   AVX2 por equivalencia de descritores com controle positivo"

O que ela decide, com numeros e no log, para CADA execucao:

  classe avx512 (Intel E AMD com avx512f visivel)  ->  PROVA DE BYTES
  NO PCM MIXADO: o hash f32 do audio.json regenerado contra o do
  commitado (a entrada EXATA do codificador — medido na CP-011, o PCM
  e identico entre Intel e AMD-avx512; e o codificador opus que diverge
  por familia). O .opus NAO e mais o ponto da prova de bytes: e
  DECODIFICADO e comparado com o decodificado do HEAD sob o TETO do
  lock (maximo observado em AMD-avx512 + margem, abaixo de -60 dBFS).
  O log diz "PCM identico; codec dentro do teto X". PCM divergente na
  classe avx512 e VERMELHO nomeado — a frota medida entrega igual.

  classe avx2  ->  EQUIVALENCIA POR DESCRITORES, por fala, no RUNNER
  (ci/equivalencia_descritores.py, com a audio-suite): o PCM diverge
  no cru (30/30 falas, CP-011) e o null test nao e a pergunta certa —
  a nulidade nao e audibilidade. Esta prova (na imagem) publica o
  estado do PCM ("PCM diferente (classe avx2)") e as DURACOES POR FALA
  do manifesto, e entrega os WAVs decodificados para o passo do runner
  medir loudness, F0 mediana (pitch_f0) e centroide contra os tetos do
  lock — com CONTROLE POSITIVO provando que os tetos discriminam.

  CONTROLE POSITIVO DO TETO DO CODEC (classe avx512): ruido injetado
  6 dB acima do teto no .opus regenerado (decodifica, injeta,
  re-codifica com os mesmos parametros, decodifica) tem de REPROVAR
  citando o numero. Teto que aceita a frota e nao pega o ruido e
  TETO_NAO_DISCRIMINA — parada nomeada, nunca verde.

  LOCK INCOMPLETO: sem o teto da sua classe (tolerancia.residuo_max_dbfs
  para a avx512; tolerancia.descritores_* para a avx2), o job RECUSA
  (saida 2, nomeando) — nunca verde por omissao.

Os DOIS pontos de residuo sao sempre medidos e publicados (diagnostico
herdado da CP-011): mix pre-opus regenerado x commitado decodificado, e
regenerado decodificado x commitado decodificado — o teto se aplica ao
segundo (os dois lados passaram pelo MESMO codec; o que sobra e
divergencia, nao ruido de codec).

Verificacao separada de validacao (Andre Borges): o veredito carrega
maquina (via job), classe, prova aplicada e numeros — as duas provas
nunca se confundem no log.

Saidas: 0 veredito verde · 1 veredito vermelho (com causa e numeros —
inclui TETO_NAO_DISCRIMINA) · 2 nao consegui medir (nomeado — decode
falhou, lock ilegivel, audio.json sem o hash do PCM).
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import voz                        # noqa: E402
from estudio_suite.comum import FILMES, filmes_com_audio  # noqa: E402

# os mesmos parametros do mixar (dublar.py): o re-encodar do controle do
# teto tem de usar o MESMO codec da trilha de verdade, senao o controle
# mede outra coisa.
TAXA, CANAIS, BITRATE = 48000, 1, "40k"

# as chaves do lock que a classe avx2 exige (a mesma lista que
# ci/equivalencia_descritores.py julga — uma so fonte: o lock)
CHAVES_DESCRITORES = ("descritores_duracao_ms_max",
                      "descritores_loudness_lu_max",
                      "descritores_f0_hz_max",
                      "descritores_centroide_hz_max")

# semente fixa do ruido do controle: o controle e deterministico como
# toda a cadeia — rodar duas vezes devolve o mesmo numero
SEMENTE_CONTROLE = 20260925


# ---- o residuo de nulidade (funcao pura, testada) --------------------------
def residuo_dbfs(pcm_a, pcm_b) -> float:
    """RMS da diferenca entre dois PCM int16, em dBFS (plena = 32768).

    PCM identicos -> -inf dBFS (e passa em qualquer teto: -inf <= teto).
    O residuo de nulidade e a pergunta "quanto SOBRA de diferenca quando
    a hipotese e que os dois sao o MESMO som": em dBFS, para que o teto
    diga se o que sobra esta abaixo do que um ouvido humano notaria.
    """
    a = np.asarray(pcm_a, dtype=np.int16)
    b = np.asarray(pcm_b, dtype=np.int16)
    n = min(len(a), len(b))
    r = a[:n].astype(np.float64) - b[:n].astype(np.float64)
    if len(r) == 0:
        return float("-inf")
    rms = float(np.sqrt(np.mean(r * r)))
    if rms == 0.0:
        return float("-inf")
    return 20.0 * math.log10(rms / 32768.0)


def fmt_dbfs(v: float) -> str:
    return "-inf" if v == float("-inf") else f"{v:.1f}"


def veredito_residuo(residuo: float, teto: float) -> tuple:
    """(ok, frase) — a frase sempre carrega o NUMERO, verde ou vermelho."""
    ok = residuo <= teto
    frase = (f"residuo {fmt_dbfs(residuo)} dBFS x teto {teto:g} dBFS "
             f"[{'OK' if ok else 'ACIMA DO TETO'}]")
    return ok, frase


# ---- o ruido do controle positivo (funcao pura, testada) -------------------
def injetar_ruido(pcm, nivel_dbfs: float, semente: int = SEMENTE_CONTROLE):
    """PCM int16 + ruido gaussiano branco de RMS nivel_dbfs (dBFS).

    Deterministico por semente: o controle positivo e reprodutivel como
    tudo nesta cadeia — duas execucoes devolvem o MESMO numero, e o
    numero do controle pode ser conferido por quem le o artefato.
    """
    a = np.asarray(pcm, dtype=np.int16)
    sigma = (10.0 ** (nivel_dbfs / 20.0)) * 32768.0
    rng = np.random.default_rng(semente)
    ruido = rng.normal(0.0, sigma, size=len(a))
    corrompido = np.rint(a.astype(np.float64) + ruido)
    return np.clip(corrompido, -32768, 32767).astype(np.int16)


# ---- leitura de PCM --------------------------------------------------------
def _ler_pcm_wav(caminho: Path) -> np.ndarray:
    with wave.open(str(caminho), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise SystemExit(f"ERRO: {caminho}: esperado mono pcm16")
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def _decodificar(opus: Path, saida: Path) -> Path:
    """opus -> wav pcm_s16le: mudanca de FORMATO, mesma duracao e taxa."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-v", "error", "-fflags", "+bitexact",
         "-i", str(opus), "-c:a", "pcm_s16le", "-f", "wav", str(saida)],
        capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise SystemExit(f"ERRO: nao decodifiquei {opus}:\n{r.stderr[-400:]}")
    return saida


# ---- duracoes por fala -----------------------------------------------------
_CHAVES_DE_FALA = ("plano", "em", "ate", "dur", "voz", "texto_sha256")


def comparar_duracoes(commitado: list, regenerado: list) -> list:
    """Divergencias de duracao POR FALA — a lista vazia e o verde.

    Compara as chaves que assinam cada fala no manifesto: plano, em, ate,
    dur (arredondado a 1 ms na gravacao), voz e o hash do texto. A duracao
    e o contrato da tolerancia entre classes: os BYTES divergem (kernel
    SIMD diferente), a FALA nao pode (a mesma legenda, o mesmo tempo de
    tela).
    """
    divergencias = []
    if len(commitado) != len(regenerado):
        divergencias.append(
            f"{len(commitado)} fala(s) no commitado x {len(regenerado)} no "
            f"regenerado — a dublagem nao cobre as mesmas falas")
    por_chave = {(c.get("plano"), c.get("em")): c for c in commitado}
    for c in regenerado:
        ref = por_chave.get((c.get("plano"), c.get("em")))
        if ref is None:
            divergencias.append(
                f"plano {c.get('plano')} em {c.get('em')}: fala sem "
                f"correspondente no commitado")
            continue
        for k in _CHAVES_DE_FALA:
            if ref.get(k) != c.get(k):
                divergencias.append(
                    f"plano {c.get('plano')} em {c.get('em')} ({c.get('voz')}): "
                    f"{k} commitado {ref.get(k)} x regenerado {c.get(k)}")
    return divergencias


# ---- o hash do PCM mixado (CP-012: o contrato) -----------------------------
def comparar_hash_pcm(mani_com: dict, mani_reg: dict) -> tuple:
    """(hash_com, hash_reg, sem_contrato, diverge) — o contrato do PCM (CP-012).

    O audio.json registra mix.pcm_f32_sha256 da MESMA dublagem que
    produziu o .opus. Falta em qualquer lado: SEM CONTRATO — divida
    apontada pelo fiscal de redublagem; sem canônico nao ha prova de
    bytes (recusa nomeada em toda classe). DIVERGE: reprova na classe
    avx512 (a frota medida entrega o PCM igual); na avx2 e o ESTADO
    esperado — registrado, publicado, e a equivalencia segue por
    descritores (a decisao do dono separa verificacao de validacao).
    """
    sem_contrato = []
    h_com = (mani_com.get("mix") or {}).get("pcm_f32_sha256")
    h_reg = (mani_reg.get("mix") or {}).get("pcm_f32_sha256")
    if not h_com:
        sem_contrato.append("audio.json commitado sem mix.pcm_f32_sha256 — "
                            "divida apontada pelo fiscal de redublagem "
                            "(dublagem anterior a CP-012); sem canônico a "
                            "prova de bytes do PCM nao existe")
    if not h_reg:
        sem_contrato.append("audio.json regenerado sem mix.pcm_f32_sha256 — "
                            "o dublar que rodou nao gravou o contrato do PCM "
                            "(versao antiga na imagem?)")
    diverge = bool(h_com and h_reg and h_com != h_reg)
    return h_com, h_reg, sem_contrato, diverge


def _conferir_etapas(mani_reg: dict, fid: str) -> list:
    """A cross-check do instrumento: o audio.json e o etapas.json da MESMA
    dublagem tem de carregar o MESMO hash do mix f32 — divergencia aqui e
    defeito de instrumento (o hash gravado nao e o do arquivo medido), nao
    de audio. O etapas.json mora em workspace/voz-etapas (diagnostico da
    CP-011); o contrato mora no audio.json (CP-012)."""
    achados = []
    etapas_p = RAIZ / "workspace" / "voz-etapas" / f"{fid}.etapas.json"
    if not etapas_p.exists():
        return achados
    try:
        et = json.loads(etapas_p.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"etapas.json ilegivel ({e}) — instrumento de diagnostico "
                f"indisponivel, a prova segue pelo contrato do audio.json"]
    h_et = et.get("mix_pcm_f32")
    h_reg = (mani_reg.get("mix") or {}).get("pcm_f32_sha256")
    if h_et and h_reg and h_et != h_reg:
        achados.append("o audio.json e o etapas.json da mesma dublagem "
                       "discordam sobre o hash do mix f32 — instrumento "
                       "inconsistente, nada se prova assim")
    return achados


# ---- o controle positivo do teto do codec ----------------------------------
def nivel_de_controle(teto: float) -> float:
    """O nivel do ruido do controle: 6 dB acima do teto (CP-012)."""
    return teto + 6.0


def controlar_teto_do_codec(pcm_reg, pcm_com, teto: float) -> tuple:
    """(reprovou, residuo, frase) — o controle positivo do teto do codec.

    CENARIO (o do plano): "Mix PCM identico + .opus com ruido injetado
    6 dB acima do teto de codec -> reprova, citando o numero". O hash
    do PCM mixado segue BATENDO (o ruido mora na ENTREGA do .opus, nao
    na sintese); o ruido de RMS (teto + 6 dB) e injetado no PCM
    DECODIFICADO da trilha regenerada — exatamente o ponto onde o teto
    julga (decoded x decoded) — e o residuo contra o commitado
    decodificado tem de ficar ACIMA do teto, citando o numero. NAO se
    re-codifica de proposito: uma re-codificacao carrega o ruido de
    quantizacao do PROPRIO codec (-36 dBFS, medido), que engoliria o
    ruido do controle e o deixaria vermelho PELA RAZAO ERRADA — controle
    que sempre reprova nao prova nada. O ruido tem semente fixa: o
    numero do controle e conferivel no artefato. Teto que deixa passar
    o ruido 6 dB acima dele e TETO_NAO_DISCRIMINA — parada nomeada.
    """
    nivel = nivel_de_controle(teto)
    corrompido = injetar_ruido(pcm_reg, nivel)
    residuo = residuo_dbfs(corrompido, pcm_com)
    reprovou = residuo > teto
    frase = (f"controle do teto do codec: ruido injetado a {nivel:g} dBFS "
             f"(6 dB acima do teto {teto:g}) na ENTREGA decodificada com o "
             f"hash do PCM batendo -> residuo {fmt_dbfs(residuo)} dBFS "
             f"[{'REPROVOU — o teto enxerga' if reprovou else 'NAO REPROVOU'}]")
    return reprovou, residuo, frase


# ---- a prova ----------------------------------------------------------------
def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _teto_do_codec(tol: dict):
    """O teto do codec (tolerancia.residuo_max_dbfs) ou None se ausente."""
    if "residuo_max_dbfs" not in tol:
        return None
    try:
        return float(str(tol["residuo_max_dbfs"]).strip())
    except ValueError:
        return None


def _tetos_de_descritores(tol: dict) -> dict:
    """{chave: float} dos tetos de descritores — o que existir (CP-012)."""
    out = {}
    for k in CHAVES_DESCRITORES:
        if k in tol:
            try:
                out[k] = float(str(tol[k]).strip())
            except ValueError:
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--commitado", default="/commitado",
                    help="espelho do audio commitado (raiz do repositorio)")
    ap.add_argument("--saida", default="/prova",
                    help="onde o prova.json e os WAVs decodificados vao")
    args = ap.parse_args()
    commitado = Path(args.commitado)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    a = voz.ancora()
    classe_ancora = str(a["ambiente"].get("classe_simd", "")).strip()
    tol = voz.tolerancia()
    teto = _teto_do_codec(tol)
    tetos_desc = _tetos_de_descritores(tol)
    classe_runner = voz.classe_simd_medida()

    # Qual prova roda — dito no LOG antes de qualquer numero, para o
    # leitor nunca confundir verificacao (bytes no PCM) com validacao
    # (teto do codec / descritores no runner).
    if classe_runner == classe_ancora:
        prova = "bytes-pcm+codec-sob-teto"
    else:
        prova = "descritores-por-fala"
    print("== PROVA POR CLASSE (CP-012: bytes no PCM mixado, codec por "
          "tolerancia decodificada, AVX2 por descritores)")
    print(f"   classe do runner:  {classe_runner} (flags medidas)")
    print(f"   classe da ancora:  {classe_ancora} (voz.lock)")
    print(f"   teto do codec:     "
          + (f"{teto:g} dBFS (voz.lock, base {tol.get('base_dbfs', '?')} + "
             f"margem {tol.get('margem_db', '?')} dB, ponto "
             f"{tol.get('ponto', '?')})" if teto is not None
             else "NAO REGISTRADO — lock INCOMPLETO para a classe avx512"))
    print(f"   tetos descritores: "
          + (f"{len(tetos_desc)}/{len(CHAVES_DESCRITORES)} registrados"
             + (f" ({', '.join(sorted(tetos_desc))})" if tetos_desc else "")
             if tetos_desc else
             " NAO REGISTRADOS — lock INCOMPLETO para a classe avx2 "
             "(fase de medicao: os numeros saem publicados, o veredito "
             "nao fica verde por omissao)"))
    print(f"   PROVA APLICADA:    {prova}")

    filmes = list(filmes_com_audio())
    if not filmes:
        print("   nenhum filme declara audio — nada a provar (a prova por "
              "classe e a prova de QUEM FALA)")
        (saida / "prova.json").write_text(json.dumps(
            {"prova": prova, "classe": {"runner": classe_runner,
                                        "ancora": classe_ancora},
             "filmes": [], "veredito": "sem filmes com audio"}, indent=1) + "\n",
            encoding="utf-8")
        return 0

    # lock incompleto para a classe que roda: RECUSA nomeada (nunca verde
    # por omissao) — mas os numeros desta execucao sao medidos e publicados
    # ANTES da recusa: e deles que o teto um dia nasce (CP-011 ensinou).
    recusa_lock = None
    if classe_runner == classe_ancora and teto is None:
        recusa_lock = ("voz.lock sem tolerancia.residuo_max_dbfs — lock "
                       "INCOMPLETO para a classe avx512 (CP-012): a prova "
                       "de bytes do PCM exige o teto do codec para julgar "
                       "a codificacao; recusa, nunca verde por omissao")
    elif classe_runner != classe_ancora and len(tetos_desc) < len(CHAVES_DESCRITORES):
        faltam = sorted(set(CHAVES_DESCRITORES) - set(tetos_desc))
        recusa_lock = (f"voz.lock sem os tetos de descritores da classe "
                       f"avx2 — lock INCOMPLETO (faltam: {', '.join(faltam)}). "
                       f"As medidas desta execucao sao publicadas no "
                       f"prova.json e no passo de descritores: o teto nasce "
                       f"da medicao da frota (CP-012, fase 2); sem ele a "
                       f"classe avx2 nao fica verde")

    relatorio, vermelho, instrumento = [], [], []
    wavs_para_compare = []
    for fid in filmes:
        print(f"\n== {fid}")
        base_reg = FILMES / fid / "audio"
        base_com = commitado / "filmes" / fid / "audio"
        # (i) bytes do .opus — DIAGNOSTICO desde a CP-012: a decisao do
        # dono moveu a prova de bytes para o PCM; o numero continua
        # publicado (verde ou vermelho, ele diz o estado da frota)
        divergentes = []
        for f in sorted(base_reg.glob("*.opus")):
            espelho = base_com / f.name
            if not espelho.exists():
                divergentes.append(f"{f.name}: sem espelho commitado")
            elif _sha256(f) != _sha256(espelho):
                divergentes.append(f.name)
        n_opus = len(list(base_reg.glob("*.opus")))
        print(f"   bytes .opus: {n_opus - len(divergentes)}/{n_opus} identicos"
              + (f" — DIVERGENTES: {', '.join(divergentes[:6])}"
                 + ("…" if len(divergentes) > 6 else "")
                 if divergentes else " (diagnostico — a prova de bytes "
                                     "mudou de etapa na CP-012)"))

        # (ii) duracoes por fala — do manifesto regenerado contra o commitado
        try:
            mani_com = json.loads((base_com / "audio.json").read_text(encoding="utf-8"))
            mani_reg = json.loads((base_reg / "audio.json").read_text(encoding="utf-8"))
        except FileNotFoundError as e:
            print(f"   ERRO: manifesto ausente ({e}) — nao consegui medir")
            (saida / "prova.json").write_text(json.dumps(
                {"veredito": "NAO MEDIDO", "erro": str(e)}, indent=1) + "\n",
                encoding="utf-8")
            return 2
        div_dur = comparar_duracoes(mani_com.get("clipes", []),
                                    mani_reg.get("clipes", []))
        print(f"   duracoes por fala: "
              + ("identicas" if not div_dur
                 else f"{len(div_dur)} divergencia(s): " + "; ".join(div_dur[:4])))

        # (iii) o CONTRATO do PCM mixado (CP-012) — o hash f32 do audio.json
        h_com, h_reg, sem_contrato, diverge = comparar_hash_pcm(mani_com, mani_reg)
        ach_etapas = _conferir_etapas(mani_reg, fid)
        instrumento += ach_etapas
        pcm_igual = bool(h_com and h_reg and h_com == h_reg)
        if sem_contrato:
            print(f"   PCM mixado: SEM CONTRATO — {'; '.join(sem_contrato)}")
        elif pcm_igual:
            nota = ("bate com o etapas.json" if not ach_etapas
                    else "PONTO: o instrumento discorda (ver abaixo)")
            print("   PCM mixado (f32, a entrada exata do codificador): "
                  f"IDENTICO — {nota}")
        else:
            print("   PCM mixado (f32, a entrada exata do codificador): "
                  f"DIVERGE (commitado {h_com[:16]}… x regenerado "
                  f"{h_reg[:16]}…)")

        # (iv) residuo nos DOIS pontos, sempre medido e publicado
        wav_com = saida / f"{fid}-commitado.wav"
        wav_reg = saida / f"{fid}-regenerado.wav"
        _decodificar(base_com / f"{fid}.opus", wav_com)
        _decodificar(base_reg / f"{fid}.opus", wav_reg)
        pcm_com, pcm_reg = _ler_pcm_wav(wav_com), _ler_pcm_wav(wav_reg)
        res_opus = residuo_dbfs(pcm_com, pcm_reg)
        mix_wav = RAIZ / "workspace" / "voz-etapas" / f"{fid}.mix.wav"
        res_mix = None
        if mix_wav.exists():
            res_mix = residuo_dbfs(_ler_pcm_wav(mix_wav), pcm_com)
        print(f"   residuo opus decodificado x commitado decodificado: "
              f"{fmt_dbfs(res_opus)} dBFS"
              + (f" | mix pre-opus x commitado decodificado: {fmt_dbfs(res_mix)} dBFS"
                 f" (leva o ruido de codec do lado commitado — ponto de "
                 f"diagnostico, nao de teto)" if res_mix is not None else ""))
        if len(pcm_com) != len(pcm_reg):
            print(f"   ATENCAO: {len(pcm_com)} amostras no commitado x "
                  f"{len(pcm_reg)} no regenerado")
        # CP-012: os WAVs sao publicados por NOME no prova.json (o passo de
        # descritores roda NO RUNNER, onde o diretorio da prova e outro —
        # caminho absoluto da gravacao era caminho do CONTAINER e o passo
        # antigo de compare ja arrastava esse defeito latente: nunca rodou
        # porque o teto nunca existiu. Nome + diretorio do passo = sem amarrar
        # o consumidor a casa de quem produziu.
        wavs_para_compare += [wav_com.name, wav_reg.name]

        # o veredito deste filme, pela prova que vale para a classe
        problema = None
        controle = None
        if prova == "bytes-pcm+codec-sob-teto":
            if div_dur:
                problema = f"duracoes por fala divergentes: {'; '.join(div_dur[:3])}"
            elif sem_contrato or ach_etapas:
                problema = "; ".join(sem_contrato + ach_etapas)
            elif not pcm_igual:
                problema = ("o hash do PCM mixado DIVERGE na classe avx512 — "
                            "a frota medida (CP-011, 4 amostras AMD-avx512 + "
                            "6 Intel) entrega o PCM identico; divergencia "
                            "aqui e sintese divergente, nao familia de CPU")
            else:
                ok, frase = veredito_residuo(res_opus, teto)
                print(f"   {frase} [ponto {tol.get('ponto', '?')}]")
                if not ok:
                    problema = (frase + " — a codificacao divergiu acima do "
                                "teto da frota")
                else:
                    # CONTROLE POSITIVO: o ruido 6 dB acima do teto, com o
                    # hash do PCM batendo, tem de REPROVAR citando o numero
                    reprovou, res_c, frase_c = controlar_teto_do_codec(
                        pcm_reg, pcm_com, teto)
                    print(f"   {frase_c}")
                    controle = {"reprovou": reprovou,
                                "residuo_dbfs": (fmt_dbfs(res_c)
                                                 if res_c == float("-inf")
                                                 else round(res_c, 2)),
                                "ruido_dbfs": round(nivel_de_controle(teto), 2)}
                    if not reprovou:
                        problema = ("TETO_NAO_DISCRIMINA — " + frase_c +
                                    ": o teto aceita a frota e aceita o "
                                    "ruido 6 dB acima dele; tolerancia que "
                                    "nao enxerga mudanca real e parada "
                                    "nomeada (CP-012)")
            if problema is None:
                print("   VEREDITO DO FILME: PCM identico; codec dentro do "
                      f"teto {teto:g} dBFS (controle positivo reprovou)")
        else:  # descritores-por-fala (classe avx2)
            if div_dur:
                problema = (f"duracoes por fala divergentes (o contrato de "
                            f"equivalencia comeca por ele): "
                            f"{'; '.join(div_dur[:3])}")
            elif sem_contrato or ach_etapas:
                problema = "; ".join(sem_contrato + ach_etapas)
            else:
                print("   PCM diferente (classe avx2); equivalencia por "
                      "descritores: medida no RUNNER pelo passo "
                      "ci/equivalencia_descritores.py sobre os WAVs "
                      "publicados (loudness, F0 mediana, centroide, "
                      "duracao medida) contra os tetos do lock — o "
                      "veredito desta classe sai LÁ, com os numeros e o "
                      "controle positivo")
        if problema:
            vermelho.append(f"{fid}: {problema}")
            print(f"   VEREDITO DO FILME: VERMELHO — {problema}")
        elif prova == "bytes-pcm+codec-sob-teto":
            print(f"   VEREDITO DO FILME: verde ({prova})")
        else:
            print(f"   VEREDITO DO FILME (na imagem): duracoes ok — "
                  f"aguardando os descritores do runner")

        relatorio.append({
            "filme": fid,
            "bytes_opus": {"identicos": not divergentes,
                           "divergentes": divergentes,
                           "total_opus": n_opus,
                           "nota": "diagnostico desde a CP-012 (a prova de "
                                   "bytes mudou de etapa)"},
            "pcm_mixado": {"hash_commitado": h_com, "hash_regenerado": h_reg,
                           "identico": pcm_igual},
            "duracoes": {"ok": not div_dur, "divergencias": div_dur},
            "residuo_dbfs": {
                "opus_decodificado": (None if res_opus is None
                                      else (fmt_dbfs(res_opus) if res_opus == float("-inf")
                                            else round(res_opus, 2))),
                "mix_pre_opus": (None if res_mix is None
                                 else (fmt_dbfs(res_mix) if res_mix == float("-inf")
                                       else round(res_mix, 2))),
            },
            "controle_codec": controle,
            "amostras": {"commitado": len(pcm_com), "regenerado": len(pcm_reg)},
        })

    veredito = ("verde — " + prova if not vermelho
                else f"VERMELHO — {prova}: " + " | ".join(vermelho))
    doc = {
        "classe": {"runner": classe_runner, "ancora": classe_ancora,
                   "teto_dbfs": teto,
                   "tetos_descritores": {k: tetos_desc[k]
                                         for k in sorted(tetos_desc)}},
        "prova": prova,
        "filmes": relatorio,
        "wavs_para_compare": wavs_para_compare,
        "instrumento": instrumento,
        "veredito": veredito,
    }
    if recusa_lock:
        doc["recusa_lock"] = recusa_lock
    (saida / "prova.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n== VEREDITO: {veredito}")
    if recusa_lock:
        print(f"== RECUSA (lock incompleto): {recusa_lock}")
        return 2
    print("   (a equivalencia por descritores da classe avx2 roda no RUNNER "
          "sobre os WAVs publicados; o veredito final da execucao combina "
          "as duas provas)")
    return 1 if vermelho else 0


if __name__ == "__main__":
    sys.exit(main())
