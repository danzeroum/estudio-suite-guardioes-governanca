"""A voz e ancorada por SHA, materializada efemera, conferida byte a byte.

Mesma arquitetura do lei.lock, pro mesmo motivo: dublar com outro modelo
produziria OUTRO audio do que o revisado -- silenciosamente. O voz.lock
declara modelo e hashes; o modelo mora em workspace/voz/, que o .gitignore
recusa; e a conferencia roda SEMPRE, inclusive quando nada foi baixado.

Diferenca de proposito em relacao a lei: a lei tem dono externo
(guardioes-governanca); a voz e um bem publico (piper-voices, MIT). O que o
lock ancora nao e "de quem e", e "EXATAMENTE qual pesos produziram esta
dublagem" -- o audio commitado e a evidencia, e o lock e o que torna a
evidencia reproduzivel.

CP-007: pesos iguais nao bastam. O byte final de um .opus assinam tambem
o piper, o onnxruntime, o numpy/scipy do motor de timbre, o fonemizador
embutido no wheel e o ffmpeg+libopus do mix -- medido em outra maquina,
as duracoes deslocam ate +0,08 s com o MESMO modelo. O bloco `ambiente:`
do lock ancora essas versoes; conferir_ambiente() as mede e recusa dublar
na divergencia, antes de escrever qualquer arquivo.
"""
import ctypes
import hashlib
import importlib.metadata
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from .comum import ErroDeDados, RAIZ, WORKSPACE

LOCK = RAIZ / "voz.lock"
DESTINO = WORKSPACE / "voz"


def _bloco_raso(txt: str, nome: str) -> dict:
    """Pares 'chave: valor' de um bloco topologico 'nome:' — raso, sem YAML.

    Mesma disciplina do parser dos pesos: o lock e contrato lido por
    regex, porque um parser de YAML aqui seria uma dependencia a mais
    para interpretar um arquivo que ninguem deveria editar a mao. A
    secao comeca na chave de coluna zero e acaba na proxima.
    """
    m = re.search(rf"^{nome}:\s*$", txt, re.M)
    if not m:
        return {}
    resto = txt[m.end():]
    fim = re.search(r"^\S", resto, re.M)
    secao = resto[:fim.start()] if fim else resto
    return dict(re.findall(r"^  ([\w.-]+):\s*(\S+)\s*$", secao, re.M))


def ancora() -> dict:
    """Le voz.lock sem dependencia de YAML: formato fixo e raso, como lei.lock."""
    if not LOCK.exists():
        raise ErroDeDados(
            "voz.lock nao existe. Sem ancora, nao ha dublagem: cada maquina "
            "sintetizaria com o modelo que tivesse a mao, e o audio commitado "
            "nao seria reproduzivel. Crie o lock ANTES de dublar.")
    txt = LOCK.read_text(encoding="utf-8")
    nome = re.search(r"^\s*nome:\s*(\S+)\s*$", txt, re.M)
    origem = re.search(r"^\s*origem:\s*(\S+)\s*$", txt, re.M)
    arquivos = dict(re.findall(r"^  (\S+):\n    sha256:\s*([0-9a-f]{64})", txt, re.M))
    if not (nome and origem):
        raise ErroDeDados("voz.lock sem modelo.nome / modelo.origem legiveis.")
    if not arquivos:
        raise ErroDeDados("voz.lock nao lista nenhum arquivo com sha256.")
    ambiente = _bloco_raso(txt, "ambiente")
    if not ambiente:
        raise ErroDeDados(
            "voz.lock sem o bloco ambiente (CP-007). So os pesos nao "
            "reproduzem um .opus: piper, onnxruntime, numpy/scipy, o "
            "fonemizador do wheel e o ffmpeg/libopus do mix tambem assinam "
            "os bytes -- dublar sem essa ancora e reproduzir de ouvido. "
            "Avancar o lock e change-proposal, como qualquer ancora.")
    return {"nome": nome.group(1), "origem": origem.group(1),
            "arquivos": arquivos, "ambiente": ambiente}


