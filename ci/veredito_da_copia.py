#!/usr/bin/env python3
"""O veredito e a identidade da cópia, com RÓTULOS ÚNICOS (CP-014).

A diretiva do dono (25/09/2026): "corrigir a observação AVX2 e os rótulos
do identidade.json" — cada campo do identidade.json passa a ter UM estado
nomeado, nunca texto ambíguo. O defeito medido que esta CP corrige: o
identidade.json da CP-013 carregava "copia avx2 (sem build, CP-013) ou
DIVERGENTE" (dois estados numa string com "ou"), "NAO RODOU", "nao
medida", "NAO REGISTRADO" — rótulos que não dizem se o campo foi medido,
falhou ou não se aplica àquela classe.

O ESQUEMA (o contrato desta CP):

  medido:<valor>            o campo foi medido NESTA cópia e o valor segue
                            os dois pontos
  falhou:<motivo>           o campo devia ser medido e a medição falhou,
                            com o motivo NOMEADO
  nao_aplicavel:<motivo>    o campo não se aplica a esta cópia, com o
                            motivo nomeado — a cópia avx2 declara os
                            campos de SÍNTESE como
                            "nao_aplicavel:classe_avx2"

CAMPOS DE SÍNTESE (exigem build/dublagem; na cópia avx2 do gate são todos
"nao_aplicavel:classe_avx2", exatamente como a aceite da CP-014 pede):
threads.efetivas_da_sessao, threads.gravadas_no_audio_json,
threads.omp_da_imagem, prova.determinismo_interno e
prova.veredito_da_prova_por_classe.

Campos de identidade da máquina (cpu.*, nproc, cgroup, classe medida) são
fatos do lscpu, sempre presentes quando o artefato existe — a etapa de
identidade reprova a cópia antes de qualquer veredito se o lscpu falhar,
 então não carregam estado alternativo. Os campos de LEITURA do lock
(threads da ancora, classe da ancora, teto do codec) são lidos AQUI do
voz.lock pela fonte única (estudio_suite/voz.py): medido ou
falhou:<motivo>, para toda classe.

O que este script escreve (o contrato do agregador continua o da CP-013):
  veredito.json    cópia, run, cpu, classe, prova, veredito, detalhe e
                   números — avx512 decide pela prova da CP-012; avx2 é
                   "observacao" (neutra; a observação de verdade é o
                   dispatch manual observar_avx2, não mais o gate)
  identidade.json  a identidade rotulada da CP-014

RÓTULO AMBÍGUO NÃO PUBLICA: se qualquer valor de qualquer campo contém a
palavra "ou" (o "ou" de ambiguidade, não o de substantivo), o script
RECUSA (saída 2, ROTULO_AMBIGUO nomeando o campo) — o artefato ambíguo
não nasce. E se um campo de medição não casa com o esquema
medido/falhou/nao_aplicavel, idem (ROTULO_FORA_DO_ESQUEMA).

Saídas: 0 escreveu os dois artefatos · 2 rótulo ambíguo ou fora do
esquema — nada publicado.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import voz                    # noqa: E402

# o "ou" que é ambiguidade: palavra isolada (o "ou" de "quarenta" não é —
# a regex exige limites de palavra, e "or" em inglês não é nada aqui)
OU_AMBIGUO = re.compile(r"(?<![A-Za-zÀ-ÿ])ou(?![A-Za-zÀ-ÿ])", re.IGNORECASE)

# os campos de medição: todo valor casa com um destes três estados
ESTADOS = ("medido:", "falhou:", "nao_aplicavel:")

# os campos de síntese — na cópia avx2 do gate, todos nao_aplicavel
CAMPOS_SINTESE = ("threads.efetivas_da_sessao", "threads.gravadas_no_audio_json",
                  "threads.omp_da_imagem", "prova.determinismo_interno",
                  "prova.veredito_da_prova_por_classe")


def _rotulo(estado: str, valor) -> str:
    """um estado nomeado, sempre"""
    return f"{estado}{valor}"


def _checar_rotulos(doc: dict, onde: str) -> list:
    """devolve a lista de violações (vazia = conforme) do documento todo."""
    problemas = []

    def caminhar(no, caminho):
        if isinstance(no, dict):
            for k, v in no.items():
                caminhar(v, f"{caminho}.{k}")
        elif isinstance(no, list):
            for i, v in enumerate(no):
                caminhar(v, f"{caminho}[{i}]")
        elif isinstance(no, str):
            if OU_AMBIGUO.search(no):
                problemas.append(f"ROTULO_AMBIGUO: {caminho} = {no!r} "
                                 f"contém 'ou' — estado único, nunca texto "
                                 f"com alternativa")
    caminhar(doc, onde)
    return problemas


def _checar_esquema(doc: dict) -> list:
    """todo campo de medição (threads.*/classe_simd.*/prova.*) casa com
    medido:/falhou:/nao_aplicavel: — sem exceção."""
    problemas = []

    def secoes():
        for nome in ("threads", "classe_simd", "prova"):
            sec = doc.get(nome)
            if isinstance(sec, dict):
                for k, v in sec.items():
                    yield f"{nome}.{k}", v
    for campo, valor in secoes():
        if not isinstance(valor, str) or not valor.startswith(ESTADOS):
            problemas.append(f"ROTULO_FORA_DO_ESQUEMA: {campo} = {valor!r} "
                             f"— os três estados nomeados são "
                             f"medido:/falhou:/nao_aplicavel:")
    return problemas


def _lock_rotulado() -> dict:
    """os três campos de leitura do lock, rotulados — medido ou falhou."""
    out = {}
    try:
        amb = voz.ancora()["ambiente"]
        out["threads.ancora_voz_lock"] = _rotulo(
            "medido:", str(amb.get("threads", "ausente")))
    except Exception as e:
        out["threads.ancora_voz_lock"] = _rotulo(
            "falhou:", f"lock-ilegivel-{type(e).__name__}")
    try:
        classe = str(voz.ancora()["ambiente"].get("classe_simd", "")).strip()
        if not classe:
            raise ValueError("sem classe_simd no ambiente do lock")
        out["classe_simd.da_ancora"] = _rotulo("medido:", classe)
    except Exception as e:
        out["classe_simd.da_ancora"] = _rotulo(
            "falhou:", f"lock-sem-classe-{type(e).__name__}")
    try:
        tol = voz.tolerancia()
        teto = str(tol.get("residuo_max_dbfs", "")).strip()
        if not teto:
            raise ValueError("sem residuo_max_dbfs no bloco tolerancia")
        out["classe_simd.teto_residuo_dbfs"] = _rotulo("medido:", teto)
    except Exception as e:
        out["classe_simd.teto_residuo_dbfs"] = _rotulo(
            "falhou:", f"lock-sem-tolerancia-{type(e).__name__}")
    return out


def _gravadas_no_audio_json() -> str:
    """as threads gravadas no audio.json do primeiro filme com audio —
    o REGISTRADO pela síntese (na cp avx512, o regenerado; commitado de
    resto, é leitura de arquivo, nunca env)."""
    import glob
    alvo = sorted(glob.glob(str(RAIZ / "filmes" / "*" / "audio" / "audio.json")))
    if not alvo:
        return _rotulo("falhou:", "sem-audio-json-no-repositorio")
    try:
        ambi = json.load(open(alvo[0])).get("ambiente", {})
        return _rotulo("medido:", str(ambi.get("threads", "nao gravado")))
    except Exception as e:
        return _rotulo("falhou:", f"audio-json-ilegivel-{type(e).__name__}")


def _determinismo(rodada1: Path, rodada2: Path, classe: str) -> str:
    if classe != "avx512":
        return _rotulo("nao_aplicavel:", "classe_avx2")
    try:
        if not (rodada1.exists() and rodada2.exists()):
            return _rotulo("falhou:", "rodadas-nao-rodaram")
        if rodada1.read_text() == rodada2.read_text():
            return _rotulo("medido:", "estavel")
        return _rotulo("medido:", "divergente")
    except Exception as e:
        return _rotulo("falhou:", f"rodadas-ilegiveis-{type(e).__name__}")


def _veredito_prova(prova: Path, classe: str) -> str:
    if classe != "avx512":
        return _rotulo("nao_aplicavel:", "classe_avx2")
    try:
        p = json.loads(prova.read_text(encoding="utf-8"))
        v = str(p.get("veredito", "")).strip()
        if v:
            return _rotulo("medido:", v)
        return _rotulo("falhou:", "prova-sem-veredito")
    except FileNotFoundError:
        return _rotulo("falhou:", "prova-nao-rodou")
    except Exception as e:
        return _rotulo("falhou:", f"prova-ilegivel-{type(e).__name__}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--saida", default="/tmp/identidade",
                    help="onde veredito.json e identidade.json vão")
    ap.add_argument("--prova", default="/tmp/prova/prova.json",
                    help="o prova.json da cópia (classe avx512)")
    ap.add_argument("--rodada1", default="/tmp/rodada1.sha256",
                    help="os sha256 da rodada 1")
    ap.add_argument("--rodada2", default="/tmp/rodada2.sha256",
                    help="os sha256 da rodada 2")
    args = ap.parse_args()
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    classe = (os.environ.get("CLASSE_DO_RUNNER")
              or "").strip() or "indeterminada"

    # ---- o veredito.json: o contrato do agregador (CP-013) ---------------
    doc = {
        "copia": os.environ.get("COPIA"),
        "run_id": os.environ.get("RUN_ID"),
        "run_attempt": os.environ.get("ATTEMPT"),
        "cpu": os.environ.get("CPU_MODELO", "ilegivel"),
        "classe": classe,
    }
    if classe == "avx512":
        doc["prova"] = "bytes-pcm+codec-sob-teto"
        causa = "prova.json ausente/ilegivel"
        p = {}
        try:
            p = json.loads(Path(args.prova).read_text(encoding="utf-8"))
            v = str(p.get("veredito", "?")).strip()
        except Exception as e:
            v, causa = "NAO MEDIDO", f"prova.json ausente/ilegivel: {e}"
        if v.startswith("verde"):
            doc["veredito"] = "identica"
            doc["detalhe"] = v + " (CP-012: PCM idêntico; codec sob teto; controle vivo)"
        elif v.startswith("VERMELHO"):
            doc["veredito"] = "divergente"
            doc["detalhe"] = v
        else:
            doc["veredito"] = "nao-provou"
            doc["detalhe"] = f"{v} — {causa}"
        numeros = {}
        try:
            for f in p.get("filmes", []):
                numeros[f.get("filme")] = {
                    "pcm_mixado": (f.get("pcm_mixado") or {}).get("identico"),
                    "residuo_codec_dbfs": (f.get("residuo_dbfs") or {}).get(
                        "opus_decodificado"),
                    "controle_codec_dbfs": (f.get("controle_codec") or {}).get(
                        "residuo_dbfs"),
                }
        except Exception:
            pass
        doc["numeros"] = numeros
    elif classe == "avx2":
        # CP-014: a cópia avx2 do GATE não observa mais (a observação de
        # verdade — regenerado x âncora, fala a fala — é o dispatch manual
        # observar_avx2). Aqui só declara a saída cedo: neutra.
        doc["prova"] = "observacao-dispatch-manual"
        doc["veredito"] = "observacao"
        doc["detalhe"] = ("classe avx2: saída cedo no gate — sem build, sem "
                          "gate, sem audio-suite, sem medir a âncora "
                          "(CP-014: medir o mesmo arquivo em toda cópia não "
                          "traz informação); a observação é o dispatch "
                          "manual observar_avx2")
    else:
        doc["prova"] = "classificacao"
        doc["veredito"] = "indeterminada"
        doc["detalhe"] = ("o classificador não determinou a classe — a cópia "
                          "não prova nem observa; ilegível para o agregador")

    # ---- o identidade.json: rótulos únicos (CP-014) -----------------------
    na_avx2 = _rotulo("nao_aplicavel:", "classe_avx2")
    lock = _lock_rotulado()

    def env_ou_na(env, falha):
        if classe != "avx512":
            return na_avx2
        v = (os.environ.get(env) or "").strip()
        return _rotulo("medido:", v) if v else _rotulo("falhou:", falha)

    identidade = {
        "esquema_rotulos": {
            "cp": "CP-014",
            "estados": ["medido:", "falhou:", "nao_aplicavel:"],
            "nota": ("campos de síntese na cópia avx2 do gate: "
                     "nao_aplicavel:classe_avx2; a observação desta classe "
                     "é o dispatch manual observar_avx2"),
        },
        "run_id": os.environ.get("RUN_ID"),
        "run_attempt": os.environ.get("ATTEMPT"),
        "copia": os.environ.get("COPIA"),
        "cpu": {
            "modelo": os.environ.get("CPU_MODELO", "ilegivel"),
            "sockets": os.environ.get("SOCKETS"),
            "nucleos_fisicos": os.environ.get("NUCLEOS_FISICOS"),
            "threads_por_nucleo": os.environ.get("THREADS_POR_NUCLEO"),
            "avx2": bool(int(os.environ.get("AVX2", "0") or 0)),
            "avx512f": bool(int(os.environ.get("AVX512F", "0") or 0)),
            "amx_tile": bool(int(os.environ.get("AMX_TILE", "0") or 0)),
            "nproc": os.environ.get("NPROC"),
            "cgroup_cpu_max": os.environ.get("CGROUP_CPU"),
        },
        "threads": {
            "ancora_voz_lock": lock["threads.ancora_voz_lock"],
            "efetivas_da_sessao": env_ou_na("THREADS_EFETIVAS",
                                            "probe-da-sessao-nao-rodou"),
            # o registro de threads do audio.json é a PONTO FINAL da cadeia
            # de síntese (lock -> ENV -> sessão -> gravado): sem síntese
            # (cópia avx2 do gate), não há cadeia — nao_aplicavel
            "gravadas_no_audio_json": (na_avx2 if classe == "avx2"
                                       else _gravadas_no_audio_json()),
            "omp_da_imagem": env_ou_na("OMP_NUM_THREADS",
                                       "env-omp-nao-medido"),
        },
        "classe_simd": {
            "do_runner": (
                _rotulo("medido:", classe)
                if classe in ("avx512", "avx2")
                else _rotulo("falhou:", "classificador-nao-declarou")),
            "da_ancora": lock["classe_simd.da_ancora"],
            "teto_residuo_dbfs": lock["classe_simd.teto_residuo_dbfs"],
        },
        "prova": {
            "determinismo_interno": _determinismo(
                Path(args.rodada1), Path(args.rodada2), classe),
            "veredito_da_prova_por_classe": _veredito_prova(
                Path(args.prova), classe),
            "observacao_da_ancora": (
                _rotulo("nao_aplicavel:",
                        "observacao-por-dispatch-observar_avx2")
                if classe == "avx2" else
                _rotulo("nao_aplicavel:", "classe_avx512")),
        },
    }

    # ---- rótulo ambíguo não publica ---------------------------------------
    problemas = (_checar_rotulos(identidade, "identidade")
                 + _checar_rotulos(doc, "veredito")
                 + _checar_esquema(identidade))
    if problemas:
        for p in problemas:
            print(f"ERRO: {p}", file=sys.stderr)
        print("ERRO: o artefato ambíguo não nasce — corrija o rótulo "
              "(CP-014)", file=sys.stderr)
        return 2

    (saida / "veredito.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    (saida / "identidade.json").write_text(
        json.dumps(identidade, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    print("== veredito da cópia (CP-014: rótulos únicos) — "
          f"{doc.get('copia')}/{classe}: {doc.get('veredito')}")
    print(json.dumps(identidade, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
