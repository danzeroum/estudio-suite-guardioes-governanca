#!/usr/bin/env python3
"""O roteador da segunda onda automática (CP-015) — a decisão do dono:

"N pela fração da janela móvel da frota; segunda onda automática quando
a primeira não tiver AVX-512; rerun humano deixa de ser o caminho de
volta."

Este script é o job que OLHA a primeira onda e decide se a segunda
acorda. Ele roda depois da onda 1 (e mesmo se a onda 1 tiver cópias
vermelhas — `if: always()`) e lê os vereditos.json baixados dos
artefatos identidade-onda1-*. A regra é UMA, sem exceção:

  SEGUNDA ONDA ACORDA  se e somente se TODAS as cópias esperadas da
                       onda 1 têm artefato legível, sem duplicatas, e
                       TODAS são classe avx2 — zero AVX-512 no sorteio.
                       É o caso do SORTEIO da frota: nenhuma cópia
                       decisiva caiu, nenhuma reprova, nenhuma divergiu
                       — o desenho manda tentar de novo, NO MESMO RUN,
                       sem humano no caminho.

  SEGUNDA ONDA NÃO ACORDA em qualquer outro estado: com alguma cópia
                       AVX-512 (identica, divergente ou nao-provou),
                       com artefato ausente/corrompido, com veredito
                       impróprio ou classe indeterminada. Esses casos não
                       são do sorteio: o AGREGADOR FINAL os nomeia
                       (DIVERGENCIA_AVX512 / AMOSTRA_ILEGIVEL / verde) —
                       a segunda onda não existe para mascarar cópia que
                       não provou; ilegível reprova, nunca vira outra
                       sorte.

Saídas: 0 a decisão foi tomada (segunda_onda true ou false — o job
escreve a saída e o rotear.json; o veredito do run é do AGREGADOR) ·
2 estrutural: nem ler a onda 1 foi possível (diretório de artefatos
ausente) — o run segue vermelho pelo agregador, que verá as cópias
sem artefato.

O rotear.json vai para --saida (artefato do job); a saída "segunda_onda"
vai para o $GITHUB_OUTPUT quando a variável existe — é ela que acorda o
job dublador-onda2 (if: needs.rotear.outputs.segunda_onda == 'true').
"""
import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