# ---- o ambiente de sintese (CP-007) ----------------------------------------
# A lista e a de tudo que toca os bytes entre a legenda e o .opus. python
# entra como major.minor: patch de CPython nao muda o resultado das
# extensoes C (quem roda os numeros e numpy/scipy), mas a serie sim.
PACOTES = ("piper-tts", "onnxruntime", "numpy", "scipy")


def _versao_pacote(nome: str) -> str:
    try:
        return importlib.metadata.version(nome)
    except importlib.metadata.PackageNotFoundError:
        return "ausente"


def _sha_espeak() -> str:
    """A ancora do fonemizador: sha256 dos dados que o wheel do piper embute.

    O espeak-ng mora DENTRO do wheel (espeak-ng-data + a ponte C) e a
    biblioteca nao expoe numero de versao -- o que da para PROVAR e o
    digest dos dados de fonemizacao. Sem isso, wheel reconstruido ou
    dado trocado fonemizariam diferente com a mesma etiqueta de versao.
    """
    try:
        from piper.phonemize_espeak import ESPEAK_DATA_DIR
    except Exception:
        return "ausente"
    if not ESPEAK_DATA_DIR.is_dir():
        return "ausente"
    h = hashlib.sha256()
    for f in sorted(p for p in ESPEAK_DATA_DIR.rglob("*") if p.is_file()):
        rel = f.relative_to(ESPEAK_DATA_DIR).as_posix().encode()
        dados = f.read_bytes()
        h.update(len(rel).to_bytes(4, "big")); h.update(rel)
        h.update(len(dados).to_bytes(8, "big")); h.update(dados)
    return "sha256:" + h.hexdigest()


def _versao_ffmpeg() -> str:
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True,
                           text=True, timeout=60)
    except Exception:
        return "ausente"
    m = re.search(r"ffmpeg version (\S+)", r.stdout or "")
    return m.group(1) if m else "nao legivel"


def _versao_libopus() -> str:
    """A string do PROPRIO libopus, nao a etiqueta do pacote do sistema.

    O mixer chama a biblioteca que o ffmpeg carregou: mesmo binario de
    ffmpeg pode linkar libopus diferente em cada maquina, e o .opus muda
    com ela.
    """
    for nome in ("libopus.so.0", "libopus.so"):
        try:
            lib = ctypes.CDLL(nome)
        except OSError:
            continue
        try:
            lib.opus_get_version_string.restype = ctypes.c_char_p
            return lib.opus_get_version_string().decode().removeprefix("libopus ")
        except Exception:
            return "nao legivel"
    return "nao medivel"


def ambiente_instalado() -> dict:
    """As versoes EFETIVAS do ambiente de sintese — medidas, nunca assumidas.

    Cada chave e medida na hora, no caminho que o dublar de fato usa:
    importlib.metadata para os pacotes, o proprio espeak-ng-data do wheel,
    o binario do ffmpeg, a biblioteca libopus carregada. E a mesma lista
    do bloco ambiente do voz.lock -- quem crescer de um lado tem de
    crescer do outro, e a conferencia e bidirecional.
    """
    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        **{p: _versao_pacote(p) for p in PACOTES},
        "espeak-ng": _sha_espeak(),
        "ffmpeg": _versao_ffmpeg(),
        "libopus": _versao_libopus(),
    }


def _correcao(pacote: str, esperado: dict) -> str:
    """O comando que alinha o ambiente com a ancora — o erro nao cala."""
    if pacote == "python":
        return f"rode com Python {esperado['python']} (a serie do runtime e ancora)"
    if pacote == "espeak-ng":
        return ("reinstale o wheel que embute o fonemizador: "
                f"pip install --force-reinstall piper-tts=={esperado.get('piper-tts', '?')}")
    if pacote == "ffmpeg":
        return f"instale ffmpeg {esperado['ffmpeg']} (a build inteira e a ancora)"
    if pacote == "libopus":
        return f"instale libopus {esperado['libopus']} (no Debian: apt install libopus0)"
    return f"pip install {pacote}=={esperado[pacote]}"


