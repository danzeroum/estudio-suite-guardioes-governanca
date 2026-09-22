"""As amostras de timbre sao ancoradas por SHA, materializadas e conferidas.

Mesma arquitetura do voz.lock, pelo mesmo motivo: dublar com outra portadora
produziria OUTRO timbre do que o revisado -- silenciosamente. O amostras.lock
declara origem, URL, licenca, sha256 e atribuicao de cada portadora; os
arquivos moram em workspace/amostras/, que o .gitignore recusa; e a
conferencia roda SEMPRE, inclusive quando nada foi baixado.

Diferenca de proposito em relacao a voz: o modelo Piper e um bem publico
estavel, mas a portadora e obra de TERCEIROS com licenca. Por isso o lock
tambem declara a LICENCA e a ancora aceita so CC0/CC-BY (CP-005): som
nao-livre na suite e divida que aparece quando o filme sai do repositorio.

A URL ancorada e o preview publico do CDN do Freesound, que dispensa chave
de API -- a API v2 exige token (401 sem FREESOUND_API_KEY), e nenhuma chave
foi fornecida a suite. A coleta fica reproduzivel em qualquer maquina: baixa
da URL do lock, confere o sha256 do preview, e normaliza para 48 kHz mono
.wav com ffmpeg (-fflags +bitexact) -- mudanca de FORMATO, nunca de duracao.
"""
import hashlib
import re
import subprocess
import urllib.request
from pathlib import Path

from .comum import ErroDeDados, RAIZ, WORKSPACE

LOCK = RAIZ / "amostras.lock"
DESTINO = WORKSPACE / "amostras"
TAXA, CANAIS = 48000, 1

# Politica de licencas da CP-005: so cabe na suite o que e livre para
# comercial E para derivadas -- o vocoder IMPOE envelope a portadora, o que
# ja e obra derivada. NC ou ND nao cabem, e BBC RemArc alem de nao-ser-livre
# veda uso em sintese. A lista e fechada de proposito.
LICENCAS_LIVRES = {"Creative Commons 0", "Creative Commons Attribution"}

_CAMPOS = ("origem", "url", "licenca", "sha256", "atribuicao", "papel")


def ancora() -> dict:
    """Le amostras.lock sem dependencia de YAML: formato fixo e raso.

    Cada entrada declara os seis campos; licenca ausente ou fora da politica
    da CP-005 falha aqui -- "a licenca nao constar" e reprovacao de ancora,
    nao warning. O mesmo para sha que nao casa o formato hex de 64.
    """
    if not LOCK.exists():
        raise ErroDeDados(
            "amostras.lock nao existe. Sem ancora nao ha timbre: cada maquina "
            "baixaria a amostra que tivesse a mao, e o timbre commitado nao "
            "seria reproduzivel -- nem licenciavel. Crie o lock ANTES de "
            "dublar com timbre (CP-005).")
    txt = LOCK.read_text(encoding="utf-8")
    amostras = {}
    for m in re.finditer(r"^  ([\w-]+):\n((?:^    \w+: .*\n?)+)", txt, re.M):
        aid, corpo = m.group(1), m.group(2)
        pares = dict(re.findall(r"^    (\w+): (.*)$", corpo, re.M))
        pares = {k: v.strip('"') for k, v in pares.items()}
        faltam = [c for c in _CAMPOS if not pares.get(c)]
        if faltam:
            raise ErroDeDados(
                f"amostras.lock: '{aid}' nao declara {', '.join(faltam)} -- "
                f"entrada pela metade e pior que entrada nenhuma.")
        if pares["licenca"] not in LICENCAS_LIVRES:
            raise ErroDeDados(
                f"amostras.lock: '{aid}' declara licenca '{pares['licenca']}', "
                f"fora da politica da CP-005 (somente {' ou '.join(sorted(LICENCAS_LIVRES))}). "
                f"Som NC/ND/RemArc entra na suite por change-proposal que "
                f"revogue a politica -- nunca por edicao silenciosa do lock.")
        if not re.fullmatch(r"[0-9a-f]{64}", pares["sha256"]):
            raise ErroDeDados(
                f"amostras.lock: '{aid}' tem sha256 malformado -- ancora sem "
                f"hash nao ancora nada.")
        amostras[aid] = pares
    if not amostras:
        raise ErroDeDados("amostras.lock nao lista nenhuma amostra.")
    return amostras


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _baixar(url: str, alvo: Path, atribuicao: str) -> None:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "estudio-suite/CP-005 (coleta ancorada)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            dados = r.read()
    except Exception as e:
        raise ErroDeDados(
            f"nao consegui baixar a portadora de {url}: {e}\n"
            f"  Baixe a mao, deixe o arquivo em {alvo}, e rode de novo: o lock "
            f"confere o sha256 antes de usar.") from None
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_bytes(dados)
    _ = atribuicao  # CC0 nao exige, mas o lock declara; CC-BY cobra nos CREDITOS


