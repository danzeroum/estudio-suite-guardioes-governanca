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
"""
import hashlib
import re
import shutil
import urllib.request
from pathlib import Path

from .comum import ErroDeDados, RAIZ, WORKSPACE

LOCK = RAIZ / "voz.lock"
DESTINO = WORKSPACE / "voz"


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
    return {"nome": nome.group(1), "origem": origem.group(1), "arquivos": arquivos}


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