def conferir_ambiente(esperado: dict) -> dict:
    """Confere o ambiente instalado contra o bloco ambiente do voz.lock.

    Levanta ErroDeDados nomeando TODAS as divergencias — pacote, versao
    esperada, versao instalada e o comando que corrige — e devolve o
    ambiente medido para o manifesto (nao sai daqui divergindo, entao o
    devolvido e o ancorado). Sem flag de contorno, de proposito: dublar
    em ambiente divergente produziria audio que ninguem ancorou, e a
    divergencia silenciosa e exatamente o que o lock existe para impedir.
    Bidirecional: componente medido sem ancora e lock atrasado; ancora
    sem medida e codigo atrasado. Os dois sao divida, nao preferencia.
    """
    instalado = ambiente_instalado()
    divergencias = []
    for pacote in sorted(set(esperado) | set(instalado)):
        esp, inst = esperado.get(pacote), instalado.get(pacote)
        if esp == inst:
            continue
        if esp is None:
            divergencias.append(
                f"{pacote}: o ambiente mede {inst}, mas o voz.lock nao ancora — "
                f"componente sem ancora e lock atrasado, nao medida a mais")
        elif inst is None:
            divergencias.append(
                f"{pacote}: o lock ancora, mas o ambiente_instalado() nao mede — "
                f"codigo e lock cresceram separados, e isso e divida de CP")
        else:
            divergencias.append(
                f"{pacote}: esperado {esp}, instalado {inst}. "
                f"Corrige: {_correcao(pacote, esperado)}")
    if divergencias:
        raise ErroDeDados(
            "o ambiente de sintese NAO e o ancorado em voz.lock (bloco "
            "ambiente, CP-007) — dublar aqui produziria audio divergente do "
            "commitado sem ninguem ter editado nada:\n  "
            + "\n  ".join(divergencias) +
            "\n  O lock avanca por change-proposal; a saida nunca e dublar "
            "por cima da divergencia.")
    return instalado


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _copiar_de(origem: Path, a: dict) -> bool:
    """Um download previo ao lado da suite evita rede. So serve se bater."""
    if not origem.is_dir():
        return False
    for rel in a["arquivos"]:
        f = origem / rel
        if not f.exists() or _sha256(f) != a["arquivos"][rel]:
            return False
    for rel in a["arquivos"]:
        alvo = DESTINO / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem / rel, alvo)
    return True


def _baixar(a: dict, base_url: str) -> None:
    for rel in a["arquivos"]:
        url = f"{base_url.rstrip('/')}/{rel}"
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                dados = r.read()
        except Exception as e:
            raise ErroDeDados(
                f"nao consegui baixar '{rel}' de {a['origem']}: {e}\n"
                f"  O modelo e bem publico (piper-voices). Baixe a mao, deixe os "
                f"arquivos em workspace/voz/, e rode de novo: o lock confere o "
                f"hash antes de usar."
            ) from None
        alvo = DESTINO / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(dados)


def materializar(forcar: bool = False) -> Path:
    """Garante workspace/voz/ com o modelo ancorado, e confere cada hash."""
    a = ancora()
    completo = all((DESTINO / rel).exists() for rel in a["arquivos"])
    if forcar or not completo:
        DESTINO.mkdir(parents=True, exist_ok=True)
        # Um vizinho com o modelo ja baixado evita rede (mesma graca de lei.py).
        candidatos = [RAIZ / "_voz-origem", RAIZ.parent / "piper-voices", WORKSPACE / "piper-voices"]
        if not any(_copiar_de(c, a) for c in candidatos):
            _baixar(a, a["origem"])

    divergem = []
    for rel, esperado in a["arquivos"].items():
        f = DESTINO / rel
        if not f.exists():
            divergem.append(f"{rel}: ausente")
        elif _sha256(f) != esperado:
            divergem.append(f"{rel}: {_sha256(f)[:12]} != {esperado[:12]} declarado")
    if divergem:
        raise ErroDeDados(
            "o modelo local NAO e o modelo ancorado em voz.lock:\n  "
            + "\n  ".join(divergem) +
            "\n  Dublar com pesos divergentes produziria um audio que ninguem "
            "declarou. Baixe o modelo do lock, ou avance o lock por "
            "change-proposal -- nunca dublar por cima da divergencia."
        )
    return DESTINO
