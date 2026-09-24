#!/usr/bin/env python3
"""O agregador da prova por amostragem (CP-013) — o veredito da frota.

A decisão do dono (24/09/2026, saída (e)): o gate decide SÓ pela
identidade de bytes do PCM mixado em cópias com avx512f visível; as
cópias AVX2 saem cedo como observação; falta de amostra decisiva é
VERMELHO nomeado. Este script é o job final: lê o veredito.json de cada
cópia (um subdiretório por artefato, baixado pelo workflow) e decide o
run INTEIRO — nenhuma cópia decide sozinha, e nenhuma falta decide
calada.

O VEREDITO do agregador:

  VERDE                     >= 1 cópia AVX-512 com PCM idêntico E zero
                            cópias AVX-512 divergentes E zero amostras
                            ilegíveis. (Uma basta: a prova de bytes é
                            exata — cópia extra é sorte, não requisito.)
  DIVERGENCIA_AVX512        qualquer cópia AVX-512 divergente — com o
                            NOME da cópia e os números. A frota medida
                            (CP-011: 4/4; CP-012: 4/4) entrega o PCM
                            igual entre Intel e AMD-avx512: divergência
                            aqui é sintese divergente.
  SEM_AMOSTRA_DECISIVA      zero cópias AVX-512 no disparo. VERMELHO
                            nomeado — o caminho de volta é o RERUN (o N
                            do lock foi escolhido para P(zero) <= 2%).
                            A parada da CP só dispara se repetir 3
                            disparos SEGUIDOS (a frota teria mudado).
  AMOSTRA_ILEGIVEL          cópia esperada sem artefato, artefato
                            corrompido, classe indeterminada, cópia
                            AVX-512 que não provou (build falhou, prova
                            não rodou) ou matrix que não veio do lock.
                            Reprova — nunca conta como neutra: verde por
                            omissão não existe em passo nenhum desta
                            suíte desde a CP-008.

As cópias avx2 (veredito "observacao") são NEUTRAS por desenho: a
classe delas não decide nada no gate — não contribuem para o verde, não
bloqueiam, não somam. Elas aparecem no resumo (cópia, CPU, classe,
prova, veredito) porque a observação é publicada, não escondida.

O resumo vai para o GITHUB_STEP_SUMMARY (quando a variável existe) e
para o stdout; o agregado.json vai para --saida. Saídas: 0 verde · 1
vermelho nomeado (divergência, sem amostra ou amostra ilegível).
"""
import argparse
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


def ler_vereditos(artefatos: Path) -> dict:
    """{copia: (doc, sub)} de cada subdiretório com veredito.json."""
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
        if copia in por_copia:
            duplicadas.append(copia)
        por_copia[copia] = (doc, sub)
    return por_copia, duplicadas


