#!/usr/bin/env python3
"""Valida os roteiros do Estudio dos Guardioes. Sem navegador, em segundos.

O teste mais valioso do conjunto e o de CITACAO: toda legenda que cita um
artigo tem esse numero conferido contra docs/assets/data/lgpd-arts.json e
contra o guardiao do plano em gap-matrix.json. O filme nao consegue citar um
artigo que o repo nao tem, nem atribui-lo ao guardiao errado.

Validar so o campo 'arts' nao bastaria: ninguem garante que o texto que o
espectador LE diga a mesma coisa que o metadado. Por isso a varredura e sobre
o texto da legenda.

O .filme.js e JSON estrito dentro de um involucro JS de uma linha, entao o
mesmo arquivo que o navegador carrega por <script src> e lido aqui com
json.loads -- sem duplicar a fonte. Mesmo truque de guardioes.data.js.
"""
import json
import re
import sys
from pathlib import Path

from .comum import (ACOES, CAMADAS, EASES, EVENTOS, NUMERICAS, ErroDeDados,
                    FILMES, JOGOS, RAIZ, dados_do_filme, dados_do_jogo,
                    filmes_existentes, jogos_existentes, json_de_js)
from . import lei as _lei

# Numeros por extenso que uma legenda pode usar para CONTAR incisos.
# 'um' e 'uma' ficam DE FORA, de proposito: em portugues sao artigo indefinido
# muito mais vezes do que numeral. "nem um a mais" e "uma das dez rotas" nao
# contam incisos, e inclui-los enchia a guarda de falso positivo. E uma excecao
# nomeada, nao um skip generico -- os outros numerais continuam valendo.
EXTENSO = {"dois": 2, "duas": 2, "tres": 3, "três": 3, "quatro": 4,
           "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
           "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
           "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18,
           "dezenove": 19, "vinte": 20}
ROMANOS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII",
           "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]

# Limites de legenda (R12). 15 cps e teto tecnico, nao meta.
CPS, DUR_MIN, LINHAS_MAX, COLUNAS_MAX = 15.0, 1.2, 2, 42

falhas, avisos, checados = [], [], 0


def falha(msg):
    falhas.append(msg)



def bloco_chaves(txt, campo):
    """Nomes de chave de um objeto literal, sem executar JS."""
    m = re.search(campo + r":\s*\{", txt)
    if not m:
        return set()
    i, nivel = m.end() - 1, 0
    for j in range(i, len(txt)):
        nivel += (txt[j] == "{") - (txt[j] == "}")
        if nivel == 0:
            return set(re.findall(r"'([a-zA-Z-]+)':\s*\{", txt[i:j + 1]))
    return set()


def rigs_de_js(caminho):
    """Um ou mais rigs por arquivo: rigs/*.rig.js traz um, props.js traz seis.
    Props ganham expressoes: {neutro} em runtime, entao aqui o padrao e esse."""
    txt = caminho.read_text(encoding="utf-8")
    pedacos = txt.split("prop({")[1:] or [txt]
    out = []
    for pedaco in pedacos:
        ident = re.search(r"id:\s*'([a-z-]+)'", pedaco)
        if not ident:
            continue
        out.append({
            "id": ident.group(1),
            "poses": bloco_chaves(pedaco, "poses"),
            "expressoes": bloco_chaves(pedaco, "expressoes") or {"neutro"},
            "partes": set(re.findall(r'data-part="([^"]+)"', pedaco)),
        })
    return out


def incisos_do_caput(texto):
    """Quantos incisos o CAPUT do artigo enumera.

    Para no primeiro paragrafo: as listas dentro de um paragrafo sao outra
    coisa. No Art. 18, por exemplo, o caput enumera os nove direitos do
    titular, e o § 4o enumera duas RESPOSTAS DO CONTROLADOR -- contar os onze
    juntos foi exatamente o erro que esta funcao existe para impedir.
    """
    fim = texto.find("§ 1")
    caput = texto if fim < 0 else texto[:fim]
    n = 0
    for r in ROMANOS:
        if re.search(rf"(?:^|\s){re.escape(r)}\s+-\s", caput):
            n += 1
        else:
            break
    return n


