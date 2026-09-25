#!/usr/bin/env python3
"""O agregador da prova por amostragem (CP-013) — o veredito da frota.

A decisão do dono (24/09/2026, saída (e)): o gate decide SÓ pela
identidade de bytes do PCM mixado em cópias com avx512f visível; as
cópias AVX2 saem cedo como observação; falta de amostra decisiva é
VERMELHO nomeado. Este script é o job final: lê o veredito.json de cada
cópia (um subdiretório por artefato, baixado pelo workflow) e decide o
run INTEIRO — nenhuma cópia decide sozinha, e nenhuma falta decide
calada.

CP-015 (decisão do dono 25/09/2026): o veredito é sobre AS ONDAS. Se a
primeira onda terminar com ZERO cópias AVX-512, o workflow roda uma
SEGUNDA onda automática de N cópias no mesmo run — e é AQUI que as duas
se encontram: o agregador lê os artefatos de TODAS as ondas (o campo
"onda" do veredito.json distingue onda-1/copia-3 de onda-2/copia-3) e
decide sobre o CONJUNTO. O rerun humano deixa de ser o caminho de volta:
o caminho automático já rodou dentro do próprio workflow.

CP-014 (passo 5): o agregado.json ganhou o campo REGISTRO — a entrada
daquela execução (classe por cópia, SEM_AMOSTRA sim/não, run/head)
pronta para o registro versionado harness/frota/execucoes-gate.json.
CP-015: a entrada ganha AS ONDAS (quantas rodaram, classes por cópia de
cada onda) — é dela que ci/atualizar_registro_frota.py alimenta o
registro para o PR de manutenção. Commit automático no main, jamais.

O VEREDITO do agregador (sobre todas as ondas declaradas):

  VERDE                     >= 1 cópia AVX-512 com PCM idêntico E zero
                            cópias AVX-512 divergentes E zero amostras
                            ilegíveis, em qualquer onda. (Uma basta: a
                            prova de bytes é exata — cópia extra é
                            sorte, não requisito.)
  DIVERGENCIA_AVX512        qualquer cópia AVX-512 divergente — com o
                            NOME da ONDA e da cópia e os números.
  SEM_AMOSTRA_DECISIVA      zero cópias AVX-512 EM TODAS AS ONDAS. Com
                            a segunda onda automática, só nasce após
                            DUAS ondas vazias (P(duas vazias) = 0,0315%
                            com N=13 e a fração da janela — o vermelho
                            ~50x mais raro); continua VERMELHO nomeado.
  AMOSTRA_ILEGIVEL          cópia esperada sem artefato, artefato
                            corrompido, classe indeterminada, cópia
                            AVX-512 que não provou, onda declarada que
                            não entregou, ou matrix que não veio do
                            lock. Reprova — nunca conta como neutra:
                            verde por omissão não existe em passo nenhum
                            desta suíte desde a CP-008.

As cópias avx2 (veredito "observacao") são NEUTRAS por desenho: a
classe delas não decide nada no gate — não contribuem para o verde, não
bloqueiam, não somam. Elas aparecem no resumo (onda, cópia, CPU, classe,
prova, veredito) porque a observação é publicada, não escondida.

O resumo vai para o GITHUB_STEP_SUMMARY (quando a variável existe) e
para o stdout; o agregado.json vai para --saida. Saídas: 0 verde · 1
vermelho nomeado (divergência, sem amostra ou amostra ilegível).
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

CAMPOS_OBRIGATORIOS = ("copia", "cpu", "classe", "prova", "veredito")

# o veredito de cópia que cada classe pode declarar (o contrato do passo
# "O veredito da cópia" do workflow — quem escreve fora disso é ilegível)
VEREDITOS_AVX512 = ("identica", "divergente", "nao-provou")
VEREDITOS_AVX2 = ("observacao",)


def _onda_do_doc(doc: dict) -> int:
    """A onda da cópia: campo 'onda' do veredito.json (CP-015); artefatos
    da era CP-013/014 não carregavam o campo — onda 1 por definição."""
    try:
        return int(str(doc.get("onda", 1)).strip() or 1)
    except (TypeError, ValueError):
        return 1


def ler_vereditos(artefatos: Path) -> dict:
    """{(onda, copia): (doc, sub)} de cada subdiretório com veredito.json."""
    por_copia = {}
    duplicadas = []
    if not artefatos.exists():
        return {}, []
    for sub in sorted(p for p in artefatos.iterdir() if p.is_dir()):
        v = sub / "veredito.json"
        if not v.exists():
            continue
        doc = json.loads(v.read_text(encoding="utf-8"))
        copia = str(doc.get("copia", "")).strip()
        if not copia:
            continue
        chave = (_onda_do_doc(doc), copia)
        if chave in por_copia:
            duplicadas.append(chave)
        por_copia[chave] = (doc, sub)
    return por_copia, duplicadas


def resumo_tabela(linhas: list) -> str:
    """A tabela do resumo do job: onda, cópia, CPU, classe, prova, veredito."""
    out = ["| onda | cópia | CPU | classe | prova | veredito |",
           "|---|---|---|---|---|---|"]
    for l in linhas:
        out.append(f"| {l.get('onda', 1)} | {l.get('copia', '?')} | "
                    f"{l.get('cpu', '?')} | {l.get('classe', '?')} | "
                    f"{l.get('prova', '?')} | {l.get('veredito', '?')} |")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--artefatos", required=True,
                    help="diretório com um subdir por artefato de cópia")
    ap.add_argument("--copias", required=True,
                    help="cópias esperadas POR ONDA: JSON (saída do planejar) "
                         "ou lista separada por vírgula")
    ap.add_argument("--ondas", default="1",
                    help="ondas declaradas deste run (ex.: '1' ou '1,2') — "
                         "a segunda existe quando o roteador acordou a onda "
                         "automática (CP-015); o veredito é sobre o conjunto")
    ap.add_argument("--conferir-n", action="store_true",
                    help="conferir o nº de cópias POR ONDA contra o "
                         "frota.amostragem do lock")
    ap.add_argument("--saida", default=None,
                    help="onde o agregado.json vai (default: --artefatos)")
    args = ap.parse_args()
    artefatos = Path(args.artefatos)
    saida = Path(args.saida) if args.saida else artefatos

    # as cópias esperadas — a matrix que o planejar declarou (e que veio
    # do lock: --conferir-n fecha o circulo, o N mora num lugar so)
    bruto = args.copias.strip()
    if bruto.startswith("["):
        esperadas_copia = [str(c) for c in json.loads(bruto)]
    else:
        esperadas_copia = [c.strip() for c in bruto.split(",") if c.strip()]
    if not esperadas_copia:
        print("ERRO: nenhuma cópia esperada — o agregador julga um run, "
              "não uma cópia", file=sys.stderr)
        return 2

    # as ondas declaradas (CP-015): a matrix se repete por onda
    try:
        ondas = [int(o) for o in str(args.ondas).split(",") if str(o).strip()]
    except ValueError:
        print(f"ERRO: --ondas ilegível ({args.ondas!r}) — use '1' ou '1,2'",
              file=sys.stderr)
        return 2
    ondas = ondas or [1]
    esperadas = [(o, c) for o in ondas for c in esperadas_copia]

    if args.conferir_n:
        from estudio_suite import voz
        fr = voz.frota()
        if "amostragem" not in fr:
            print("ERRO: voz.lock sem frota.amostragem — lock INCOMPLETO "
                  "(CP-013): a matrix não pode ser conferida; recusa, nunca "
                  "verde por omissão", file=sys.stderr)
            return 2
        n_lock = int(str(fr["amostragem"]).strip())
        if len(esperadas_copia) != n_lock or len(set(ondas)) != len(ondas):
            print(f"ERRO: AMOSTRA_ILEGIVEL — a matrix declarou "
                  f"{len(esperadas_copia)} cópias em {len(set(ondas))} "
                  f"onda(s) e o lock ancora N={n_lock} (bloco frota, "
                  f"recalculado da janela — CP-015): o tamanho da amostra "
                  f"mora no lock, não no YAML; recusa nomeada", file=sys.stderr)
            return 1

    try:
        por_copia, duplicadas = ler_vereditos(artefatos)
    except json.JSONDecodeError as e:
        print(f"ERRO: AMOSTRA_ILEGIVEL — artefato corrompido (veredito.json "
              f"ilegível: {e})", file=sys.stderr)
        return 1

    print("== AGREGADOR DA PROVA POR AMOSTRAGEM (CP-013 — decisão (e) do dono;"
          " CP-015 — veredito sobre as ondas)")
    print(f"   cópias esperadas: {len(esperadas_copia)} por onda x "
          f"{len(ondas)} onda(s) ({', '.join('onda-' + str(o) for o in ondas)})"
          + (", conferidas contra o lock" if args.conferir_n else "") + ")")
    print(f"   artefatos lidos:  {len(por_copia)}"
          + (f" — DUPLICADAS: {', '.join(f'onda-{o}/{c}' for o, c in sorted(duplicadas))}"
             if duplicadas else ""))

    # o NOME público da cópia: "onda-N/copia-M" quando há mais de uma
    # onda (o agregador distingue), e a chave simples "copia-M" na onda
    # única — o formato da era CP-013/014 segue legível no agregado
    def nome_de(onda, copia):
        return (f"onda-{onda}/{copia}" if len(ondas) > 1 else copia)

    identicas, divergentes, observacoes, ilegiveis = [], [], [], []
    problemas = []
    if duplicadas:
        ilegiveis += [nome_de(o, c) for o, c in duplicadas]
        problemas.append(f"cópias com artefato DUPLICADO (retry?): "
                         f"{', '.join(sorted(nome_de(o, c) for o, c in duplicadas))}")
    for chave in esperadas:
        onda, copia = chave
        nome = nome_de(onda, copia)
        if (onda, copia) not in por_copia:
            ilegiveis.append(nome)
            problemas.append(f"{nome}: SEM ARTEFATO — a cópia esperada não "
                             f"publicou veredito (onda não rodou? cancelada "
                             f"antes de subir?)")
            continue
        doc, sub = por_copia[(onda, copia)]
        falta = [c for c in CAMPOS_OBRIGATORIOS if not doc.get(c)]
        if falta:
            ilegiveis.append(nome)
            problemas.append(f"{nome}: veredito.json sem os campos "
                             f"{', '.join(falta)} — amostra ilegível")
            continue
        if _onda_do_doc(doc) != onda:
            ilegiveis.append(nome)
            problemas.append(f"{nome}: veredito.json declara onda "
                             f"{_onda_do_doc(doc)} — amostra ilegível")
            continue
        classe = str(doc["classe"]).strip()
        veredito = str(doc["veredito"]).strip()
        if classe == "avx512":
            if veredito not in VEREDITOS_AVX512:
                ilegiveis.append(nome)
                problemas.append(f"{nome}: classe avx512 com veredito "
                                 f"impróprio {veredito!r} — amostra ilegível")
            elif veredito == "identica":
                identicas.append(nome)
            elif veredito == "divergente":
                divergentes.append(nome)
                problemas.append(
                    f"{nome}: DIVERGÊNCIA AVX-512 — {doc.get('detalhe', '?')}")
            else:  # nao-provou
                ilegiveis.append(nome)
                problemas.append(
                    f"{nome}: cópia AVX-512 que NÃO PROVOU — "
                    f"{doc.get('detalhe', 'sem detalhe')}; nunca conta como "
                    f"neutra: a segunda onda só acorda para o sorteio sem "
                    f"AVX-512, não para a prova que não rodou")
        elif classe == "avx2":
            if veredito not in VEREDITOS_AVX2:
                ilegiveis.append(nome)
                problemas.append(f"{nome}: classe avx2 com veredito "
                                 f"impróprio {veredito!r} — amostra ilegível")
            else:
                observacoes.append(nome)
        else:
            ilegiveis.append(nome)
            problemas.append(f"{nome}: classe {classe!r} (indeterminada?) — "
                             f"não prova, não observa, não é neutra")

    # cópias além das esperadas (artefato de onda não declarada) — o
    # agregador não julga o que ninguém declarou, mas APONTA: run com
    # artefato órfão é run com estado confuso
    orfaos = sorted(set(por_copia) - set(esperadas))
    if orfaos:
        problemas.append("artefatos de cópias FORA das ondas declaradas: "
                         f"{', '.join(nome_de(o, c) for o, c in orfaos)}"
                         " — o agregador não julga cópia não declarada")
        print(f"   ATENÇÃO: artefatos de cópias FORA das ondas declaradas: "
              f"{', '.join(nome_de(o, c) for o, c in orfaos)} — o agregador "
              f"não julga cópia não declarada (estado confuso do run)")

    avx512_total = 0
    for chave in esperadas:
        if chave in por_copia and str(
                por_copia[chave][0].get("classe", "")).strip() == "avx512":
            avx512_total += 1

    # ---- o veredito -----------------------------------------------------
    # Prioridade das manchetes: a divergência medida é o achado mais grave;
    # depois a amostra que não se pode ler (NUNCA conta como neutra — e
    # nunca conta como SEM_AMOSTRA: cópia sem artefato não é sorteio da
    # frota, é run que não entregou; contá-la como SEM_AMOSTRA poluiria a
    # estatística do registro com evento que não foi do sorteio); depois a
    # falta de amostra decisiva — zero AVX-512 EM TODAS as ondas, com
    # todas as cópias legíveis: o sorteio aconteceu e não trouxe decisiva.
    # Com a segunda onda automática, isso só nasce após DUAS ondas vazias.
    # O verde exige >= 1 identica, zero divergente, zero ilegivel.
    causas_div = [p for p in problemas if p.split(":")[0] in divergentes]
    causas_ilegivel = [p for p in problemas
                       if p.split(":")[0] not in divergentes
                       and not p.startswith("cópias com artefato")
                       and not p.startswith("artefatos de cópias FORA")]
    if duplicadas:
        causas_ilegivel.insert(0, problemas[0])

    if divergentes:
        veredito = "DIVERGENCIA_AVX512"
        causas = causas_div + causas_ilegivel
    elif causas_ilegivel:
        veredito = "AMOSTRA_ILEGIVEL"
        causas = causas_ilegivel
    elif avx512_total == 0:
        veredito = "SEM_AMOSTRA_DECISIVA"
        if len(ondas) > 1:
            causas = [f"zero cópias AVX-512 nas DUAS ondas ({len(observacoes)} "
                      f"cópias avx2 publicaram observação) — a segunda onda "
                      f"automática já rodou (CP-015) e o sorteio também não "
                      f"trouxe AVX-512: o caminho de volta é revisar o N da "
                      f"janela (a frota mudou de mistura) ou o rerun"]
        else:
            causas = [f"zero cópias AVX-512 na onda única ({len(observacoes)} "
                      f"cópias avx2 publicaram observação) — o roteador devia "
                      f"ter acordado a segunda onda automática (CP-015) e ela "
                      f"não está neste veredito: o caminho de volta é o RERUN "
                      f"com o roteador no lugar"]
    elif identicas:
        veredito = "verde"
        causas = [f"{len(identicas)} cópia(s) AVX-512 com PCM idêntico, "
                  f"zero divergentes, zero ilegíveis "
                  f"({len(observacoes)} avx2 em observação)"]
    else:
        veredito = "AMOSTRA_ILEGIVEL"
        causas = ["cópias AVX-512 presentes sem veredito legível"]

    frase = " | ".join(c for c in causas if c) or "sem causa nomeada"
    veredito_final = f"{veredito} — {frase}"

    # ---- o resumo (onda, cópia, CPU, classe, prova, veredito) ------------
    linhas = []
    for chave in esperadas:
        onda, copia = chave
        if chave in por_copia:
            d = dict(por_copia[chave][0])
            d.setdefault("onda", onda)
            linhas.append(d)
        else:
            linhas.append({"onda": onda, "copia": copia, "cpu": "—",
                           "classe": "—", "prova": "—",
                           "veredito": "SEM ARTEFATO"})
    tabela = resumo_tabela(linhas)
    resumo = (
        "## A prova por amostragem da frota (CP-013; ondas CP-015)\n\n"
        f"**Veredito: {veredito_final}**\n\n"
        + tabela + "\n\n"
        + (f"- cópias AVX-512 idênticas: {', '.join(identicas) or '—'}\n"
           f"- cópias AVX-512 divergentes: {', '.join(divergentes) or '—'}\n"
           f"- cópias avx2 (observação, neutras): "
           f"{', '.join(observacoes) or '—'}\n"
           f"- amostras ilegíveis: {', '.join(ilegiveis) or '—'}\n"))
    print()
    print(resumo)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(Path(summ), "a", encoding="utf-8") as f:
            f.write(resumo + "\n")

    # ---- o registro: classes por cópia por onda (CP-014/CP-015) ---------
    # 1 onda: chaves simples (copia-N) — o formato da era CP-013/014, o
    # registro antigo continua legível; 2 ondas: chaves onda-N/copia-N.
    copias_reg = {}
    for onda, copia in esperadas:
        chave = nome_de(onda, copia)
        copias_reg[chave] = (str(por_copia[(onda, copia)][0].get("classe", "?"))
                             if (onda, copia) in por_copia else "sem-artefato")

    doc = {
        "prova": "agregador-frota",
        "cp": "CP-013",
        "copias_esperadas": esperadas_copia,
        "ondas": ondas,
        "conferiu_n_do_lock": bool(args.conferir_n),
        "identicas_avx512": identicas,
        "divergentes_avx512": divergentes,
        "observacoes_avx2": observacoes,
        "ilegiveis": ilegiveis,
        "veredito": veredito_final,
        "resumo_markdown": resumo,
        "copias": linhas,
        # CP-014 (passo 5) / CP-015 (ondas): a entrada de REGISTRO desta
        # execução — pronta para harness/frota/execucoes-gate.json. O
        # curador a acrescenta por PR de manutenção
        # (ci/atualizar_registro_frota.py junta os agregados baixados);
        # commit automático no main, JAMAIS. A independência das cópias e
        # o N da janela são recalculados de lá por ci/independencia.py.
        "registro": {
            "run": os.environ.get("GITHUB_RUN_ID"),
            "tentativa": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "head": (os.environ.get("GITHUB_SHA") or "")[:8] or None,
            "head_do_pr": ((os.environ.get("GITHUB_PR_HEAD") or "")[:8]
                           or None),
            "evento": os.environ.get("GITHUB_EVENT_NAME"),
            "quando": datetime.datetime.now(
                datetime.timezone.utc).isoformat(timespec="seconds"),
            "n": len(esperadas),
            "ondas": len(ondas),
            "copias": copias_reg,
            "avx512": avx512_total,
            "sem_amostra_decisiva": veredito == "SEM_AMOSTRA_DECISIVA",
            "fonte": "agregado.json desta execução — a entrada entra no "
                     "registro por PR de manutenção (CP-014/CP-015, "
                     "ci/atualizar_registro_frota.py)",
        },
    }
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "agregado.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"== VEREDITO: {veredito_final}")
    print(f"   agregado: {saida / 'agregado.json'}")
    print("   registro (CP-014/CP-015): a entrada desta execução vai no campo "
          "registro do agregado.json — o curador a acrescenta a "
          "harness/frota/execucoes-gate.json por PR de manutenção "
          "(ci/atualizar_registro_frota.py); commit automático no main, "
          "jamais")
    return 0 if veredito == "verde" else 1


if __name__ == "__main__":
    sys.exit(main())