def _normalizar(mp3: Path, wav: Path) -> None:
    """Preview .mp3 -> .wav 48 kHz mono. Mudanca de FORMATO, nunca de duracao."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-v", "error", "-fflags", "+bitexact",
         "-i", str(mp3), "-ar", str(TAXA), "-ac", str(CANAIS),
         "-c:a", "pcm_s16le", "-fflags", "+bitexact", str(wav)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise ErroDeDados(
            f"ffmpeg nao normalizou {mp3.name} para 48 kHz mono: "
            f"{r.stderr[-400:]}")


def materializar(forcar: bool = False) -> dict:
    """Garante workspace/amostras/ com as portadoras ancoradas e conferidas.

    Devolve {id: caminho_do_wav}. O fonte (.mp3 do lock) fica ao lado do
    derivado (.wav): conferir o fonte por sha e barato, e re-derivar o wav e
    local. Divergencia de hash falha com mensagem clara -- dublar com
    portadora divergente produziria um timbre que ninguem declarou.
    """
    ancoradas = ancora()
    DESTINO.mkdir(parents=True, exist_ok=True)
    wavs = {}
    divergem = []
    for aid, a in ancoradas.items():
        mp3, wav = DESTINO / f"{aid}.mp3", DESTINO / f"{aid}.wav"
        if forcar or not mp3.exists() or not wav.exists():
            if not mp3.exists() or _sha256(mp3) != a["sha256"]:
                # fonte local ausente ou divergente: reposiciona pela URL do
                # lock. Se o re-download tambem divergir, o cheque final pega.
                _baixar(a["url"], mp3, a["atribuicao"])
            _normalizar(mp3, wav)
        if _sha256(mp3) != a["sha256"]:
            divergem.append(
                f"{aid}: baixado de '{a['url']}' com sha {_sha256(mp3)[:12]}, "
                f"mas o lock declara {a['sha256'][:12]}")
        wavs[aid] = wav
    if divergem:
        raise ErroDeDados(
            "a amostra baixada NAO e a ancorada em amostras.lock:\n  "
            + "\n  ".join(divergem) +
            "\n  Ou a fonte mudou (avance o lock por change-proposal, com a "
            "licenca re-verificada), ou a URL nao serve mais. Nunca duble por "
            "cima da divergencia.")
    return wavs


def main(argv=None) -> int:
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    ancoradas = ancora()
    print(f"  {len(ancoradas)} portadora(s) ancorada(s) em amostras.lock:")
    for aid, a in sorted(ancoradas.items()):
        print(f"    {aid:<18} {a['licenca']:<26} {a['atribuicao'][:52]}")
    forcar = "--refazer" in argv
    wavs = materializar(forcar=forcar)
    print(f"  materializada(s) e conferida(s) em {DESTINO.relative_to(RAIZ)}/")
    for aid in sorted(wavs):
        print(f"    {aid}.wav  (48 kHz, mono)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
