"""Transforma sinal em change-proposal. DECLARADA antes de executada.

A proposta nao e um pedido de permissao generico: ela diz o que muda, que
caminhos toca, que risco corre e como se prova que funcionou. E fica no
repositorio mesmo depois de executada, porque proposta e REGISTRO HISTORICO --
uma que se apaga ao ser cumprida deixa o repositorio sem a pergunta "por que
isto e assim?".

O modulo propoe; quem aprova e humano, quando o caminho e protegido.
"""
import datetime
import re

from ..comum import HARNESS
from . import evidencias

CP = HARNESS / "change-proposals"

# O que o modulo NAO pode mudar sozinho, por mais verde que o gate fique.
# Um modulo que pode editar o proprio fiscal acaba editando o proprio fiscal.
PROTEGIDOS = ["motor/", "lei.lock", "ci/", "tests/", "harness/policies/",
              ".github/", "CLAUDE.md", "suite.yaml"]

MOLDE = """# Mudanca proposta a partir de EVIDENCIA, nao de gosto.
# Declarada antes de executada; fica como registro mesmo depois.
schema: estudio-suite/change-proposal@1

proposta:
  id: {cpid}
  titulo: "{titulo}"
  autor: agente/curador
  criada_em: "{quando}"
  estado: rascunho          # rascunho | aprovada | executada | recusada | adiada

  sinal:
    tipo: {tipo}
    chave: "{chave}"
    evidencia: >
      {evidencia}

  caminhos_afetados:
{caminhos}

  risco:
    nivel: {risco}
    porque: >
      {porque}

  aval_humano_necessario: {aval}

  como_se_prova:
{prova}
"""


def _cpid(existentes):
    ns = [int(m.group(1)) for f in existentes
          if (m := re.match(r"CP-(\d+)", f.name))]
    return f"CP-{(max(ns) + 1 if ns else 1):03d}"


def _receita(s):
    """Cada tipo de sinal vira uma proposta com caminhos, risco e prova proprios."""
    if s["tipo"] == "promocao":
        chave = s["chave"]
        return dict(
            titulo=f"Promover '{chave}' ao elenco compartilhado",
            caminhos=["motor/js/props.js ou motor/js/cenarios.js",
                      *[f"filmes/{f}/local/" for f in s["filmes"]]],
            risco="medio",
            porque=("Promover muda o motor, que e caminho protegido. Em troca, "
                    "deixar duas copias divergirem e o defeito que a regra da "
                    "segunda repeticao existe para evitar: o mesmo adereço nasce "
                    "n vezes ligeiramente diferente, e nenhuma versao e a certa."),
            aval="true",
            prova=["o adereço sai de todos os local/ e os filmes seguem verdes",
                   "as referencias de palco dos filmes envolvidos sao regravadas",
                   "python3 tests/test_navegador.py passa"])
    if s["tipo"] == "portao-teimoso":
        return dict(
            titulo=f"Rever o portao que reprova sempre: {s['chave'][:50]}",
            caminhos=["estudio_suite/pipeline.py ou tests/"],
            risco="alto",
            porque=("Portao que reprova em muitos alvos nao e um alvo ruim: ou o "
                    "portao esta errado, ou falta ferramenta para atende-lo. As "
                    "duas leituras precisam estar na proposta, porque afrouxar um "
                    "fiscal para o CI passar e a terceira opcao, e e a errada."),
            aval="true",
            prova=["o portao reprova o caso que deve reprovar (teste negativo)",
                   "e aprova o caso legitimo que hoje ele reprova"])
    if s["tipo"] == "orcamento":
        return dict(
            titulo=f"Dividir {s['chave']} por temperatura",
            caminhos=[s["chave"]],
            risco="medio",
            porque=("O arquivo passou da faixa de aviso. A resposta NAO e "
                    "afrouxar o teto: foi assim que chassi.js nasceu -- separar "
                    "o que roda por quadro do que roda uma vez no boot fez o "
                    "arquivo encolher e ficar melhor de ler."),
            aval="true",
            prova=["o arquivo encolhe; se crescer, a divisao nao valeu e reverte",
                   "os testes de navegador passam sem reescrita"])
    return None


def gerar(escrever=False):
    """Gera propostas para os sinais que ainda nao tem uma."""
    CP.mkdir(parents=True, exist_ok=True)
    existentes = sorted(CP.glob("CP-*.yaml"))
    ja = "\n".join(f.read_text(encoding="utf-8") for f in existentes)
    quando = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    novas = []
    for s in evidencias.sinais():
        # Aviso e INFORMACAO; proposta e CHAMADO A ACAO. Um arquivo a 71% do
        # teto nao precisa de ninguem agora, e abrir proposta para ele encheria
        # a fila de coisas que nao sao para fazer -- e fila que ninguem le e
        # fila que nao existe.
        if s["tipo"] == "orcamento" and s["fracao"] < 0.85:
            continue
        if f'chave: "{s["chave"]}"' in ja:
            continue                      # sinal ja tem proposta: nao duplica
        r = _receita(s)
        if not r:
            continue
        cpid = _cpid(existentes + [type("F", (), {"name": n})() for n in novas])
        corpo = MOLDE.format(
            cpid=cpid, quando=quando, tipo=s["tipo"], chave=s["chave"],
            evidencia=s["evidencia"], titulo=r["titulo"], risco=r["risco"],
            porque=r["porque"], aval=r["aval"],
            caminhos="\n".join(f"    - {c}" for c in r["caminhos"]),
            prova="\n".join(f"    - {c}" for c in r["prova"]))
        nome = f"{cpid}-{re.sub(r'[^a-z0-9]+', '-', r['titulo'].lower())[:50].strip('-')}.yaml"
        novas.append(nome)
        if escrever:
            (CP / nome).write_text(corpo, encoding="utf-8")
            existentes = sorted(CP.glob("CP-*.yaml"))
            ja += corpo
    return novas
