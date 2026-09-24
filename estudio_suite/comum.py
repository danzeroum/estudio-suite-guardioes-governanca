"""Fundamentos partilhados: caminhos, o truque JSON-em-JS, e o vocabulario.

O VOCABULARIO NAO MORA AQUI. Ele mora no motor JS e e LIDO de la. Redeclarar
`ACOES`, `NUMERICAS`, `EVENTOS` e `EASES` em Python seria duas copias de uma
verdade so: acrescentar um easing ao motor faria o validador reprovar roteiro
valido, e remover um faria ele aprovar roteiro que o motor renderiza errado.
Nada conferiria, porque nao ha como conferir duas copias -- so ha como nao
ter duas. A Fase 7 do repositorio de origem pagou por essa licao.
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MOTOR = RAIZ / "motor" / "js"
FILMES = RAIZ / "filmes"
JOGOS = RAIZ / "jogos"
PAGINAS = RAIZ / "paginas"
HARNESS = RAIZ / "harness"
WORKSPACE = RAIZ / "workspace"


class ErroDeDados(Exception):
    """Dado do repositorio ilegivel -- sai 2, nunca 1.

    A distincao e do `project`: divergencia entre o declarado e o real e uma
    coisa (exit 1); fiscal que NAO CONSEGUIU fiscalizar e outra (exit 2).
    Colapsar as duas faz 'estou sem a lei' e 'o roteiro esta errado' ficarem
    indistinguiveis, e a leitura barata vence.
    """


def json_de_js(caminho: Path):
    """Corta o prefixo de uma linha e o ';' final; o resto e JSON estrito.

    O mesmo arquivo e carregado pelo navegador por <script src> e lido aqui
    por json.loads -- uma fonte, dois leitores. Sob file:// nao ha fetch, e
    e essa restricao que escolheu o formato.
    """
    txt = caminho.read_text(encoding="utf-8")
    try:
        i = txt.index("=\n", txt.index("window.ESTUDIO_"))
    except ValueError:
        raise ErroDeDados(
            f"{caminho.name}: nao achei o prefixo 'window.ESTUDIO_...=' seguido de "
            f"quebra de linha. O arquivo tem de ser JSON estrito depois dele."
        ) from None
    corpo = txt[i + 2:].rstrip().rstrip(";").strip()
    try:
        return json.loads(corpo)
    except json.JSONDecodeError as e:
        linha = corpo[:e.pos].count("\n") + txt[:i].count("\n") + 2
        raise ErroDeDados(
            f"{caminho.name} nao e JSON valido depois do prefixo.\n"
            f"  {e.msg}, por volta da linha {linha} do arquivo.\n"
            f"  (sem virgula sobrando, sem comentario, aspas duplas)"
        ) from None


def _lista_js(arquivo: str, nome: str) -> set:
    txt = (MOTOR / arquivo).read_text(encoding="utf-8")
    m = re.search(r"var\s+" + nome + r"\s*=\s*\[(.*?)\]\s*;", txt, re.S)
    return set(re.findall(r"'([^']+)'", m.group(1))) if m else set()


def _chaves_js(arquivo: str, nome: str) -> set:
    txt = (MOTOR / arquivo).read_text(encoding="utf-8")
    i = txt.find("var " + nome)
    return set(re.findall(r"^\s*(\w+):\s*function", txt[i:], re.M)) if i >= 0 else set()


ACOES = _lista_js("filme.js", "ACOES")
NUMERICAS = _lista_js("filme.js", "NUMERICAS")
EVENTOS = _lista_js("filme.js", "EVENTOS")
EASES = _chaves_js("interp.js", "EASE")
CAMADAS = _lista_js("palco.js", "CAMADAS")

# Um regex quebrado devolveria conjunto vazio, e conjunto vazio nao reprova
# nada: o validador passaria a aprovar tudo, calado. Que e exatamente o modo
# de falhar que ler do motor existe para eliminar -- entao a leitura se confere.
_ESPERADO = {"ACOES": 5, "NUMERICAS": 5, "EVENTOS": 3, "EASES": 6, "CAMADAS": 6}
for _nome, _quanto in _ESPERADO.items():
    _v = globals()[_nome]
    if len(_v) != _quanto:
        raise ErroDeDados(
            f"nao consegui ler {_nome} do motor JS (li {sorted(_v)}, esperava "
            f"{_quanto} itens). Se o motor mudou de proposito, ajuste _ESPERADO "
            f"em estudio_suite/comum.py."
        )


def filmes_existentes():
    """Os filmes sao descobertos do disco, nunca de uma lista.

    Uma lista de filmes num arquivo de configuracao seria uma segunda
    descricao do diretorio: ela deriva em silencio no dia em que alguem
    acrescentar um filme e esquecer de registra-lo.
    """
    return sorted(d.name for d in FILMES.iterdir()
                  if d.is_dir() and (d / f"{d.name}.filme.js").exists())


def filmes_com_audio():
    """Os filmes que DECLARAM audio, lidos do proprio filme.js (CP-011).

    A declaracao `audio: true` mora no filme, nao em lista de nomes: uma
    lista hardcoded no job dublador envelheceria no primeiro filme mudo
    (um relatorio, um filme sem trilha) e acionaria dublagem de quem nao
    fala. O job dublador so acorda para quem declara -- e um filme mudo
    nao entra na lista nem aciona o job.
    """
    fora = []
    for fid in filmes_existentes():
        try:
            d = dados_do_filme(fid)
        except ErroDeDados as e:
            fora.append((fid, str(e)))
            continue
        if d.get("audio"):
            yield fid
        else:
            fora.append((fid, "nao declara audio"))
    # A descoberta que FALHOU nao pode calar: filme ilegivel na pasta de
    # filmes e divida apontada, nao filme ignorado em silencio.
    if fora:
        import sys
        print(f"  (fora da lista de dublagem: "
              + "; ".join(f"{fid}: {motivo}" for fid, motivo in fora)
              + ")", file=sys.stderr)


def jogos_existentes():
    return sorted(d.name for d in JOGOS.iterdir()
                  if d.is_dir() and (d / f"{d.name}.jogo.js").exists())


def _com_id(d, esperado: str, arquivo: str):
    """O id declarado tem de bater com o diretorio.

    Divergir aqui e barato de fazer (copiar um filme para comecar outro) e caro
    de achar: o navegador registra sob um id, a pasta se chama outro, e o
    carregador traz o arquivo certo que registra o filme errado.
    """
    if d.get("id") != esperado:
        raise ErroDeDados(
            f"{arquivo}: declara id '{d.get('id')}', mas mora em '{esperado}/'. "
            f"O id e o nome da pasta -- um dos dois esta errado."
        )
    return d


def dados_do_filme(fid: str):
    return _com_id(json_de_js(FILMES / fid / f"{fid}.filme.js"), fid, f"{fid}.filme.js")


def dados_do_jogo(jid: str):
    return _com_id(json_de_js(JOGOS / jid / f"{jid}.jogo.js"), jid, f"{jid}.jogo.js")