def confere_contagem(pid, legs, numeros_art, arts):
    """Uma legenda que diz um numero, num plano sobre um artigo, esta
    AFIRMANDO quanto aquele artigo enumera. Conferir o numero do ARTIGO nao
    basta: 'Art. 18' estava certo enquanto a legenda dizia 'onze direitos', e
    o caput do 18 tem nove.

    O escopo e o PLANO, nao a legenda: a afirmacao e a citacao costumam cair
    em legendas diferentes do mesmo plano -- foi assim no p12, e por isso a
    primeira versao desta guarda nao pegou nada.

    A regra e frouxa de proposito: se a legenda tem numeros, ao menos UM tem
    de bater com o que o caput enumera. 'uma das dez rotas' tem dois numeros
    e so o 'dez' conta -- exigir que todos batessem reprovaria a legenda boa.
    """
    esperados = set()
    for n in numeros_art:
        art = arts.get(str(n))
        if art:
            q = incisos_do_caput(art["texto"])
            if q:
                esperados.add(q)
    if not esperados:
        return
    texto = " ".join(L["txt"] for L in legs)
    achados = {}
    for m in re.finditer(r"\b([a-zA-ZçãéêÊÉ]+)\b", texto):
        v = EXTENSO.get(m.group(1).lower())
        if v:
            achados[v] = m.group(1)
    for m in re.finditer(r"\b(\d{1,2})\b", texto):
        if int(m.group(1)) not in [int(x) for x in numeros_art]:   # o numero do artigo nao conta
            achados[int(m.group(1))] = m.group(1)
    if achados and not (set(achados) & esperados):
        falha(f"{pid}: as legendas dizem {sorted(achados.values())} num plano sobre "
              f"Art. {numeros_art}, cujo caput enumera {sorted(esperados)} incisos")


def valida_jogos(arts):
    """O jogo embute o texto dos incisos porque sob file:// nao ha fetch --
    mesma razao de livro-lgpd/assets/guardioes.data.js. Embutir so e seguro
    se alguem comparar: aqui o texto e conferido BYTE A BYTE contra
    lgpd-arts.json, e a camada autoral (rotulo, pedido) so pode apontar
    incisos que existem."""
    global checados
    for jid in jogos_existentes():
        caminho = JOGOS / jid / f"{jid}.jogo.js"
        d = dados_do_jogo(jid)
        nome = f"{jid}.jogo.js"
        num = str(d.get("artigo", ""))
        art = arts.get(num)
        checados += 1
        if not art:
            falha(f"{nome}: artigo {num} nao existe em lgpd-arts.json")
            continue
        if d.get("guardiao") and art["guardiao"] != d["guardiao"]:
            falha(f"{nome}: diz que o Art. {num} e de '{d['guardiao']}', mas e de "
                  f"'{art['guardiao']}'")

        esperado = incisos_do_caput(art["texto"])
        checados += 1
        if len(d.get("direitos") or []) != esperado:
            falha(f"{nome}: lista {len(d.get('direitos') or [])} direitos, mas o caput do "
                  f"Art. {num} enumera {esperado}")

        # O texto de cada inciso, literal, contra a fonte.
        caput = art["texto"][:art["texto"].find("§ 1")]
        for dir_ in d.get("direitos") or []:
            checados += 1
            alvo = re.sub(r"\s+", " ", dir_["texto"]).strip()
            if alvo not in re.sub(r"\s+", " ", caput):
                falha(f"{nome}: o texto do inciso {dir_['inciso']} nao bate com "
                      f"lgpd-arts.json (foi digitado a mao?)")
            if not (dir_.get("rotulo") or "").strip():
                falha(f"{nome}: inciso {dir_['inciso']} sem rotulo")

        validos = {x["inciso"] for x in d.get("direitos") or []}
        for s_ in d.get("situacoes") or []:
            checados += 1
            if s_["inciso"] not in validos:
                falha(f"{nome}: situacao aponta o inciso '{s_['inciso']}', que nao existe")
            if not (s_.get("pedido") or "").strip():
                falha(f"{nome}: situacao sem texto de pedido")
        checados += 1
        if len(validos) != len(d.get("direitos") or []):
            falha(f"{nome}: ha incisos repetidos na lista de direitos")

        # Cobertura: todo direito tem de aparecer em pelo menos uma situacao.
        # Um direito orfao nao quebra nada -- o jogo roda igual -- e por isso
        # mesmo passaria sem ninguem ver: a pessoa simplesmente nunca seria
        # perguntada sobre ele. Num material que se propoe a ensinar os nove,
        # ensinar oito calado e o pior resultado possivel.
        checados += 1
        usados = {s_["inciso"] for s_ in d.get("situacoes") or []}
        orfaos = sorted(validos - usados, key=lambda i: ROMANOS.index(i))
        if orfaos:
            falha(f"{nome}: os incisos {orfaos} nao tem nenhuma situacao que os "
                  f"exercite -- quem joga nunca e perguntado sobre eles")


