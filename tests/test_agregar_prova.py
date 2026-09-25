#!/usr/bin/env python3
"""O agregador da prova por amostragem, provado com artefatos sintéticos
(CP-013; ONDAS CP-015).

A aceite da CP-013 é literal:
  - {1 AVX-512 idêntica + 11 AVX2}                -> verde
  - {0 AVX-512}                                   -> SEM_AMOSTRA_DECISIVA
  - {2 idênticas + 1 divergente}                  -> DIVERGENCIA_AVX512 nomeando a cópia
  - artefato ausente ou corrompido                -> reprova ("amostra ilegível"),
                                                     nunca conta como neutra
  - uma cópia AVX2 termina sem build e sem gate   -> classe no artefato, neutra

A aceite da CP-015 (ondas, com os casos da diretiva):
  - onda 1 {8 avx2} + onda 2 {1 AVX-512 idêntica} -> VERDE (a segunda onda
    salvou o sorteio — o rerun humano deixou de ser o caminho)
  - ondas {8 avx2} + {8 avx2}                     -> SEM_AMOSTRA_DECISIVA
    (só existe após DUAS ondas vazias — vermelho nomeado)
  - onda 2 com AVX-512 divergente                 -> DIVERGENCIA_AVX512
    NOMEANDO A ONDA E A CÓPIA
  - onda 2 declarada sem artefato                 -> AMOSTRA_ILEGIVEL (o run
    não entregou — cópia sem artefato não é sorteio, não é SEM_AMOSTRA)

O que se prova aqui: o veredito do RUN é da AMOSTRAGEM sobre as ondas,
não da cópia — nenhuma cópia decide sozinha; a divergência é nomeada com
onda e cópia; a falta de amostra decisiva é vermelho nomeado que só nasce
após duas ondas vazias; a cópia avx2 não contribui, não bloqueia e não é
neutra POR OMISSÃO — é neutra por classe declarada; e o que não se pode
ler, reprova. E os contratos estruturais: o corpo da cópia (uma onda
reutilizável, dublador-onda.yml), o roteador da segunda onda, a onda 2
condicional no orquestrador, o job obrigatório (sem continue-on-error), o
veredito.json publicado sempre, a matrix do lock e o registro com as
ondas no agregado.json.
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
    "agregar_prova", RAIZ / "ci" / "agregar_prova.py")
agregar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agregar)

ok, bad = [], []


def chk(c, msg):
    (ok if c else bad).append(msg)


def copia_veredito(copia, classe, veredito, onda=None, cpu="AMD EPYC 9V74 80-Core Processor",
                   detalhe="detalhe de teste", extra=None):
    doc = {"copia": copia, "cpu": cpu, "classe": classe,
           "prova": ("bytes-pcm+codec-sob-teto" if classe == "avx512"
                     else "observacao-dispatch-manual"),
           "veredito": veredito, "detalhe": detalhe}
    if onda is not None:
        doc["onda"] = onda
    if extra:
        doc.update(extra)
    return doc


def montar(dir_raiz, docs, nomes=None):
    """Um subdiretório por artefato, como o download-artifact@v4 deixa."""
    for i, doc in enumerate(docs):
        onda = doc.get("onda", 1)
        sub = dir_raiz / (nomes[i] if nomes else
                          f"identidade-onda{onda}-{doc['copia']}-run1")
        sub.mkdir(parents=True, exist_ok=True)
        (sub / "veredito.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def rodar(artefatos, copias, conferir_n=False, ondas="1"):
    cmd = [sys.executable, "ci/agregar_prova.py",
           "--artefatos", str(artefatos),
           "--copias", json.dumps(copias),
           "--ondas", ondas,
           "--saida", str(artefatos / "agregado")]
    if conferir_n:
        cmd.append("--conferir-n")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ)


def caso(nome):
    d = Path(tempfile.mkdtemp(prefix=f"agreg-{nome}-"))
    return d


def main():
    C12 = [f"copia-{i}" for i in range(1, 13)]
    C8 = [f"copia-{i}" for i in range(1, 9)]

    # --- a aceite, caso 1: {1 AVX-512 identica + 11 AVX2} -> verde --------
    d = caso("c1")
    docs = ([copia_veredito("copia-12", "avx512", "identica")] +
            [copia_veredito(f"copia-{i}", "avx2", "observacao")
             for i in range(1, 12)])
    montar(d, docs)
    r = rodar(d, C12)
    chk(r.returncode == 0 and "verde" in r.stdout,
        f"1 AVX-512 idêntica + 11 AVX2 -> verde (exit {r.returncode})")
    ag = json.loads((d / "agregado" / "agregado.json").read_text())
    chk(ag["identicas_avx512"] == ["copia-12"]
        and len(ag["observacoes_avx2"]) == 11 and not ag["ilegiveis"],
        "o agregado registra quem é idêntica, quem observa e ninguém ilegível")
    chk("| onda | cópia | CPU | classe | prova | veredito |" in r.stdout
        and "copia-12" in r.stdout and "observacao" in r.stdout,
        "o resumo lista onda, cópia, CPU, classe, prova e veredito de TODAS")

    # --- o REGISTRO no agregado.json (CP-014/CP-015) ---------------------
    reg = ag.get("registro")
    chk(isinstance(reg, dict) and reg.get("n") == 12
        and reg.get("avx512") == 1 and reg.get("sem_amostra_decisiva") is False,
        "o agregado.json leva a entrada de registro: n, classes por cópia, "
        "avx512 e SEM_AMOSTRA=nao (CP-014 — para o PR de manutenção)")
    chk(reg.get("ondas") == 1,
        "o registro declara 1 onda (CP-015) — a era de uma onda só continua "
        "no formato antigo, chaves de cópia simples")
    chk(reg.get("copias", {}).get("copia-12") == "avx512"
        and reg.get("copias", {}).get("copia-1") == "avx2",
        "o registro declara a classe de cada cópia esperada")
    chk("PR de manutenção" in reg.get("fonte", ""),
        "a fonte do registro declara: cresce por PR de manutenção, sem "
        "commit automático no main")
    chk("registro" in r.stdout, "o agregador anuncia a entrada de registro "
        "no stdout (o curador sabe onde buscar)")

    # --- a aceite, caso 2: {0 AVX-512} -> SEM_AMOSTRA_DECISIVA ------------
    # (era CP-013: onda única; o veredito nomeia que a segunda onda devia
    # ter acordado — hoje é o roteador quem decide, e o teste do roteador
    # prova que ele acorda)
    d = caso("c2")
    docs = [copia_veredito(f"copia-{i}", "avx2", "observacao")
            for i in range(1, 9)]
    montar(d, docs)
    r = rodar(d, C8)
    chk(r.returncode == 1 and "SEM_AMOSTRA_DECISIVA" in r.stdout,
        f"zero AVX-512 na onda única -> SEM_AMOSTRA_DECISIVA vermelho "
        f"nomeado (exit {r.returncode})")

    # --- a aceite, caso 3: {2 idênticas + 1 divergente} -> nomeada --------
    d = caso("c3")
    docs = ([copia_veredito("copia-1", "avx512", "identica"),
             copia_veredito("copia-2", "avx512", "identica"),
             copia_veredito("copia-3", "avx512", "divergente",
                            detalhe="o hash do PCM mixado DIVERGE — "
                                    "residuo -30.1 dBFS acima do teto -74.9")] +
            [copia_veredito(f"copia-{i}", "avx2", "observacao")
             for i in range(4, 9)])
    montar(d, docs)
    r = rodar(d, C8)
    chk(r.returncode == 1 and "DIVERGENCIA_AVX512" in r.stdout
        and "copia-3" in r.stdout and "-30.1" in r.stdout,
        f"2 idênticas + 1 divergente -> DIVERGENCIA_AVX512 nomeando a "
        f"copia-3 com os números (exit {r.returncode})")
    ag = json.loads((d / "agregado" / "agregado.json").read_text())
    chk(ag["divergentes_avx512"] == ["copia-3"]
        and ag["identicas_avx512"] == ["copia-1", "copia-2"],
        "o agregado separa idênticas de divergentes, com os nomes")

    # --- CP-015, a aceite da diretiva, ondas ------------------------------
    # onda 1 {8 avx2} + onda 2 {1 AVX-512 idêntica} -> VERDE
    d = caso("w1")
    o1 = [copia_veredito(f"copia-{i}", "avx2", "observacao", onda=1)
          for i in range(1, 9)]
    o2 = ([copia_veredito("copia-1", "avx512", "identica", onda=2)] +
          [copia_veredito(f"copia-{i}", "avx2", "observacao", onda=2)
           for i in range(2, 9)])
    montar(d, o1 + o2)
    r = rodar(d, C8, ondas="1,2")
    chk(r.returncode == 0 and "verde" in r.stdout,
        f"onda 1 {{8 avx2}} + onda 2 {{1 AVX-512 idêntica}} -> VERDE "
        f"(exit {r.returncode}): a segunda onda automática salvou o sorteio")
    ag = json.loads((d / "agregado" / "agregado.json").read_text())
    chk(ag["identicas_avx512"] == ["onda-2/copia-1"],
        "a cópia idêntica é nomeada COM A ONDA (onda-2/copia-1)")
    reg = ag["registro"]
    chk(reg["n"] == 16 and reg["ondas"] == 2 and reg["avx512"] == 1
        and reg["sem_amostra_decisiva"] is False,
        "o registro da execução com 2 ondas: n=16 (soma das ondas), "
        "ondas=2, avx512=1, SEM_AMOSTRA=nao")
    chk(reg["copias"].get("onda-1/copia-1") == "avx2"
        and reg["copias"].get("onda-2/copia-1") == "avx512",
        "com 2 ondas o registro prefixa as cópias: onda-1/copia-1 avx2, "
        "onda-2/copia-1 avx512")

    # ondas {8 avx2} + {8 avx2} -> SEM_AMOSTRA_DECISIVA (duas ondas vazias)
    d = caso("w2")
    o1 = [copia_veredito(f"copia-{i}", "avx2", "observacao", onda=1)
          for i in range(1, 9)]
    o2 = [copia_veredito(f"copia-{i}", "avx2", "observacao", onda=2)
          for i in range(1, 9)]
    montar(d, o1 + o2)
    r = rodar(d, C8, ondas="1,2")
    chk(r.returncode == 1 and "SEM_AMOSTRA_DECISIVA" in r.stdout
        and "DUAS ondas" in r.stdout,
        f"ondas {{8 avx2}} + {{8 avx2}} -> SEM_AMOSTRA_DECISIVA após as "
        f"duas ondas vazias (exit {r.returncode}) — vermelho nomeado")
    ag = json.loads((d / "agregado" / "agregado.json").read_text())
    chk(ag["registro"]["sem_amostra_decisiva"] is True
        and ag["registro"]["n"] == 16,
        "o registro marca SEM_AMOSTRA=sim no caso das duas ondas vazias")

    # onda 2 com AVX-512 divergente -> DIVERGENCIA nomeando ONDA e cópia
    d = caso("w3")
    o1 = [copia_veredito(f"copia-{i}", "avx2", "observacao", onda=1)
          for i in range(1, 9)]
    o2 = [copia_veredito("copia-3", "avx512", "divergente", onda=2,
                         detalhe="o hash do PCM mixado DIVERGE — "
                                 "residuo -30.1 dBFS acima do teto -74.9")]
    montar(d, o1 + o2)
    r = rodar(d, C8, ondas="1,2")
    chk(r.returncode == 1 and "DIVERGENCIA_AVX512" in r.stdout
        and "onda-2/copia-3" in r.stdout and "-30.1" in r.stdout,
        f"onda 2 com AVX-512 divergente -> DIVERGENCIA_AVX512 NOMEANDO a "
        f"onda e a cópia (exit {r.returncode})")
    ag = json.loads((d / "agregado" / "agregado.json").read_text())
    chk(ag["divergentes_avx512"] == ["onda-2/copia-3"],
        "o agregado registra a divergente com onda E cópia")

    # onda 2 declarada que não entregou -> AMOSTRA_ILEGIVEL
    d = caso("w4")
    o1 = [copia_veredito(f"copia-{i}", "avx2", "observacao", onda=1)
          for i in range(1, 9)]
    montar(d, o1)   # a onda 2 inteira sem artefato
    r = rodar(d, C8, ondas="1,2")
    chk(r.returncode == 1 and "AMOSTRA_ILEGIVEL" in r.stdout
        and "onda-2/copia-1: SEM ARTEFATO" in r.stdout,
        f"onda 2 declarada sem artefato -> AMOSTRA_ILEGIVEL nomeando "
        f"onda-2/copia-1 (exit {r.returncode}): o run não entregou, NÃO é "
        f"SEM_AMOSTRA — cópia sem artefato não é sorteio")
    ag = json.loads((d / "agregado" / "agregado.json").read_text())
    chk(ag["registro"]["sem_amostra_decisiva"] is False,
        "o registro NÃO conta o run sem artefato como SEM_AMOSTRA — a "
        "estatística do sorteio não se mistura com a entrega faltando")

    # cópia da onda 1 com o CAMPO onda divergente do esperado -> ilegível
    d = caso("w5")
    docs = [copia_veredito(f"copia-{i}", "avx2", "observacao", onda=2)
            for i in range(1, 9)]
    montar(d, docs)
    r = rodar(d, C8, ondas="1")
    chk(r.returncode == 1 and "AMOSTRA_ILEGIVEL" in r.stdout
        and "FORA das ondas declaradas" in r.stdout
        and "SEM ARTEFATO" in r.stdout,
        "vereditos de onda não declarada (2) com ondas='1' -> ilegível: as "
        "cópias da onda 1 ficam SEM ARTEFATO e os artefatos presentes são "
        "apontados FORA das ondas declaradas (o agregador não mistura "
        "ondas)")

    # --conferir-n com 2 ondas: o total tem de ser N x ondas --------------
    d = caso("w6")
    r = rodar(d, C8, conferir_n=True, ondas="1,2")
    from estudio_suite import voz as _voz
    n_lock = int(_voz.frota()["amostragem"])
    chk(r.returncode == 1 and "AMOSTRA_ILEGIVEL" in (r.stderr + r.stdout)
        and f"N={n_lock}" in (r.stderr + r.stdout),
        f"--conferir-n com 2 ondas: 8 cópias x 2 ondas != N={n_lock} do "
        f"lock x 2 -> recusa nomeada (exit {r.returncode})")

    # --- a borda: artefato AUSENTE -> amostra ilegível, nunca neutra ------
    d = caso("c4")
    docs = ([copia_veredito("copia-1", "avx512", "identica")] +
            [copia_veredito(f"copia-{i}", "avx2", "observacao")
             for i in range(2, 6)])
    montar(d, docs)  # copia-6 esperada e ausente
    r = rodar(d, [f"copia-{i}" for i in range(1, 7)])
    chk(r.returncode == 1 and "AMOSTRA_ILEGIVEL" in r.stdout
        and "copia-6" in r.stdout and "SEM ARTEFATO" in r.stdout,
        f"cópia esperada sem artefato -> reprova 'amostra ilegível' com o "
        f"nome (exit {r.returncode}) — nunca neutra")

    # --- a borda: artefato CORROMPIDO -> amostra ilegível -----------------
    d = caso("c5")
    docs = ([copia_veredito("copia-1", "avx512", "identica"),
             copia_veredito("copia-2", "avx2", "observacao")])
    montar(d, docs)
    (d / "identidade-onda1-copia-2-run1" / "veredito.json").write_text(
        "{isto não é json", encoding="utf-8")
    r = rodar(d, ["copia-1", "copia-2"])
    chk(r.returncode == 1 and "corrompido" in (r.stderr + r.stdout),
        f"artefato corrompido -> reprova nomeando (exit {r.returncode})")

    # --- veredito.json legível mas SEM os campos -> ilegível --------------
    d = caso("c6")
    sub = d / "identidade-onda1-copia-2-run1"
    sub.mkdir(parents=True)
    (sub / "veredito.json").write_text(
        json.dumps({"copia": "copia-2", "cpu": "x"}), encoding="utf-8")
    sub2 = d / "identidade-onda1-copia-1-run1"
    sub2.mkdir(parents=True)
    (sub2 / "veredito.json").write_text(
        json.dumps(copia_veredito("copia-1", "avx512", "identica")),
        encoding="utf-8")
    r = rodar(d, ["copia-1", "copia-2"])
    chk(r.returncode == 1 and "campos" in r.stdout,
        f"veredito sem os campos do contrato -> ilegível (exit {r.returncode})")

    # --- avx512 que NÃO PROVOU (build falhou / prova não rodou) ----------
    d = caso("c7")
    docs = [copia_veredito("copia-1", "avx512", "nao-provou",
                           detalhe="NAO MEDIDO — prova.json ausente"),
            copia_veredito("copia-2", "avx2", "observacao")]
    montar(d, docs)
    r = rodar(d, ["copia-1", "copia-2"])
    chk(r.returncode == 1 and "AMOSTRA_ILEGIVEL" in r.stdout
        and "NÃO PROVOU" in r.stdout,
        f"cópia AVX-512 sem prova -> ilegível vermelha, nunca neutra "
        f"(exit {r.returncode})")

    # --- cópia DUPLICADA (retry) -> ilegível nomeada ----------------------
    d = caso("c11")
    doc1 = copia_veredito("copia-1", "avx512", "identica")
    montar(d, [doc1], nomes=["identidade-onda1-copia-1-run1"])
    montar(d, [doc1], nomes=["identidade-onda1-copia-1-run2-tentativa"])
    r = rodar(d, ["copia-1"])
    chk(r.returncode == 1 and "DUPLICADO" in r.stdout,
        f"cópia com dois artefatos (retry) -> ilegível nomeada "
        f"(exit {r.returncode})")

    # --- cópia avx2 com veredito IMPRÓPRIO -> ilegível (defensivo) --------
    d = caso("c8")
    docs = [copia_veredito("copia-1", "avx512", "identica"),
            copia_veredito("copia-2", "avx2", "divergente")]
    montar(d, docs)
    r = rodar(d, ["copia-1", "copia-2"])
    chk(r.returncode == 1 and "impróprio" in r.stdout,
        f"avx2 com veredito que não é 'observacao' -> ilegível "
        f"(exit {r.returncode}): o contrato não deixa mentir a classe")

    # --- classe INDETERMINADA -> ilegível ---------------------------------
    d = caso("c9")
    docs = [copia_veredito("copia-1", "avx512", "identica"),
            copia_veredito("copia-2", "indeterminada", "indeterminada")]
    montar(d, docs)
    r = rodar(d, ["copia-1", "copia-2"])
    chk(r.returncode == 1 and "indeterminada" in r.stdout,
        f"classe indeterminada -> ilegível (exit {r.returncode})")

    # --- --conferir-n: matrix que não veio do lock -> vermelho nomeado ---
    d = caso("c10")
    docs = [copia_veredito("copia-1", "avx512", "identica")]
    montar(d, docs)
    r = rodar(d, ["copia-1"], conferir_n=True)
    chk(r.returncode == 1 and "AMOSTRA_ILEGIVEL" in (r.stderr + r.stdout)
        and f"N={n_lock}" in (r.stderr + r.stdout),
        f"matrix de 1 contra N={n_lock} do lock -> recusa nomeada "
        f"(exit {r.returncode}): o tamanho da amostra mora no lock")

    # --- os contratos estruturais dos workflows (CP-015) ------------------
    wfd = (RAIZ / ".github" / "workflows" / "dublador.yml").read_text(
        encoding="utf-8")
    wfo = (RAIZ / ".github" / "workflows" / "dublador-onda.yml").read_text(
        encoding="utf-8")

    # o corpo da cópia: os passos caros SÓ na classe avx512
    passos_avx512 = ("O builder com cache de camadas",
                     "A imagem que materializa o lock",
                     "As threads efetivas da sessão",
                     "Dublar quem declara audio (rodada 1)",
                     "Dublar quem declara audio (rodada 2)",
                     "O determinismo interno da imagem",
                     "A prova por classe (dentro da imagem)")
    for passo in passos_avx512:
        trecho = wfo[wfo.index(f"- name: {passo}"):]
        cond = trecho[:trecho.index("run:")].count(
            "if: env.CLASSE_DO_RUNNER == 'avx512'")
        chk(cond == 1,
            f"'{passo}' roda SÓ na classe avx512 (cópia avx2 sem build)")

    # o orquestrador: onda 1, roteador, onda 2 CONDICIONAL, agregador
    chk("dublador-onda1:" in wfd
        and "uses: ./.github/workflows/dublador-onda.yml" in wfd
        and "onda: 1" in wfd,
        "o dublador.yml chama a onda 1 pelo workflow reutilizável")
    chk("dublador-onda2:" in wfd
        and "if: needs.rotear.outputs.segunda_onda == 'true'" in wfd
        and "onda: 2" in wfd,
        "a onda 2 é CONDICIONAL à saída do roteador (segunda onda "
        "automática — decisão do dono)")
    chk("ci/rotear_segunda_onda.py" in wfd
        and "identidade-onda1-*" in wfd,
        "o roteador lê os artefatos da onda 1 e decide com "
        "ci/rotear_segunda_onda.py")
    chk("--ondas" in wfd and "identidade-*" in wfd
        and "ci/agregar_prova.py" in wfd and "--conferir-n" in wfd
        and "download-artifact" in wfd,
        "o agregador baixa TODAS as ondas (pattern identidade-*) e julga "
        "com --ondas e --conferir-n")
    chk("needs: [planejar, dublador-onda1, rotear, dublador-onda2]" in wfd
        and "if: always() && needs.planejar.outputs.rodar == 'true'" in wfd,
        "o agregador roda SEMPRE que o job acordou — mesmo com cópia "
        "vermelha (é ele quem nomeia)")
    chk("workflow_call" in wfo and "inputs:" in wfo
        and "copia: ${{ fromJSON(inputs.copias) }}" in wfo,
        "a onda é reutilizável (workflow_call) com a matrix do input — "
        "o corpo da cópia é UM SÓ para as duas ondas")
    chk("identidade-onda${{ inputs.onda }}-${{ matrix.copia }}-run${{ github.run_id }}" in wfo,
        "o artefato da cópia carrega a onda no nome")
    chk("ci/veredito_da_copia.py" in wfo and "if: always()" in wfo,
        "o veredito.json nasce sempre (verde também) — o contrato do "
        "agregador")
    import re as _re3
    chk(not _re3.search(r"^\s*continue-on-error:", wfd, _re3.M)
        and not _re3.search(r"^\s*continue-on-error:", wfo, _re3.M),
        "o job dublador segue OBRIGATÓRIO: nenhum continue-on-error em "
        "passo nenhum dos dois workflows")
    chk("pipx install" not in wfd and "pipx install" not in wfo,
        "o gate não instala audio-suite em passo NENHUM — o instrumento "
        "de observação saiu do gate inteiro; a observação de verdade é o "
        "dispatch manual observar_avx2")

    print(f"  {len(ok)} verificações do agregador da prova por amostragem "
          f"(CP-013; ondas CP-015).")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  o veredito do run é da amostragem SOBRE AS ONDAS: a cópia não")
    print("  decide sozinha, a divergência tem onda e nome, SEM_AMOSTRA só")
    print("  nasce após duas ondas vazias, e o que não se lê, reprova.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
