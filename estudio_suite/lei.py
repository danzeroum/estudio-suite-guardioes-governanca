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
    """Baixa cada arquivo ancorado por HTTPS simples, no commit exato.

    Nao usa git. O protocolo git pedindo um SHA solto faz o GitHub responder
    de um jeito que leva o cliente a pedir usuario -- e num runner sem tty isso
    vira "could not read Username", que nao se parece nem um pouco com a causa.
    Foi assim que quatro execucoes de CI morreram.

    raw.githubusercontent.com serve o arquivo NO COMMIT, sem autenticacao e sem
    clonar a arvore inteira. E o hash de lei.lock que decide se o que chegou
    serve: a origem do byte importa menos do que ele ser o byte declarado.
    """
    import urllib.error
    import urllib.request

    dono_repo = a["repo"]
    for rel in a["arquivos"]:
        url = f"https://raw.githubusercontent.com/{dono_repo}/{a['sha']}/{rel}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                dados = r.read()
        except urllib.error.HTTPError as e:
            extra = ""
            if e.code in (401, 403, 404):
                # 404 do GitHub cobre "nao existe" E "voce nao pode ver".
                # danzeroum/guardioes-governanca e PRIVADO, entao esta rota
                # anonima nunca serve para ele -- e dizer "sem rede" aqui
                # mandaria quem le procurar o problema no lugar errado.
                extra = (f"\n  {dono_repo} pode ser privado: esta rota e anonima e "
                         f"nao ve repositorio fechado.\n"
                         f"  Deixe um checkout dele ao lado desta suite, ou em "
                         f"_lei-origem/ dentro dela.\n"
                         f"  No CI, isso exige um segredo com permissao de leitura.")
            raise ErroDeDados(
                f"nao consegui baixar '{rel}' de {dono_repo} no commit "
                f"{a['sha'][:12]}: HTTP {e.code}.{extra}"
            ) from None
        except Exception as e:
            raise ErroDeDados(
                f"nao consegui alcancar {dono_repo} para buscar a lei: {e}\n"
                f"  Sem rede? Deixe um checkout de {dono_repo} ao lado desta "
                f"suite, ou em _lei-origem/ dentro dela."
            ) from None
        alvo = DESTINO / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(dados)


def materializar(forcar: bool = False) -> Path:
    """Garante workspace/lei/ com os arquivos ancorados, e confere cada hash."""
    a = ancora()
    completo = all((DESTINO / rel).exists() for rel in a["arquivos"])
    if forcar or not completo:
        DESTINO.mkdir(parents=True, exist_ok=True)
        # Onde um checkout da origem pode estar. No CI o actions/checkout
        # recusa path fora do workspace, entao ele cai em _lei-origem/ aqui
        # dentro -- que o .gitignore recusa, para nao virar copia versionada.
        nome = a["repo"].split("/")[-1]
        candidatos = [RAIZ / "_lei-origem", RAIZ.parent / nome, WORKSPACE / nome]
        if not any(_copiar_de(c, a) for c in candidatos):
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