def resumo_tabela(linhas: list) -> str:
    """A tabela do resumo do job: cópia, CPU, classe, prova, veredito."""
    out = ["| cópia | CPU | classe | prova | veredito |",
           "|---|---|---|---|---|"]
    for l in linhas:
        out.append(f"| {l.get('copia', '?')} | {l.get('cpu', '?')} | "
                    f"{l.get('classe', '?')} | {l.get('prova', '?')} | "
                    f"{l.get('veredito', '?')} |")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--artefatos", required=True,
                    help="diretório com um subdir por artefato de cópia")
    ap.add_argument("--copias", required=True,
                    help="cópias esperadas: JSON (saída do planejar) ou lista separada por vírgula")
    ap.add_argument("--conferir-n", action="store_true",
                    help="conferir o nº de cópias contra o frota.amostragem do lock")
    ap.add_argument("--saida", default=None,
                    help="onde o agregado.json vai (default: --artefatos)")
    args = ap.parse_args()
    artefatos = Path(args.artefatos)
    saida = Path(args.saida) if args.saida else artefatos

    # as cópias esperadas — a matrix que o planejar declarou (e que veio
    # do lock: --conferir-n fecha o circulo, o N mora num lugar so)
    bruto = args.copias.strip()
    if bruto.startswith("["):
        esperadas = [str(c) for c in json.loads(bruto)]
    else:
        esperadas = [c.strip() for c in bruto.split(",") if c.strip()]
    if not esperadas:
        print("ERRO: nenhuma cópia esperada — o agregador julga um run, "
              "não uma cópia", file=sys.stderr)
        return 2

    if args.conferir_n:
        from estudio_suite import voz
        fr = voz.frota()
        if "amostragem" not in fr:
            print("ERRO: voz.lock sem frota.amostragem — lock INCOMPLETO "
                  "(CP-013): a matrix não pode ser conferida; recusa, nunca "
                  "verde por omissão", file=sys.stderr)
            return 2
        n_lock = int(str(fr["amostragem"]).strip())
        if len(esperadas) != n_lock:
            print(f"ERRO: AMOSTRA_ILEGIVEL — a matrix declarou "
                  f"{len(esperadas)} cópias e o lock ancora N={n_lock} "
                  f"(bloco frota): o tamanho da amostra mora no lock, não "
                  f"no YAML; recusa nomeada", file=sys.stderr)
            return 1

    try:
        por_copia, duplicadas = ler_vereditos(artefatos)
    except json.JSONDecodeError as e:
        print(f"ERRO: AMOSTRA_ILEGIVEL — artefato corrompido (veredito.json "
              f"ilegível: {e})", file=sys.stderr)
        return 1

    print("== AGREGADOR DA PROVA POR AMOSTRAGEM (CP-013 — decisão (e) do dono)")
    print(f"   cópias esperadas: {len(esperadas)} (matrix do planejar"
          + (", conferida contra o lock" if args.conferir_n else "") + ")")
    print(f"   artefatos lidos:  {len(por_copia)}"
          + (f" — DUPLICADAS: {', '.join(duplicadas)}" if duplicadas else ""))

    identicas, divergentes, observacoes, ilegiveis = [], [], [], []
    problemas = []
    if duplicadas:
        ilegiveis += duplicadas
        problemas.append(f"cópias com artefato DUPLICADO (retry?): "
                         f"{', '.join(sorted(duplicadas))}")
    for copia in esperadas:
        if copia not in por_copia:
            ilegiveis.append(copia)
            problemas.append(f"{copia}: SEM ARTEFATO — a cópia esperada não "
                             f"publicou veredito (cancelada antes de subir?)")
            continue
        doc, sub = por_copia[copia]
        falta = [c for c in CAMPOS_OBRIGATORIOS if not doc.get(c)]
        if falta:
            ilegiveis.append(copia)
            problemas.append(f"{copia}: veredito.json sem os campos "
                             f"{', '.join(falta)} — amostra ilegível")
            continue
        classe = str(doc["classe"]).strip()
        veredito = str(doc["veredito"]).strip()
        if classe == "avx512":
            if veredito not in VEREDITOS_AVX512:
                ilegiveis.append(copia)
                problemas.append(f"{copia}: classe avx512 com veredito "
                                 f"impróprio {veredito!r} — amostra ilegível")
            elif veredito == "identica":
                identicas.append(copia)
            elif veredito == "divergente":
                divergentes.append(copia)
                problemas.append(
                    f"{copia}: DIVERGÊNCIA AVX-512 — {doc.get('detalhe', '?')}")
            else:  # nao-provou
                ilegiveis.append(copia)
                problemas.append(
                    f"{copia}: cópia AVX-512 que NÃO PROVOU — "
                    f"{doc.get('detalhe', 'sem detalhe')}; nunca conta como "
                    f"neutra: o rerun é o caminho de volta")
        elif classe == "avx2":
            if veredito not in VEREDITOS_AVX2:
                ilegiveis.append(copia)
                problemas.append(f"{copia}: classe avx2 com veredito "
                                 f"impróprio {veredito!r} — amostra ilegível")
            else:
                observacoes.append(copia)
        else:
            ilegiveis.append(copia)
            problemas.append(f"{copia}: classe {classe!r} (indeterminada?) — "
                             f"não prova, não observa, não é neutra")

    avx512_total = 0
    for copia in esperadas:
        if copia in por_copia and str(
                por_copia[copia][0].get("classe", "")).strip() == "avx512":
            avx512_total += 1

    # ---- o veredito -----------------------------------------------------
    # Prioridade das manchetes: a divergência medida é o achado mais grave;
    # depois a amostra que não se pode ler (nunca neutra); depois a falta
    # de amostra decisiva (zero avx512 — rerun). O verde exige >= 1
    # identica, zero divergente, zero ilegivel.
    causas_div = [p for p in problemas if p.split(":")[0] in divergentes]
    causas_ilegivel = [p for p in problemas
                       if p.split(":")[0] not in divergentes
                       and not p.startswith("cópias com artefato")]
    if duplicadas:
        causas_ilegivel.insert(0, problemas[0])

    if divergentes:
        veredito = "DIVERGENCIA_AVX512"
        causas = causas_div + causas_ilegivel
    elif causas_ilegivel:
        veredito = ("SEM_AMOSTRA_DECISIVA" if avx512_total == 0
                    else "AMOSTRA_ILEGIVEL")
        causas = causas_ilegivel
    elif avx512_total == 0:
        veredito = "SEM_AMOSTRA_DECISIVA"
        causas = [f"zero cópias AVX-512 no disparo ({len(observacoes)} "
                  f"cópias avx2 publicaram observação) — o N do lock foi "
                  f"escolhido para P(zero) <= 2%: o caminho de volta é o "
                  f"RERUN"]
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

    # ---- o resumo (cópia, CPU, classe, prova, veredito) -----------------
    linhas = []
    for copia in esperadas:
        if copia in por_copia:
            linhas.append(por_copia[copia][0])
        else:
            linhas.append({"copia": copia, "cpu": "—", "classe": "—",
                           "prova": "—", "veredito": "SEM ARTEFATO"})
    tabela = resumo_tabela(linhas)
    resumo = (
        "## A prova por amostragem da frota (CP-013)\n\n"
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

    doc = {
        "prova": "agregador-frota",
        "cp": "CP-013",
        "copias_esperadas": esperadas,
        "conferiu_n_do_lock": bool(args.conferir_n),
        "identicas_avx512": identicas,
        "divergentes_avx512": divergentes,
        "observacoes_avx2": observacoes,
        "ilegiveis": ilegiveis,
        "veredito": veredito_final,
        "resumo_markdown": resumo,
        "copias": linhas,
    }
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "agregado.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"== VEREDITO: {veredito_final}")
    print(f"   agregado: {saida / 'agregado.json'}")
    return 0 if veredito == "verde" else 1


if __name__ == "__main__":
    sys.exit(main())
