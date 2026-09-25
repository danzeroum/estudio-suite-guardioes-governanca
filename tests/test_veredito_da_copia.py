#!/usr/bin/env python3
"""Os rótulos únicos do identidade.json (CP-014), provados com cópias
sintéticas.

A aceite da CP-014 é literal:
  - artefato AVX2 -> TODOS os campos de síntese em nao_aplicavel
    (exatamente "nao_aplicavel:classe_avx2")
  - campo com "ou" -> o teste reprova (e a GERAÇÃO reprova: o artefato
    ambíguo não nasce — ROTULO_AMBIGUO nomeando o campo)
  - cada campo de medição casa com um estado único: medido:<valor>,
    falhou:<motivo> ou nao_aplicavel:<motivo>

O que se prova aqui: o gerador (ci/veredito_da_copia.py) escreve o
veredito.json (o contrato do agregador — avx2 neutra, avx512 pela prova
da CP-012) e o identidade.json rotulado; o validador recusa rótulo com
"ou" e rótulo fora do esquema; a cópia avx2 declara a síntese inteira
como nao_aplicavel; a cópia avx512 mede (ou nomeia a falha de medir) —
nunca texto ambíguo. E o contrato estrutural do workflow: a saída cedo
da avx2 é SEM pipx/audio-suite, e o veredito/identidade nascem do
módulo.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

_spec = importlib.util.spec_from_file_location(
    "veredito_da_copia", RAIZ / "ci" / "veredito_da_copia.py")
vd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vd)

ok, bad = [], []


def chk(c, msg):
    (ok if c else bad).append(msg)


def gerar(tmp: Path, env: dict, prova=None, r1=None, r2=None) -> subprocess.CompletedProcess:
    e = {**env}
    import os
    env_backup = {k: os.environ.get(k) for k in e}
    os.environ.update(e)
    try:
        prova_path = tmp / "prova.json"
        if prova is None:
            prova_path.unlink(missing_ok=True)   # o caso 'sem prova' não pode
        elif prova is not None:                # ler o prova.json do caso anterior
            prova_path.write_text(json.dumps(prova), encoding="utf-8")
        cmd = [sys.executable, "ci/veredito_da_copia.py",
               "--saida", str(tmp / "saida"),
               "--prova", str(prova_path),
               "--rodada1", str(r1 or tmp / "r1.sha256"),
               "--rodada2", str(r2 or tmp / "r2.sha256")]
        return subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ)
    finally:
        for k, v in env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def principais() -> dict:
    return {"COPIA": "copia-1", "RUN_ID": "123", "ATTEMPT": "1",
            "CPU_MODELO": "AMD EPYC 9V74 80-Core Processor",
            "SOCKETS": "1", "NUCLEOS_FISICOS": "80",
            "THREADS_POR_NUCLEO": "1", "AVX2": "1", "AVX512F": "0",
            "AMX_TILE": "0", "NPROC": "4", "CGROUP_CPU": "400000 100000"}


CAMPOS_SINTESE = ("efetivas_da_sessao", "gravadas_no_audio_json",
                  "omp_da_imagem")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="rotulos-"))

    # --- a aceite: artefato AVX2 -> síntese toda em nao_aplicavel -----
    r = gerar(tmp, {**principais(), "CLASSE_DO_RUNNER": "avx2"})
    chk(r.returncode == 0, f"a cópia avx2 gera sem erro (exit {r.returncode})")
    ident = json.loads((tmp / "saida" / "identidade.json").read_text())
    for campo in CAMPOS_SINTESE:
        chk(ident["threads"][campo] == "nao_aplicavel:classe_avx2",
            f"avx2: threads.{campo} = 'nao_aplicavel:classe_avx2'")
    chk(ident["prova"]["determinismo_interno"] == "nao_aplicavel:classe_avx2",
        "avx2: prova.determinismo_interno = 'nao_aplicavel:classe_avx2'")
    chk(ident["prova"]["veredito_da_prova_por_classe"]
        == "nao_aplicavel:classe_avx2",
        "avx2: prova.veredito_da_prova_por_classe = 'nao_aplicavel:classe_avx2'")
    chk(ident["prova"]["observacao_da_ancora"].startswith("nao_aplicavel:"),
        "avx2: a observação declara nao_aplicavel com motivo nomeado "
        "(dispatch manual)")
    ver = json.loads((tmp / "saida" / "veredito.json").read_text())
    chk(ver["veredito"] == "observacao",
        "avx2: o veredito da cópia segue 'observacao' (neutra no agregador)")
    chk(ver["prova"] == "observacao-dispatch-manual",
        "avx2: a prova declarada aponta o dispatch manual (CP-014)")

    # --- o esquema: todo campo de medição tem estado nomeado ------------
    for secao in ("threads", "classe_simd", "prova"):
        for campo, valor in ident[secao].items():
            chk(isinstance(valor, str) and valor.startswith(
                ("medido:", "falhou:", "nao_aplicavel:")),
                f"{secao}.{campo} casa com medido:/falhou:/nao_aplicavel: "
                f"({valor!r})")
    chk(ident["classe_simd"]["do_runner"] == "medido:avx2",
        "a classe medida é 'medido:avx2'")
    chk(ident["classe_simd"]["da_ancora"] == "medido:avx512",
        "a classe da ancora vem do lock como 'medido:avx512'")
    chk(ident["classe_simd"]["teto_residuo_dbfs"] == "medido:-74.9",
        "o teto do codec vem do lock como 'medido:-74.9'")

    # --- nenhum texto com "ou" em artefato NENHUM ----------------------
    def sem_ou(no, caminho):
        if isinstance(no, dict):
            for k, v in no.items():
                sem_ou(v, f"{caminho}.{k}")
        elif isinstance(no, str):
            chk(vd.OU_AMBIGUO.search(no) is None,
                f"{caminho} não contém 'ou' (rótulo único): {no[:60]!r}")
    sem_ou(ident, "identidade")
    sem_ou(ver, "veredito")

    # --- a aceite: campo com "ou" -> REPROVA ---------------------------
    problemas = vd._checar_rotulos(
        {"threads": {"efetivas_da_sessao":
                     "copia avx2 (sem build, CP-013) ou DIVERGENTE"}},
        "identidade")
    chk(len(problemas) == 1 and "ROTULO_AMBIGUO" in problemas[0]
        and "efetivas_da_sessao" in problemas[0],
        "o defeito real da CP-013 ('... ou DIVERGENTE') é ROTULO_AMBIGUO "
        "nomeando o campo")
    chk(vd._checar_rotulos({"a": "texto sem alternativa"}, "x") == [],
        "texto sem 'ou' passa")

    # --- rótulo fora do esquema reprova --------------------------------
    fora = vd._checar_esquema(
        {"threads": {"efetivas_da_sessao": "NAO RODOU"},
         "classe_simd": {}, "prova": {}})
    chk(len(fora) == 1 and "ROTULO_FORA_DO_ESQUEMA" in fora[0],
        "'NAO RODOU' (sem estado) é ROTULO_FORA_DO_ESQUEMA — o antigo "
        "defeito nomeado")

    # --- a cópia avx512 MEDE (ou nomeia a falha) -----------------------
    r1, r2 = tmp / "ra.sha256", tmp / "rb.sha256"
    r1.write_text("a 1\nb 2\n")
    r2.write_text("a 1\nb 2\n")
    prova = {"veredito": "verde — bytes-pcm+codec-sob-teto",
             "filmes": [{"filme": "jornada-dado",
                         "pcm_mixado": {"identico": True},
                         "residuo_dbfs": {"opus_decodificado": -80.9},
                         "controle_codec": {"residuo_dbfs": -68.63}}]}
    r = gerar(tmp, {**principais(), "CLASSE_DO_RUNNER": "avx512",
                    "AVX512F": "1", "THREADS_EFETIVAS": "4",
                    "OMP_NUM_THREADS": "4"}, prova=prova, r1=r1, r2=r2)
    chk(r.returncode == 0, f"a cópia avx512 gera sem erro (exit {r.returncode})")
    ident = json.loads((tmp / "saida" / "identidade.json").read_text())
    ver = json.loads((tmp / "saida" / "veredito.json").read_text())
    for campo in CAMPOS_SINTESE:
        chk(ident["threads"][campo].startswith("medido:"),
            f"avx512: threads.{campo} é medido: ({ident['threads'][campo]!r})")
    chk(ident["prova"]["determinismo_interno"] == "medido:estavel",
        "avx512: determinismo medido:estavel (as rodadas batem)")
    chk(ident["prova"]["veredito_da_prova_por_classe"]
        == "medido:verde — bytes-pcm+codec-sob-teto",
        "avx512: o veredito da prova é medido:<veredito>")
    chk(ver["veredito"] == "identica" and ver["numeros"]["jornada-dado"][
        "residuo_codec_dbfs"] == -80.9,
        "avx512: o veredito da cópia segue a prova da CP-012 com números")
    chk(ident["prova"]["observacao_da_ancora"] == "nao_aplicavel:classe_avx512",
        "avx512: a observação (exclusiva da avx2) é nao_aplicavel:classe_avx512")

    # --- avx512 SEM prova rodada: falhou nomeado, nunca ambíguo --------
    r = gerar(tmp, {**principais(), "CLASSE_DO_RUNNER": "avx512",
                    "AVX512F": "1"}, prova=None)
    chk(r.returncode == 0, f"avx512 sem prova gera (exit {r.returncode})")
    ident = json.loads((tmp / "saida" / "identidade.json").read_text())
    ver = json.loads((tmp / "saida" / "veredito.json").read_text())
    chk(ident["prova"]["veredito_da_prova_por_classe"].startswith("falhou:"),
        "avx512 sem prova: 'falhou:prova-nao-rodou' — nunca 'NAO RODOU' solto")
    chk(ident["threads"]["efetivas_da_sessao"].startswith("falhou:"),
        "avx512 sem probe de sessão: 'falhou:probe-da-sessao-nao-rodou'")
    chk(ver["veredito"] == "nao-provou",
        "avx512 sem prova: a cópia nao-provou (ilegível no agregador)")

    # --- o contrato estrutural do workflow ------------------------------
    wf = (RAIZ / ".github" / "workflows" / "dublador.yml").read_text(
        encoding="utf-8")
    chk("python3 ci/veredito_da_copia.py" in wf,
        "o veredito/identidade nascem de ci/veredito_da_copia.py no workflow")
    trecho_saida = wf[wf.index("A saída cedo da classe avx2"):]
    fim = trecho_saida.index("# CP-013: daqui para baixo")
    trecho_saida = trecho_saida[:fim]
    chk("if: env.CLASSE_DO_RUNNER == 'avx2'" in trecho_saida,
        "a saída cedo da avx2 é um passo próprio da classe")
    chk("pipx" not in trecho_saida and "observacao_ancora" not in trecho_saida
        and "observar_avx2.py" not in trecho_saida,
        "a saída cedo NÃO instala nem roda instrumento nenhum — só declara "
        "(o echo menciona audio-suite para DIZER que não instala)")
    corpo_avx2 = wf[wf.index("A saída cedo da classe avx2"):]
    corpo_avx2 = corpo_avx2[:corpo_avx2.index("O veredito e a identidade") \
        if "O veredito e a identidade" in corpo_avx2 else len(corpo_avx2)]
    chk("observacao_ancora.py" not in corpo_avx2,
        "o passo de saída cedo não chama observacao_ancora.py (a âncora "
        "não é mais medida no gate)")
    import re as _re
    chk("pipx install" not in wf,
        "o gate (dublador.yml) não instala audio-suite em passo NENHUM — "
        "o instrumento de observação saiu do gate inteiro (CP-014)")
    # o workflow de observação existe e é dispatch manual
    wfo = (RAIZ / ".github" / "workflows" / "observar-avx2.yml").read_text(
        encoding="utf-8")
    chk("workflow_dispatch" in wfo and "ci/observar_avx2.py" in wfo,
        "o dispatch manual observar_avx2 existe e mede com "
        "ci/observar_avx2.py")
    chk("observação, sem gate" in wfo,
        "o dispatch carrega o rótulo 'observação, sem gate'")

    print(f"  {len(ok)} verificações dos rótulos únicos (CP-014).")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  o identidade.json não tem campo ambíguo: medido, falhou com")
    print("  motivo ou nao_aplicavel com motivo — nunca texto com 'ou'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
