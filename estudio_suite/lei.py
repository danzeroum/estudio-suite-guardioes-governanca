"""A lei: ancorada por SHA, materializada efemera, conferida byte a byte.

Esta suite NAO versiona o texto da LGPD. Ela declara em `lei.lock` de qual
commit de `danzeroum/guardioes-governanca` a lei vem, e materializa em
`workspace/lei/`, que o .gitignore recusa.

A conferencia de hash e o ponto inteiro. Materializar sem conferir seria uma
copia com passo extra: se a origem mudasse embaixo da ancora, o validador
passaria a medir os roteiros contra uma lei que ninguem declarou -- e diria
"tudo certo", porque de fato estaria tudo certo contra a lei errada.
"""
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

from .comum import ErroDeDados, RAIZ, WORKSPACE, json_de_js  # noqa: F401

LOCK = RAIZ / "lei.lock"
DESTINO = WORKSPACE / "lei"


def ancora() -> dict:
    """Le lei.lock sem dependencia de YAML: o formato e fixo e raso de proposito."""
    if not LOCK.exists():
        raise ErroDeDados("lei.lock nao existe. Sem ancora, nao ha lei para medir o roteiro.")
    txt = LOCK.read_text(encoding="utf-8")
    sha = re.search(r"^\s*sha:\s*([0-9a-f]{40})\s*$", txt, re.M)
    url = re.search(r"^\s*url:\s*(\S+)\s*$", txt, re.M)
    repo = re.search(r"^\s*repo:\s*(\S+)\s*$", txt, re.M)
    if not (sha and url and repo):
        raise ErroDeDados("lei.lock sem origem.sha / origem.url / origem.repo legiveis.")
    arquivos = dict(re.findall(r"^  (\S+):\n    sha256:\s*([0-9a-f]{64})", txt, re.M))
    if not arquivos:
        raise ErroDeDados("lei.lock nao lista nenhum arquivo com sha256.")
    return {"sha": sha.group(1), "url": url.group(1), "repo": repo.group(1),
            "arquivos": arquivos}


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _copiar_de(origem: Path, a: dict) -> bool:
    """Um checkout vizinho ja no disco evita rede. So serve se os hashes baterem."""
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


def _buscar_do_remoto(a: dict) -> None:
    repo = WORKSPACE / "lei-git"
    repo.mkdir(parents=True, exist_ok=True)
    def git(*args, **kw):
        return subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, text=True, **kw)
    if not (repo / ".git").exists():
        git("init", "-q")
        git("remote", "add", "origem", a["url"])
    r = git("fetch", "--depth", "1", "origem", a["sha"])
    if r.returncode != 0:
        raise ErroDeDados(
            f"nao consegui buscar a lei em {a['repo']} no commit {a['sha'][:12]}.\n"
            f"  git: {(r.stderr or '').strip()[:200]}\n"
            f"  Sem rede? Deixe um checkout de {a['repo']} ao lado desta suite."
        )
    for rel in a["arquivos"]:
        r = git("checkout", "FETCH_HEAD", "--", rel)
        if r.returncode != 0:
            raise ErroDeDados(f"o commit ancorado nao tem '{rel}': {(r.stderr or '').strip()[:160]}")
        alvo = DESTINO / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / rel, alvo)


def materializar(forcar: bool = False) -> Path:
    """Garante workspace/lei/ com os arquivos ancorados, e confere cada hash."""
    a = ancora()
    completo = all((DESTINO / rel).exists() for rel in a["arquivos"])
    if forcar or not completo:
        DESTINO.mkdir(parents=True, exist_ok=True)
        vizinho = RAIZ.parent / a["repo"].split("/")[-1]
        if not _copiar_de(vizinho, a):
            _buscar_do_remoto(a)

    # A conferencia roda SEMPRE, inclusive quando nada foi baixado: o arquivo
    # pode ter sido editado no workspace entre uma execucao e a seguinte.
    divergem = []
    for rel, esperado in a["arquivos"].items():
        f = DESTINO / rel
        if not f.exists():
            divergem.append(f"{rel}: ausente")
        elif _sha256(f) != esperado:
            divergem.append(f"{rel}: {_sha256(f)[:12]} != {esperado[:12]} declarado")
    if divergem:
        raise ErroDeDados(
            "a lei materializada nao e a lei ancorada:\n  " + "\n  ".join(divergem) +
            "\n  Rode com --refazer-lei, ou avance lei.lock por change-proposal."
        )
    return DESTINO


def carregar():
    """Devolve (artigos, guardioes) da lei ancorada."""
    import json
    base = materializar()
    arts = json.loads((base / "docs/assets/data/lgpd-arts.json").read_text(encoding="utf-8"))
    gap = json.loads((base / "docs/assets/data/gap-matrix.json").read_text(encoding="utf-8"))
    return arts["artigos"], gap["guardioes"]
