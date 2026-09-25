#!/usr/bin/env python3
"""Junta os artefatos do dispatch observar_avx2 na EVIDÊNCIA versionada
(CP-016, proposta — passo 1 do plano).

Cada cópia avx2 sorteada pelo dispatch publica observacao-avx2-<copia>-
run<id>.zip com o observacao-avx2.json DELA (deltas por fala — CP-014 —
e, desde a CP-016, o sha256 do PCM mixado por filme: regenerado_avx2 e
ancora_commitada). Este script é o braço do curador: varre um diretório
com os zips (ou jsons extraídos) baixados da API, agrupa por RUN (as
cópias de um mesmo dispatch são uma EXECUÇÃO), deduplica e escreve
harness/frota/observacao-avx2.json — a evidência versionada que
ci/determinismo_avx2.py lê para o veredito. Sem gate, sem teto: a
pergunta é de verificação (determinismo na classe); a decisão (virar
âncora) é do dono.

Uso:
  ci/atualizar_observacao_avx2.py --artefatos DIR [--evidencia
      harness/frota/observacao-avx2.json] [--dry-run]

Saídas: 0 evidência atualizada (ou nada a fazer) · 2 nenhum artefato
legível — nada acontece com a evidência.
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

EVIDENCIA_DEFAULT = RAIZ / "harness" / "frota" / "observacao-avx2.json"


def _observacoes_de(d: Path):
    """(caminho, doc) de cada observacao-avx2.json legível — zip ou solto."""
    achados = []
    candidatos = ([d] if d.is_file()
                  else sorted(p for p in d.rglob("*")
                              if p.suffix in (".zip", ".json")))
    for p in candidatos:
        try:
            if p.suffix == ".zip":
                with zipfile.ZipFile(p) as z:
                    nome = [n for n in z.namelist()
                            if n.endswith("observacao-avx2.json")]
                    if not nome:
                        continue
                    doc = json.loads(z.read(nome[0]).decode("utf-8"))
            else:
                if p.name != "observacao-avx2.json":
                    continue
                doc = json.loads(p.read_text(encoding="utf-8"))
        except (zipfile.BadZipFile, json.JSONDecodeError, OSError):
            continue
        if isinstance(doc, dict) and doc.get("prova") == "observacao-avx2":
            achados.append((p, doc))
    return achados


def _copia_de(doc: dict, fonte: str) -> dict:
    """a entrada desta cópia: modelo, status e os hashes por filme."""
    filmes = {}
    for f in doc.get("filmes", []):
        fid = f.get("filme")
        hashes = f.get("hash_pcm_mixado") or {}
        filmes[fid] = {
            "regenerado_avx2": hashes.get("regenerado_avx2"),
            "ancora_commitada": hashes.get("ancora_commitada"),
        }
    return {
        "copia": doc.get("copia"),
        "classe": doc.get("classe"),
        "cpu": doc.get("cpu", "ilegivel"),
        "status": doc.get("status", "?"),
        "filmes": filmes,
        "fonte": fonte,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--artefatos", required=True,
                    help="diretório (ou arquivo) com observacao-avx2-*.zip "
                         "baixados da API ou observacao-avx2.json extraídos")
    ap.add_argument("--evidencia", default=str(EVIDENCIA_DEFAULT),
                    help="o arquivo de evidência versionado a atualizar")
    ap.add_argument("--dry-run", action="store_true",
                    help="calcular e imprimir sem escrever nada")
    args = ap.parse_args()

    ev_path = Path(args.evidencia)
    if ev_path.exists():
        ev = json.loads(ev_path.read_text(encoding="utf-8"))
    else:
        ev = {"$schema": "estudio-suite/frota-observacao-avx2@1",
              "descricao": ("Evidência do dispatch observar_avx2 (CP-016, "
                            "proposta): uma entrada por EXECUÇÃO (run), as "
                            "cópias avx2 que observaram com o modelo de CPU e "
                            "o sha256 do PCM mixado por filme (regenerado_avx2 "
                            "e ancora_commitada). É daqui que "
                            "ci/determinismo_avx2.py recalcula o veredito — "
                            "nada é afirmado."),
              "como_cresce": ("ci/atualizar_observacao_avx2.py junta os "
                              "artefatos baixados; cresce por PR, sem commit "
                              "automático no main"),
              "execucoes": []}

    print("== ATUALIZAR A EVIDÊNCIA observar_avx2 (CP-016, proposta)")
    print(f"   evidência: {ev_path} | {len(ev['execucoes'])} execuções")

    achados = _observacoes_de(Path(args.artefatos))
    if not achados:
        print(f"ERRO: nenhum observacao-avx2.json legível em "
              f"{args.artefatos} — a evidência NÃO foi tocada",
              file=sys.stderr)
        return 2
    print(f"   artefatos de cópia encontrados: {len(achados)}")

    ja = {(str(e["run"]), str(c["copia"]))
          for e in ev["execucoes"] for c in e.get("copias", [])}
    runs_por_id = {str(e["run"]): e for e in ev["execucoes"]}
    novas_copias, duplicadas, invalidas = 0, 0, 0
    for p, doc in achados:
        run = str(doc.get("run_id") or "?")
        copia = doc.get("copia")
        if not copia or run == "?":
            invalidas += 1
            print(f"     x {p.name}: sem run_id/copia — ignorado")
            continue
        if (run, copia) in ja:
            duplicadas += 1
            continue
        if str(doc.get("classe")) != "avx2":
            # o dispatch publica saída-cedo para avx512 em outro artefato;
            # um observacao-avx2.json de outra classe seria incoerente
            invalidas += 1
            print(f"     x {p.name}: classe {doc.get('classe')!r} (não avx2) "
                  f"— ignorado")
            continue
        entrada = _copia_de(doc, p.name)
        if not entrada["filmes"]:
            invalidas += 1
            print(f"     x {p.name}: sem filmes com hash — ignorado")
            continue
        if run not in runs_por_id:
            nova_exec = {"run": run, "copias": []}
            ev["execucoes"].append(nova_exec)
            runs_por_id[run] = nova_exec
        runs_por_id[run]["copias"].append(entrada)
        # quando do run não está no artefato da cópia — o curador anota
        runs_por_id[run].setdefault("quando", None)
        runs_por_id[run].setdefault("head", None)
        ja.add((run, copia))
        novas_copias += 1

    def _chave_exec(e):
        return str(e.get("quando") or "")  # runs sem quando ficam na frente

    ev["execucoes"].sort(key=_chave_exec)

    modelos = sorted({c.get("cpu") for e in ev["execucoes"]
                      for c in e.get("copias", [])})
    print(f"   cópias NOVAS: {novas_copias} | já registradas: {duplicadas} "
          f"| inválidas: {invalidas}")
    print(f"   execuções na evidência: {len(ev['execucoes'])} | modelos de "
          f"CPU avx2 observados: {len(modelos)}")
    for m in modelos:
        n = sum(1 for e in ev["execucoes"] for c in e.get("copias", [])
                if c.get("cpu") == m)
        print(f"     {n:2d}x {m}")

    if args.dry_run:
        print("   --dry-run: a evidência NÃO foi escrita")
        return 0
    ev_path.write_text(
        json.dumps(ev, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print(f"   evidência ESCRITA: {ev_path} — virar histórico é commit de PR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
