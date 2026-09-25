#!/usr/bin/env python3
"""Junta os agregados baixados no REGISTRO versionado (CP-015, passo 5).

O agregador publica a linha de cada execução no agregado.json (campo
"registro" — classe por cópia, ondas usadas, SEM_AMOSTRA sim/não). Este
script é o braço do CURADOR: varre um diretório de agregados baixados
(zips do workflow ou agregado.json já extraídos), valida cada entrada e
a acrescenta a harness/frota/execucoes-gate.json — o registro que só
cresce POR PR DE MANUTENÇÃO. Commit automático no main, JAMAIS: o que
este script escreve é o WORKING TREE do curador; virar histórico é
commit de PR, revisado pelo rito.

O que ele faz, na ordem:
  1. lê o registro versionado (o estado atual);
  2. varre --artefatos por agregado.json (direto) ou *.zip (lendo o
     agregado.json de dentro, como o download da API entrega);
  3. valida cada entrada do campo "registro" (run/tentativa/n/copias/
     avx512/ondas/sem_amostra coerentes entre si);
  4. acrescenta as entradas NOVAS (deduplicadas por run+tentativa — o
     mesmo run baixado duas vezes não entra duas vezes; o rerun de um
     run vira tentativa nova, entrada própria);
  5. reordena por quando (a ordem do registro é cronológica);
  6. REGRAVA o bloco "calculo" com ci/independencia.calcular_do_registro
     — o mesmo caminho do teste: o número do registro é recalculável,
     nunca afirmado;
  7. escreve o registro (a menos que --dry-run) e imprime o resumo:
     o que entrou, o que já estava, o que foi rejeitado e por quê.

Uso:
  ci/atualizar_registro_frota.py --artefatos DIR [--cp CP-015]
      [--registro harness/frota/execucoes-gate.json] [--dry-run]

Saídas: 0 registro atualizado (ou nada a fazer) · 2 nenhum agregado
legível no diretório — nada acontece com o registro.
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import importlib.util                      # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "independencia", RAIZ / "ci" / "independencia.py")
ind = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ind)

REGISTRO_DEFAULT = RAIZ / "harness" / "frota" / "execucoes-gate.json"


def _agregados_de(d: Path):
    """(caminho, doc) de cada agregado legível — zip ou json extraído."""
    achados = []
    if d.is_file():
        candidatos = [d]
    else:
        candidatos = sorted(p for p in d.rglob("*")
                            if p.suffix in (".zip", ".json"))
    for p in candidatos:
        try:
            if p.suffix == ".zip":
                with zipfile.ZipFile(p) as z:
                    nome = [n for n in z.namelist()
                            if n.endswith("agregado.json")]
                    if not nome:
                        continue
                    doc = json.loads(z.read(nome[0]).decode("utf-8"))
            else:
                if p.name != "agregado.json":
                    continue
                doc = json.loads(p.read_text(encoding="utf-8"))
        except (zipfile.BadZipFile, json.JSONDecodeError, OSError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("registro"), dict):
            achados.append((p, doc))
    return achados


def _validar(reg: dict) -> str | None:
    """None se a entrada é íntegra; senão, o motivo nomeado."""
    for campo in ("run", "tentativa", "n", "copias", "avx512",
                  "sem_amostra_decisiva"):
        if reg.get(campo) is None:
            return f"sem o campo {campo}"
    try:
        n = int(reg["n"])
        avx = int(reg["avx512"])
        tent = int(reg["tentativa"])
        ondas = int(reg.get("ondas", 1) or 1)
    except (TypeError, ValueError):
        return "n/avx512/tentativa/ondas não são inteiros"
    copias = reg.get("copias")
    if not isinstance(copias, dict) or len(copias) != n:
        return f"n={n} != {len(copias) if isinstance(copias, dict) else '?'} cópias"
    contadas = sum(1 for v in copias.values() if v == "avx512")
    if contadas != avx:
        return f"avx512={avx} != {contadas} contadas nas cópias"
    if n <= 0 or ondas <= 0 or n % ondas != 0:
        return f"n={n} não é múltiplo das ondas={ondas}"
    sem = bool(reg["sem_amostra_decisiva"])
    if sem != (avx == 0):
        return (f"sem_amostra_decisiva={sem} com avx512={avx} — "
                "incoerente (SEM_AMOSTRA é zero AVX-512 em todas as ondas)")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--artefatos", required=True,
                    help="diretório (ou arquivo) com agregado.json ou zips "
                         "agregado-frota-* baixados da API")
    ap.add_argument("--cp", default="CP-015",
                    help="a era/CP das entradas novas (default CP-015) — "
                         "rótulo do curador, não do workflow")
    ap.add_argument("--registro", default=str(REGISTRO_DEFAULT),
                    help="o registro versionado a atualizar")
    ap.add_argument("--dry-run", action="store_true",
                    help="calcular e imprimir sem escrever nada")
    args = ap.parse_args()

    raiz_arte = Path(args.artefatos)
    registro_path = Path(args.registro)
    doc = json.loads(registro_path.read_text(encoding="utf-8"))
    execucoes = doc["execucoes"]
    print("== ATUALIZAR O REGISTRO DA FROTA (CP-015, passo 5 — por PR de "
          "manutenção, commit automático jamais)")
    print(f"   registro: {registro_path} | {len(execucoes)} entradas")

    achados = _agregados_de(raiz_arte)
    if not achados:
        print(f"ERRO: nenhum agregado legível em {raiz_arte} — o registro "
              f"NÃO foi tocado", file=sys.stderr)
        return 2
    print(f"   agregados encontrados: {len(achados)}")

    ja = {(str(e["run"]), int(e["tentativa"])) for e in execucoes}
    novas, rejeitadas, duplicadas = [], [], []
    for p, agregado in achados:
        reg = agregado["registro"]
        run, tent = str(reg.get("run")), reg.get("tentativa")
        motivo = _validar(reg)
        if motivo:
            rejeitadas.append(f"{p.name} (run {run} t{tent}): {motivo}")
            continue
        if (run, int(tent)) in ja:
            duplicadas.append(f"run {run} t{tent} ({p.name})")
            continue
        entrada = {
            "cp": args.cp,
            "run": run,
            "tentativa": int(tent),
            "head": reg.get("head"),
            "evento": reg.get("evento"),
            "quando": reg.get("quando"),
            "n": int(reg["n"]),
            "ondas": int(reg.get("ondas", 1) or 1),
            "copias": reg["copias"],
            "avx512": int(reg["avx512"]),
            "sem_amostra_decisiva": bool(reg["sem_amostra_decisiva"]),
            "fonte": (f"agregado.json de {p.name} — "
                      + str(agregado.get("veredito", "?"))[:120]),
        }
        if reg.get("head_do_pr"):
            entrada["head_do_pr"] = reg["head_do_pr"]
        novas.append(entrada)
        ja.add((run, int(tent)))

    # rejeitadas com run/tentativa JÁ registrados são só ruído de
    # download repetido — o motivo importa para as novas
    execucoes_novo = execucoes + novas

    def _chave(e):
        # quando pode vir com "Z" ou "+00:00" — parse única para ordenar
        import datetime as _dt
        bruto = str(e.get("quando") or "")
        try:
            t = _dt.datetime.fromisoformat(bruto.replace("Z", "+00:00"))
        except ValueError:
            t = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)
        return (t, str(e.get("run")), int(e.get("tentativa", 1)))

    execucoes_novo.sort(key=_chave)

    calculo = ind.calcular_do_registro({"execucoes": execucoes_novo})
    doc["execucoes"] = execucoes_novo
    doc["calculo"] = calculo

    print(f"   entradas NOVAS: {len(novas)}")
    for e in novas:
        print(f"     + run {e['run']} t{e['tentativa']} | {e['quando']} | "
              f"n={e['n']} em {e['ondas']} onda(s) | avx512={e['avx512']} | "
              f"SEM_AMOSTRA={'sim' if e['sem_amostra_decisiva'] else 'não'}")
    print(f"   já registradas (ignoradas): {len(duplicadas)}"
          + (f" — {'; '.join(duplicadas)}" if duplicadas else ""))
    print(f"   rejeitadas por invalidez: {len(rejeitadas)}")
    for r in rejeitadas:
        print(f"     x {r}")
    j = calculo["janela"]
    print(f"   calculo regravado: janela J={j['j']} com "
          f"{j['execucoes_na_janela']} execuções"
          + (" (INCOMPLETA — usa todas)" if j["janela_incompleta"] else "")
          + f" | fração {j['fracao']} | N {j['n_recalculado']} "
          f"x lock {j['n_do_lock']} — "
          f"{'CONFORME' if j['n_conforme'] else 'N DESATUALIZADO'}")
    print(f"   taxa SEM_AMOSTRA: {calculo['taxa_sem_amostra']['k']}/"
          f"{calculo['taxa_sem_amostra']['n']} = "
          f"{calculo['taxa_sem_amostra']['valor']:.3%}")

    if args.dry_run:
        print("   --dry-run: o registro NÃO foi escrito")
        return 0
    registro_path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(f"   registro ESCRITO: {registro_path} — virar histórico é commit "
          f"de PR de manutenção (o rito decide, não o script)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