CAMPOS_OBRIGATORIOS = ("copia", "cpu", "classe", "prova", "veredito")
VEREDITOS_AVX512 = ("identica", "divergente", "nao-provou")
VEREDITOS_AVX2 = ("observacao",)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--artefatos", required=True,
                    help="diretório com os artefatos da ONDA 1 (um subdir "
                         "por artefato, como o download-artifact@v4 deixa)")
    ap.add_argument("--copias", required=True,
                    help="cópias esperadas da onda 1: JSON (saída do "
                         "planejar) ou lista separada por vírgula")
    ap.add_argument("--saida", default=None,
                    help="onde o rotear.json vai (default: --artefatos)")
    args = ap.parse_args()
    artefatos = Path(args.artefatos)
    saida = Path(args.saida) if args.saida else artefatos

    bruto = args.copias.strip()
    if bruto.startswith("["):
        esperadas = [str(c) for c in json.loads(bruto)]
    else:
        esperadas = [c.strip() for c in bruto.split(",") if c.strip()]
    if not esperadas:
        print("ERRO: nenhuma cópia esperada — o roteador julga uma onda, "
              "não uma cópia", file=sys.stderr)
        return 2

    # estrutural: sem o diretório de artefatos não há decisão POSSÍVEL —
    # o agregador verá as cópias sem artefato e reprovará; aqui o nome é
    # a ausência inteira
    if not artefatos.exists() or not any(artefatos.iterdir()):
        print(f"ERRO: ONDA_1_ILEGIVEL — o diretório de artefatos "
              f"{artefatos} não existe ou está vazio: nem ler a primeira "
              f"onda foi possível; sem rota, sem segunda onda, e o "
              f"agregador reprovará as {len(esperadas)} cópias como "
              f"SEM ARTEFATO", file=sys.stderr)
        return 2

    por_copia, duplicadas = {}, []
    corrompidos = []
    for sub in sorted(p for p in artefatos.iterdir() if p.is_dir()):
        v = sub / "veredito.json"
        if not v.exists():
            continue
        try:
            doc = json.loads(v.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            corrompidos.append(f"{sub.name}: veredito.json corrompido ({e})")
            continue
        copia = str(doc.get("copia", "")).strip()
        if not copia:
            continue
        if copia in por_copia:
            duplicadas.append(copia)
        por_copia[copia] = doc

    print("== ROTEADOR DA SEGUNDA ONDA (CP-015 — decisão do dono)")
    print(f"   cópias esperadas na onda 1: {len(esperadas)}")
    print(f"   vereditos legíveis: {len(por_copia)}"
          + (f" — corrompidos: {len(corrompidos)}" if corrompidos else "")
          + (f" — DUPLICADAS: {', '.join(sorted(duplicadas))}"
             if duplicadas else ""))

    # a regra: segunda onda ACORDA só para o sorteio limpo sem AVX-512
    avx512, problemas = [], []
    for c in esperadas:
        if c not in por_copia:
            problemas.append(f"{c}: SEM ARTEFATO na onda 1")
            continue
        doc = por_copia[c]
        falta = [k for k in CAMPOS_OBRIGATORIOS if not doc.get(k)]
        if falta:
            problemas.append(f"{c}: veredito.json sem os campos "
                             f"{', '.join(falta)}")
            continue
        classe = str(doc["classe"]).strip()
        veredito = str(doc["veredito"]).strip()
        if classe == "avx512":
            avx512.append(f"{c} ({veredito})")
        elif classe != "avx2":
            problemas.append(f"{c}: classe {classe!r} indeterminada")
        elif veredito not in VEREDITOS_AVX2:
            problemas.append(f"{c}: classe avx2 com veredito impróprio "
                             f"{veredito!r}")
    if duplicadas:
        problemas.append(f"cópias com artefato DUPLICADO: "
                         f"{', '.join(sorted(duplicadas))}")
    if corrompidos:
        problemas += corrompidos

    sorteio_limpo = not problemas and not avx512
    segunda = sorteio_limpo

    if segunda:
        motivo = (f"sorteio sem AVX-512: as {len(esperadas)} cópias da onda "
                  f"1 são TODAS avx2 (neutras por classe) — a segunda onda "
                  f"acorda NO MESMO RUN (sem rerun humano, CP-015); "
                  f"P(uma onda vazia) ~ 1,77% com N=13 e a fração da janela")
    elif avx512:
        motivo = (f"a onda 1 TEM AVX-512 ({'; '.join(avx512)}) — não há "
                  f"falta de amostra: o agregador decide sobre o que existe")
    else:
        motivo = ("a onda 1 tem estado que não é do sorteio ("
                  + "; ".join(problemas[:5])
                  + (f" e mais {len(problemas) - 5} problema(s)"
                     if len(problemas) > 5 else "")
                  + ") — a segunda onda não existe para mascarar cópia "
                  "ilegível: o agregador nomeia o vermelho")

    print(f"   SEGUNDA ONDA: {'ACORDA' if segunda else 'não acorda'}")
    print(f"   motivo: {motivo}")

    doc = {
        "prova": "rotear-segunda-onda",
        "cp": "CP-015",
        "copias_esperadas": esperadas,
        "vereditos_lidos": len(por_copia),
        "avx512_na_onda_1": avx512,
        "problemas": problemas,
        "segunda_onda": segunda,
        "motivo": motivo,
    }
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "rotear.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    gout = os.environ.get("GITHUB_OUTPUT")
    if gout:
        with open(gout, "a", encoding="utf-8") as f:
            f.write(f"segunda_onda={'true' if segunda else 'false'}\n")

    print(f"   rotear.json: {saida / 'rotear.json'}")
    print("   o veredito do run é do AGREGADOR — sobre as ondas declaradas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
