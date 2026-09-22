#!/usr/bin/env python3
"""O fiscal de amostras e a ancora, provados nos dois sentidos (CP-005).

Som de terceiro entra na suite por UMA porta: o amostras.lock, com licenca
declarada e sha256. Aqui se prova que a porta abre para a chave certa (lock
real le, coleta reproduz, rig declarado e lido) e NAO abre para errada
(licenca fora da politica, entrada pela metade, bytes divergentes, portadora
pirata em uso).

A coleta dos casos usa URLs file:// com fixture local: o CI nao tem rede
para o Freesound e nao precisa dela -- o que o CI prova e a LOGICA da
ancora, e a coleta real e evidencia de maquina local, registrada no PR.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import amostras                          # noqa: E402
from estudio_suite import dublar                           # noqa: E402
from estudio_suite import pipeline                          # noqa: E402
from estudio_suite.comum import FILMES                      # noqa: E402

ok, bad = [], []
FANTASMA = "teste-amostras-fantasma"


def chk(c, msg):
    (ok if c else bad).append(msg)


def _lock_fixture(caminho: Path, url: str, sha: str, licenca='"Creative Commons 0"',
                  atribuicao="Autor Teste — Som de Teste"):
    caminho.write_text(
        "schema: estudio-suite/amostras-lock@1\n\namostras:\n"
        f"  teste-portadora:\n"
        f"    origem: https://exemplo.teste/som/1/\n"
        f"    url: {url}\n"
        f"    licenca: {licenca}\n"
        f"    sha256: {sha}\n"
        f"    atribuicao: \"{atribuicao}\"\n"
        f"    papel: \"portadora de teste\"\n", encoding="utf-8")


def _filme_fantasma():
    d = FILMES / FANTASMA
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    filme = {
        "id": FANTASMA, "titulo": "Fantasma das amostras", "duracao": 8,
        "elenco": {"ana": {"rig": "raposa", "papel": "Titular"}},
        "planos": [{
            "id": "p01", "titulo": "Teste", "dur": 8, "guardiao": "coruja",
            "cenario": "vazio", "poster": 3, "arts": [],
            "entra": {"ana": {"x": 300, "y": 620}},
            "legendas": [{"em": 0.3, "ate": 5.5, "txt": "Uma legenda que fala."}],
        }],
    }
    (d / f"{FANTASMA}.filme.js").write_text(
        "window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};"
        "window.ESTUDIO_FILMES[\"" + FANTASMA + "\"]=\n" +
        json.dumps(filme, ensure_ascii=False, indent=1) + "\n;\n", encoding="utf-8")
    return d


def main():
    # --- o lock real le, e a licenca de cada portadora consta -----------
    ancoradas = amostras.ancora()
    chk(len(ancoradas) == 4,
        f"o amostras.lock real ancora 4 portadoras ({sorted(ancoradas)})")
    for aid, a in sorted(ancoradas.items()):
        chk(a["licenca"] in amostras.LICENCAS_LIVRES,
            f"{aid}: licenca '{a['licenca']}' dentro da politica da CP-005")
        chk(len(a["sha256"]) == 64 and all(c in "0123456789abcdef" for c in a["sha256"]),
            f"{aid}: sha256 bem formado")
        chk(bool(a["atribuicao"]) and bool(a["origem"]),
            f"{aid}: atribuicao e origem declaradas")

    # --- regressao da CP-004: o ritmo DECLARADO agora e LIDO ------------
    v = dublar.voz_do_rig("coruja")
    chk(v.get("ritmo") == -0.10, f"coruja: ritmo -0.10 lido do rig ({v.get('ritmo')})")
    chk(dublar.voz_do_rig("elefante").get("ritmo") == -0.15, "elefante: ritmo -0.15 lido")
    chk(dublar.voz_do_rig("tartaruga").get("ritmo") == -0.20, "tartaruga: ritmo -0.20 lido")
    v = dublar.voz_do_rig("raposa")
    chk(v.get("ritmo") == 0.05, f"raposa: ritmo 0.05 do TOPO preservado ({v.get('ritmo')})")
    chk(v.get("registros", {}).get("titular", {}).get("ritmo") == 0.05
        and v["registros"]["encarregado"]["ritmo"] == 0.0,
        "raposa: registros por papel lidos (titular 0.05, encarregado 0.0)")

    # --- o sub-bloco timbre e lido como dado (ainda sem aplicacao) ------
    chk("timbre" not in dublar.voz_do_rig("coruja"),
        "nenhum rig real declara timbre ainda — Sprint 6 nao aplica som")

    # --- ancoras quebradas falham com mensagem clara --------------------
    tmp = Path(tempfile.mkdtemp())
    fonte = tmp / "fonte.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=0.5",
                    "-ar", "22050", "-ac", "1", str(fonte)], check=True)
    sha_fonte = hashlib.sha256(fonte.read_bytes()).hexdigest()
    _lock_fixture(tmp / "lock.yaml", fonte.as_uri(), sha_fonte)

    orig_lock, orig_dest = amostras.LOCK, amostras.DESTINO
    amostras.LOCK, amostras.DESTINO = tmp / "lock.yaml", tmp / "ws"
    try:
        # licenca fora da politica: a porta nao abre
        _lock_fixture(tmp / "lock_nc.yaml", fonte.as_uri(), sha_fonte,
                      licenca='"Attribution-NonCommercial"')
        amostras.LOCK = tmp / "lock_nc.yaml"
        try:
            amostras.ancora()
            chk(False, "licenca NC recusada pela ancora")
        except Exception as e:
            chk("CP-005" in str(e) and "NC" in str(e),
                f"licenca NC recusada com a politica nomeada ({str(e)[:60]}...)")

        # entrada pela metade: melhor falhar alto que ancorar pela metade
        (tmp / "lock_meio.yaml").write_text(
            "schema: estudio-suite/amostras-lock@1\n\namostras:\n"
            f"  quebrada:\n    origem: https://x/\n    url: https://x/y.mp3\n"
            f"    licenca: \"Creative Commons 0\"\n"
            f"    sha256: {sha_fonte}\n", encoding="utf-8")
        amostras.LOCK = tmp / "lock_meio.yaml"
        try:
            amostras.ancora()
            chk(False, "entrada sem atribuicao recusada")
        except Exception as e:
            chk("atribuicao" in str(e), "entrada pela metade recusada nomeando o campo")

        # coleta reproduzivel: baixa (file://), confere sha, deriva o wav
        _lock_fixture(tmp / "lock.yaml", fonte.as_uri(), sha_fonte)
        amostras.LOCK = tmp / "lock.yaml"
        wavs = amostras.materializar()
        wav = wavs["teste-portadora"]
        chk(wav.exists(), "coleta materializa o wav da portadora")
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=sample_rate,channels,codec_name",
             "-of", "csv=p=0", str(wav)], capture_output=True, text=True)
        chk(probe.stdout.strip() == "pcm_s16le,48000,1",
            f"wav derivado em 48 kHz mono pcm16 ({probe.stdout.strip()})")
        sha1 = hashlib.sha256(wav.read_bytes()).hexdigest()
        wavs = amostras.materializar()  # segunda execucao: nada refaz, mesma derivacao
        chk(hashlib.sha256(wavs["teste-portadora"].read_bytes()).hexdigest() == sha1,
            "coleta e derivacao reproduziveis (mesmo sha256 em duas execucoes)")

        # bytes divergentes: a ancora NAO abre. O re-download busca da
        # fonte TAMBEM adulterada (file:// aponta pro mesmo arquivo), e o
        # cheque final do sha pega a divergencia.
        fonte.write_bytes(fonte.read_bytes() + b"x")
        shutil.rmtree(tmp / "ws", ignore_errors=True)   # forca novo download
        try:
            amostras.materializar()
            chk(False, "sha divergente recusado")
        except Exception as e:
            chk("NAO e a ancorada" in str(e),
                f"sha divergente falha com mensagem clara ({str(e)[:50]}...)")

        # --- fiscal: o filme real (sem timbre) nao e fiscalizado --------
        amostras.LOCK = orig_lock
        _filme_fantasma()
        for fid in ("jornada-dado", "legitimo-interesse", FANTASMA):
            a = pipeline.fiscal_amostras(fid)
            chk(a == [], f"{fid}: sem timbre declarado, fiscal cala ({a})")

        # --- fiscal: portadora pirata em uso e VERMELHO ------------------
        # (o fiscal e chamado direto, como o de redublagem em test_dublar:
        # o portao storyboard o invoca depois do validador de roteiro, que
        # exige a lei ancorada -- no CI com LEI_TOKEN o wiring inteiro roda)
        original_voz = dublar.voz_do_rig
        dublar.voz_do_rig = lambda rig: (
            {"timbre": {"portadora": "som-de-terceiro-sem-origem", "mistura": 0.35}}
            if rig == "coruja" else original_voz(rig))
        try:
            a = pipeline.fiscal_amostras(FANTASMA)
            chk(len(a) == 1 and "NAO consta em amostras.lock" in a[0]
                and "coruja" in a[0],
                f"portadora pirata em uso e apontada ({a})")
            # rig SEM timbre no mesmo filme: nao gera achado falso
            # portadora ancorada: fiscal cala
            dublar.voz_do_rig = lambda rig: (
                {"timbre": {"portadora": "coruja-pio", "mistura": 0.35}}
                if rig == "coruja" else original_voz(rig))
            chk(pipeline.fiscal_amostras(FANTASMA) == [],
                "portadora ancorada no lock: fiscal cala")
        finally:
            dublar.voz_do_rig = original_voz
    finally:
        amostras.LOCK, amostras.DESTINO = orig_lock, orig_dest
        shutil.rmtree(FILMES / FANTASMA, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"  {len(ok)} verificacoes da ancora e do fiscal de amostras.")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  som de terceiro so entra pela porta do lock — e a porta confere.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
