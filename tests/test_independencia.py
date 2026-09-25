#!/usr/bin/env python3
"""A independência das cópias, recalculada do registro (CP-014, passo 5).

A aceite da CP-014 é literal:
  - a taxa observada de SEM_AMOSTRA e a correlação intra-execução estão
    CALCULADAS e REGISTRADAS — no bloco 'calculo' de
    harness/frota/execucoes-gate.json, recalculável daqui
  - a regra da diretiva: taxa > 2% com IC de 95% acima de 2% (limite
    inferior acima de 2%) dispara NAO_INDEPENDENTE — nos DOIS ICs
    (Wilson e Clopper-Pearson)
  - o registro cresce por PR de manutenção; nada de commit automático

O que se prova aqui: o ci/independencia.py refaz a aritmética das 11
execuções registradas e devolve EXATAMENTE o cálculo gravado (o número
é reproduzível, nunca afirmado); o caso sintético com taxa alta e IC
acima de 2% DISPARA a parada e recalcula o N; os ICs batem com valores
de referência (Wilson 1/11; Clopper-Pearson nas bordas); e cada entrada
do registro é íntegra (n == len(copias), avx512 conferível, N do lock
confere com o tamanho das matrizes registradas).
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

_spec = importlib.util.spec_from_file_location(
    "independencia", RAIZ / "ci" / "independencia.py")
ind = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ind)

REGISTRO = RAIZ / "harness" / "frota" / "execucoes-gate.json"

ok, bad = [], []


def chk(c, msg):
    (ok if c else bad).append(msg)


def main():
    from estudio_suite import voz
    fr = voz.frota()
    n_lock = int(str(fr["amostragem"]).strip())
    num, den = str(fr["fracao_avx512f"]).split("/")
    p_lock = int(num) / int(den)

    # --- o registro existe e cada entrada é íntegra ---------------------
    doc = json.loads(REGISTRO.read_text(encoding="utf-8"))
    execucoes = doc["execucoes"]
    chk(doc["$schema"] == "estudio-suite/frota-gate@1",
        "o registro declara o esquema frota-gate@1")
    chk(len(execucoes) >= 11,
        f"o registro leva as execuções medidas (tem {len(execucoes)})")
    for e in execucoes:
        integro = (int(e["n"]) == len(e["copias"])
                   and int(e["avx512"]) == sum(
                       1 for v in e["copias"].values() if v == "avx512")
                   and bool(e["sem_amostra_decisiva"]) == (int(e["avx512"]) == 0))
        chk(integro,
            f"run {e['run']} t{e['tentativa']}: n={e['n']}, avx512="
            f"{e['avx512']}, sem_amostra={e['sem_amostra_decisiva']} "
            f"íntegros entre si")
        chk(int(e["n"]) == n_lock,
            f"run {e['run']} t{e['tentativa']}: matrix N={e['n']} == N do "
            f"lock ({n_lock})")
        chk(bool(e.get("fonte")),
            f"run {e['run']} t{e['tentativa']}: a fonte é declarada")
    sem_amostra = [e for e in execucoes if e["sem_amostra_decisiva"]]
    chk(len(sem_amostra) == 2
        and {e["run"] for e in sem_amostra} == {"36075600630", "36091333340"}
        and all(e["tentativa"] == 1 for e in sem_amostra),
        "as DUAS SEM_AMOSTRA_DECISIVA reais (36075600630 t1 da CP-013 e "
        "36091333340 t1 da CP-014 — ambas devolvidas pelo rerun) estão "
        "registradas com a fonte declarada")

    # --- o cálculo gravado == o cálculo recalculado ---------------------
    calc = ind.calcular(execucoes, p_lock, n_lock)
    gravado = doc["calculo"]
    chk(gravado["taxa_sem_amostra"]["valor"] == calc["taxa_sem_amostra"]["valor"]
        and gravado["taxa_sem_amostra"]["k"] == calc["taxa_sem_amostra"]["k"]
        and gravado["taxa_sem_amostra"]["n"] == calc["taxa_sem_amostra"]["n"],
        f"taxa gravada == recalculada: {calc['taxa_sem_amostra']['k']}/"
        f"{calc['taxa_sem_amostra']['n']}")
    chk(gravado["taxa_sem_amostra"]["ic_wilson_95"]
        == calc["taxa_sem_amostra"]["ic_wilson_95"],
        "IC de Wilson gravado == recalculado")
    chk(gravado["taxa_sem_amostra"]["ic_clopper_pearson_95"]
        == calc["taxa_sem_amostra"]["ic_clopper_pearson_95"],
        "IC de Clopper-Pearson gravado == recalculado")
    chk(gravado["correlacao_intra_execucao"]["estatistica_quiquad_dispersao"]
        == calc["correlacao_intra_execucao"]["estatistica_quiquad_dispersao"]
        and gravado["correlacao_intra_execucao"]["p_valor_dispersao"]
        == calc["correlacao_intra_execucao"]["p_valor_dispersao"],
        "a dispersão gravada == recalculada (qui-quadrado e p-valor)")
    chk(gravado["veredito"]["nao_independente_dispara"]
        == calc["veredito"]["nao_independente_dispara"] is False,
        "o veredito gravado == recalculado: NAO_INDEPENDENTE não dispara "
        "(a regra declarada exige os DOIS ICs; o Wilson dispara sozinho e "
        "o CP cruza — o quase está registrado)")

    # --- os números que a CP-014 registra, conferidos -------------------
    t = calc["taxa_sem_amostra"]
    chk(t["k"] == 2 and t["n"] == 14,
        "2 SEM_AMOSTRA em 14 execuções (a medição da CP-014, com a "
        "2ª ocorrência real no próprio fechamento)")
    chk(abs(t["valor"] - 2 / 14) < 1e-5,
        "a taxa é 2/14 = 14,29%")
    chk(t["ic_wilson_95"][0] > 0.02,
        "o IC de Wilson está INTEIRO acima de 2% (limite inferior 4,01%) — "
        "o Wilson, sozinho, dispararia")
    chk(t["ic_clopper_pearson_95"][0] <= 0.02,
        "o IC de Clopper-Pearson CRUZA 2% (limite inferior 1,78%) — é ele "
        "que segura a regra declarada (os DOIS ICs), por 0,22 pontos: o "
        "QUASE-disparar é o estado registrado, não um segredo")
    c = calc["correlacao_intra_execucao"]
    chk(0.05 < c["p_valor_dispersao"],
        "dispersão sem sobredispersão (p=%.3f > 0,05): as cópias de um "
        "mesmo run são sorteios independentes" % c["p_valor_dispersao"])
    chk(abs(c["razao_variancia"] - 1.0) < 0.25,
        "variância observada ~ binomial (razão %.2f): sem correlação "
        "intra-execução" % c["razao_variancia"])
    chk(c["fracao_avx512_observada"] < c["fracao_do_lock"]
        and c["p_cauda_binomial_total"] < 0.05,
        "a fração da era CP-013 (%.1f%%) está ABAIXO da fração do lock "
        "(%.1f%%), cauda binomial %.4f — pool vivo registrado, sem "
        "concluir" % (100 * c["fracao_avx512_observada"],
                      100 * c["fracao_do_lock"],
                      c["p_cauda_binomial_total"]))
    v = calc["veredito"]
    chk(v["n_recalculado_da_taxa_observada"] == 13
        and v["aumento_percentual_n"] == 62.5,
        "o N condicional (se a fração se confirmar) é 13, +62,5% — acima "
        "dos 50%: aplicação unilateral proibida, proposta por CP")
    # a fronteira honesta: UMA ocorrência a mais (3 em 15) cruza o CP e a
    # parada dispara — o teste declara o quase
    chk(ind.ic_clopper_pearson(3, 15)[0] > 0.02
        and ind.ic_wilson(3, 15)[0] > 0.02,
        "a fronteira medida: 3 SEM_AMOSTRA em 15 execuções põem os DOIS "
        "ICs acima de 2% e NAO_INDEPENDENTE dispara — a parada está a uma "
        "ocorrência de distância, e o registro diz isso")

    # --- a regra da diretiva, provada nos dois sentidos -----------------
    # caso sintético: 6 SEM_AMOSTRA em 10 — taxa 60%, IC inferior >> 2%
    sinteticas = [{"n": 8, "avx512": 0, "sem_amostra_decisiva": True,
                   "copias": {f"c{i}": "avx2" for i in range(8)}} for _ in range(6)] + \
                 [{"n": 8, "avx512": 2, "sem_amostra_decisiva": False,
                   "copias": {**{f"c{i}": "avx512" for i in range(2)},
                              **{f"c{i}": "avx2" for i in range(2, 8)}}}
                  for _ in range(4)]
    calc2 = ind.calcular(sinteticas, p_lock, n_lock)
    chk(calc2["veredito"]["nao_independente_dispara"] is True,
        "6/10 com IC acima de 2%: NAO_INDEPENDENTE DISPARA (a regra da "
        "diretiva, provada no sentido que para)")
    chk(calc2["taxa_sem_amostra"]["ic_wilson_95"][0] > 0.02
        and calc2["taxa_sem_amostra"]["ic_clopper_pearson_95"][0] > 0.02,
        "no caso que dispara, os DOIS ICs estão acima de 2%")
    # taxa acima de 2% com IC ABAIXO (poucas execuções) NÃO dispara:
    # 1 SEM_AMOSTRA em 5 — Wilson lower ~1,7% cruza o limiar
    poucas = ([{"n": 8, "avx512": 0, "sem_amostra_decisiva": True,
                "copias": {f"c{i}": "avx2" for i in range(8)}}] +
               [{"n": 8, "avx512": 2, "sem_amostra_decisiva": False,
                 "copias": {**{f"c{i}": "avx512" for i in range(2)},
                            **{f"c{i}": "avx2" for i in range(2, 8)}}}
                for _ in range(4)])
    calc3 = ind.calcular(poucas, p_lock, n_lock)
    chk(calc3["taxa_sem_amostra"]["valor"] > 0.02
        and calc3["taxa_sem_amostra"]["ic_clopper_pearson_95"][0] <= 0.02
        and calc3["veredito"]["nao_independente_dispara"] is False,
        "taxa 20% (1/5) com o IC conservador (Clopper-Pearson) cruza 2%: "
        "NÃO dispara — a regra exige os DOIS ICs acima do limiar; o poder "
        "baixo não é evidência de dependência")

    # --- os ICs batem com valores de referência ------------------------
    chk(abs(ind.ic_wilson(1, 11)[0] - 0.01623) < 2e-4
        and abs(ind.ic_wilson(1, 11)[1] - 0.37736) < 2e-4,
        "Wilson 1/11 ≈ [1,62%; 37,74%]")
    chk(abs(ind.ic_clopper_pearson(1, 11)[0] - 0.00231) < 2e-4,
        "Clopper-Pearson 1/11 lower ≈ 0,23%")
    # bordas exatas: k=0 e k=n
    chk(abs(ind.ic_clopper_pearson(0, 10)[1] - (1 - 0.025 ** 0.1)) < 1e-9,
        "Clopper-Pearson 0/10 upper = 1-(0,025)^(1/10) — a borda exata")
    chk(abs(ind.ic_clopper_pearson(10, 10)[0] - 0.025 ** 0.1) < 1e-9,
        "Clopper-Pearson 10/10 lower = (0,025)^(1/10)")
    # qui-quadrado contra a tabela
    chk(abs(ind._p_quiquad(10.0, 10) - 0.4405) < 1e-3,
        "p(chi2 10 >= 10) ≈ 0,4405 (tabela)")
    chk(abs(ind._p_quiquad(3.841, 1) - 0.05) < 1e-3,
        "p(chi2 1 >= 3,841) ≈ 0,05 (tabela)")
    # a definição dos limites CP: a cauda no ponto é o alfa
    k, n = 1, 11
    p_hi = ind.ic_clopper_pearson(k, n)[1]
    chk(abs(ind._binom_cdf_ate(k, n, p_hi) - 0.025) < 1e-6,
        "no limite superior da CP, P(X<=k) = 0,025 exato (a definição)")

    # --- o registro cresce por PR de manutenção -------------------------
    chk("commit automático" in doc["como_cresce"].lower().replace("automático", "automático"),
        "o registro declara como cresce: por PR de manutenção, sem commit "
        "automático no main")
    chk("fronteira" in doc["como_cresce"],
        "a fronteira do regresso é declarada: o PR que fecha o registro "
        "leva as execuções medidas até o seu último commit; a do commit "
        "final entra no próximo PR de manutenção")

    print(f"  {len(ok)} verificações da independência das cópias (CP-014).")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  a taxa e a correlação são recalculadas do registro: 2/14 com")
    print("  o Wilson acima de 2% e o CP cruzando — a regra dos dois ICs")
    print("  segura a parada a uma ocorrência de distância; sem")
    print("  sobredispersão e fração abaixo do lock: vigiado com número.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