def main():
    global checados
    arts, gmx = _lei.carregar()
    base_lei = _lei.materializar()
    rigs = {}
    for f in sorted((RAIZ / "motor/js/rigs").glob("*.rig.js")) + [RAIZ / "motor/js/props.js"]:
        for r in rigs_de_js(f):
            rigs[r["id"]] = r

    # --- paridade de tokens entre o estudio e o tema do site ---------------
    # A cor canonica e da lei, nao da suite: personagens.css tem de OBEDECER.
    tema = (base_lei / "docs/assets/css/theme.css").read_text(encoding="utf-8")
    pers = (RAIZ / "motor/css/personagens.css").read_text(encoding="utf-8")
    for gid in gmx:
        a = re.search(rf"--c-{gid}:\s*(#[0-9a-fA-F]{{6}})", tema)
        b = re.search(rf"--rig-{gid}:\s*(#[0-9a-fA-F]{{6}})", pers)
        checados += 1
        if not (a and b):
            falha(f"token de {gid} ausente em theme.css ou personagens.css")
        elif a.group(1).lower() != b.group(1).lower():
            falha(f"cor canonica de {gid} diverge: theme.css {a.group(1)} x "
                  f"personagens.css {b.group(1)}")

    for fid in filmes_existentes():
        caminho = FILMES / fid / f"{fid}.filme.js"
        d = dados_do_filme(fid)
        nome = f"{fid}.filme.js"
        alvos = set(d.get("elenco", {})) | set(d.get("props", {}))
        rig_de = {}
        for a, meta in list(d.get("elenco", {}).items()) + list(d.get("props", {}).items()):
            rig_de[a] = meta.get("rig", a)
            checados += 1
            if rig_de[a] not in rigs:
                falha(f"{nome}: alvo '{a}' usa rig '{rig_de[a]}', que nao existe")

        # --- duracao ------------------------------------------------------
        soma = sum(P["dur"] for P in d["planos"])
        checados += 1
        if abs(soma - d["duracao"]) > 1e-6:
            falha(f"{nome}: duracao declarada {d['duracao']}s, soma dos planos {soma}s")

        vistos_guardiao = set()
        for P in d["planos"]:
            pid = f"{nome}/{P['id']}"
            if P.get("guardiao"):
                vistos_guardiao.add(P["guardiao"])

            for a, e in (P.get("entra") or {}).items():
                checados += 1
                if a not in alvos:
                    falha(f"{pid}: entra '{a}' fora do elenco")
                    continue
                for p, v in e.items():
                    if p in ("pose", "expressao"):
                        campo = "poses" if p == "pose" else "expressoes"
                        if v not in rigs[rig_de[a]][campo]:
                            falha(f"{pid}: '{a}' ({rig_de[a]}) nao tem {p} '{v}'")
                    elif p not in NUMERICAS and p != "espelho":
                        falha(f"{pid}/entra/{a}: propriedade '{p}' desconhecida")

            for A in P.get("acoes") or []:
                checados += 1
                a = A.get("alvo")
                if a != "camera" and a not in alvos:
                    falha(f"{pid}: acao com alvo '{a}' fora do elenco")
                if not (ACOES & set(A)):
                    falha(f"{pid}/{a}: acao sem verbo")
                if A.get("ease") and A["ease"] not in EASES:
                    falha(f"{pid}/{a}: ease '{A['ease']}' fora da tabela")
                dur = A.get("dur", 0)
                if A.get("em", 0) + dur > P["dur"] + 1e-6:
                    falha(f"{pid}/{a}: acao em {A.get('em')}+{dur} passa da duracao "
                          f"do plano ({P['dur']}s)")
                for p in (A.get("para") or {}):
                    if p not in NUMERICAS:
                        falha(f"{pid}/{a}: propriedade '{p}' nao e animavel")
                for p, campo in (("pose", "poses"), ("expressao", "expressoes")):
                    if A.get(p) and a in rig_de and A[p] not in rigs[rig_de[a]][campo]:
                        falha(f"{pid}: '{a}' ({rig_de[a]}) nao tem {p} '{A[p]}'")
                if A.get("evento"):
                    if A["evento"] not in EVENTOS:
                        falha(f"{pid}: evento '{A['evento']}' fora dos tres permitidos")
                    # A citacao vira um SELO clicavel na tela, entao ela precisa
                    # do artigo e do guardiao -- e os dois tem de bater com a
                    # fonte canonica, como ja vale para o texto da legenda.
                    dd = A.get("dados") or {}
                    num, gid = str(dd.get("artigo", "")), dd.get("guardiao")
                    checados += 1
                    if not num or not gid:
                        falha(f"{pid}: evento '{A['evento']}' sem dados.artigo ou dados.guardiao")
                    elif num not in arts:
                        falha(f"{pid}: citacao aponta Art. {num}, que nao existe em lgpd-arts.json")
                    elif arts[num]["guardiao"] != gid:
                        falha(f"{pid}: citacao diz que Art. {num} e de '{gid}', mas e de "
                              f"'{arts[num]['guardiao']}'")
                    elif gid not in gmx:
                        falha(f"{pid}: citacao aponta guardiao '{gid}', que nao existe")
                    elif P.get("guardiao") and gid != P["guardiao"]:
                        falha(f"{pid}: citacao e do guardiao '{gid}', mas o plano declara "
                              f"'{P['guardiao']}'")

            # --- legendas: limites e sobreposicao -------------------------
            legs = P.get("legendas") or []
            for i, L in enumerate(legs):
                checados += 1
                dur = L["ate"] - L["em"]
                linhas = L["txt"].split("\n")
                n = len(L["txt"].replace("\n", " "))
                if dur < DUR_MIN:
                    falha(f"{pid}: legenda {L['em']}-{L['ate']} dura {dur:.1f}s, "
                          f"minimo {DUR_MIN}s")
                if n / dur > CPS:
                    corte = L["txt"].rfind(" ", 0, len(L["txt"]) // 2 + 8)
                    sug = f" -- quebre em: {L['txt'][:corte]!r} + {L['txt'][corte + 1:]!r}" \
                          if corte > 0 else ""
                    falha(f"{pid}: legenda {L['em']}-{L['ate']} = {n / dur:.1f} cps, "
                          f"acima de {CPS}{sug}")
                if len(linhas) > LINHAS_MAX:
                    falha(f"{pid}: legenda {L['em']} tem {len(linhas)} linhas "
                          f"(max {LINHAS_MAX})")
                for ln in linhas:
                    if len(ln) > COLUNAS_MAX:
                        falha(f"{pid}: linha de {len(ln)} caracteres (max {COLUNAS_MAX}): {ln!r}")
                if L["ate"] > P["dur"] + 1e-6:
                    falha(f"{pid}: legenda termina em {L['ate']}s, alem do plano ({P['dur']}s)")
                if i and L["em"] < legs[i - 1]["ate"] - 1e-6:
                    falha(f"{pid}: legendas {legs[i - 1]['em']} e {L['em']} se sobrepoem")

                # --- QUEM FALA (CP-004) ----------------------------------
                # O audio deriva da legenda, e a legenda pode nomear o
                # ator. O campo e opcional: sem ele, fala o guardiao do
                # plano (ou o Narrador, em plano sem guardiao). Quando
                # existe, tem de apontar o ELENCO -- "dado" e prop, e
                # prop nao fala.
                if L.get("quem") is not None and L["quem"] not in d.get("elenco", {}):
                    falha(f"{pid}: legenda {L['em']}-{L['ate']} diz quem='{L['quem']}', "
                          f"que nao esta no elenco. O campo aponta uma chave de "
                          f"elenco, e o padrao vem de plano.guardiao.")

                # --- A CITACAO: o texto que o espectador le ---------------
                for m in re.finditer(r"Arts?\.\s*(\d+)", L["txt"]):
                    num = m.group(1)
                    checados += 1
                    if num not in arts:
                        falha(f"{pid}: legenda cita Art. {num}, que nao existe em "
                              f"lgpd-arts.json")
                        continue
                    dono = arts[num]["guardiao"]
                    if P.get("guardiao") and dono != P["guardiao"]:
                        falha(f"{pid}: legenda cita Art. {num}, que e de '{dono}', mas o "
                              f"plano declara guardiao '{P['guardiao']}'")
                    if int(num) not in (P.get("arts") or []):
                        falha(f"{pid}: legenda cita Art. {num}, que nao esta em "
                              f"arts={P.get('arts')}")
                    if L.get("ref") is not None and int(L["ref"]) != int(num):
                        falha(f"{pid}: legenda cita Art. {num} mas ref={L['ref']}")


            if legs and (P.get("arts") or []):
                checados += 1
                confere_contagem(pid, legs, P["arts"], arts)

            for numero in P.get("arts") or []:
                checados += 1
                chave = str(numero)
                if chave not in arts:
                    falha(f"{pid}: arts inclui {numero}, que nao existe em lgpd-arts.json")
                elif P.get("guardiao") and arts[chave]["guardiao"] != P["guardiao"]:
                    falha(f"{pid}: Art. {numero} e de '{arts[chave]['guardiao']}', "
                          f"plano declara '{P['guardiao']}'")

        # --- cobertura: opt-in, nao regra geral ---------------------------
        # Exigir os cinco guardioes em TODO roteiro era uma regra particular do
        # filme de 2 minutos disfarcada de geral: um filme de 40 segundos sobre
        # um artigo nao cobre cinco guardioes, e forca-lo a cobrir seria a
        # dispersao tematica que o proprio checklist manda evitar. Quem quer a
        # exigencia declara "cobertura": "completa".
        if d.get("cobertura") == "completa":
            for gid in gmx:
                checados += 1
                if gid not in vistos_guardiao:
                    falha(f"{nome}: declara cobertura completa, mas o guardiao "
                          f"'{gid}' nao aparece em nenhum plano")
        else:
            checados += 1
            if not vistos_guardiao:
                falha(f"{nome}: nenhum plano tem guardiao")

        # --- o roteiro em prosa e o dado dizem a mesma coisa ---------------
        md_path = FILMES / fid / "roteiro.md"
        if not md_path.exists():
            avisos.append(f"{nome}: sem roteiro em prosa em {md_path.relative_to(RAIZ)}")
        else:
            md = md_path.read_text(encoding="utf-8")
            cab = dict((m.group(1), int(m.group(2)))
                       for m in re.finditer(r"^### (p\d\d) — .+? · (\d+) s ·", md, re.M))
            legs_md = {}
            pid = None
            for linha in md.splitlines():
                m = re.match(r"^### (p\d\d) — ", linha)
                if m:
                    pid = m.group(1)
                    legs_md[pid] = []
                m = re.match(r"^\| \d+,\d – \d+,\d \| (.+?) \|$", linha)
                if m and pid:
                    legs_md[pid].append(m.group(1).replace("<br>", "\n"))
            for P in d["planos"]:
                checados += 1
                if P["id"] not in cab:
                    falha(f"{nome}: plano {P['id']} nao existe no roteiro em prosa")
                elif cab[P["id"]] != P["dur"]:
                    falha(f"{nome}/{P['id']}: dur {P['dur']}s no dado, "
                          f"{cab[P['id']]}s no roteiro em prosa")
                txts = [L["txt"] for L in P.get("legendas") or []]
                if legs_md.get(P["id"]) != txts:
                    falha(f"{nome}/{P['id']}: legendas divergem entre o roteiro em prosa "
                          f"e o .filme.js")

    valida_jogos(arts)

    print(f"  {checados} verificacoes em {len(filmes_existentes())} roteiro(s) "
          f"e {len(jogos_existentes())} jogo(s)")
    for a in avisos:
        print(f"  aviso: {a}")
    if falhas:
        for f in falhas:
            print(f"  ERRO: {f}", file=sys.stderr)
        print(f"\n  {len(falhas)} falha(s).", file=sys.stderr)
        return 1
    print("  roteiro consistente com a fonte canonica.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
