#!/usr/bin/env python3
"""A independência das cópias e o N DA JANELA MÓVEL, recalculados do
registro (CP-014 passo 5; CP-015 passos 2 e 3).

A aceite da CP-015 é literal:
  - o diagnóstico: o excesso de SEM_AMOSTRA (2 observadas) se explica
    pela DERIVA da fração (esperado 1,16 sob p=0,268 em 14 disparos;
    P(X>=2)=32%), NÃO por dependência — sem sobredispersão em nenhum
    referencial; NAO_INDEPENDENTE não dispara (a regra dos DOIS ICs)
  - o N da janela: fração 0,268 -> 13 (o menor N com P(zero) <= 2%);
    o N do lock TEM DE BATER, senão o fiscal reprova "N desatualizado"
  - a borda: registro com menos de J execuções -> o cálculo usa todas e
    declara "janela incompleta", NUNCA inventa fração
  - a regra da diretiva (herdada da CP-014): taxa > 2% com os DOIS ICs
    de 95% acima de 2% dispara NAO_INDEPENDENTE — provada nos dois
    sentidos
  - o registro cresce por PR de manutenção; nada de commit automático

O que se prova aqui: o ci/independencia.py refaz a aritmética das 15
execuções registradas (as 14 da era CP-013/014 + a pendente do head
final da CP-014, run 36092359210) e devolve EXATAMENTE o cálculo gravado
no bloco 'calculo' do registro (o número é reproduzível, nunca afirmado);
o caso sintético com taxa alta e ICs acima de 2% DISPARA a parada; o
fiscal do N dispara "N desatualizado" quando o lock diverge da janela;
os ICs batem com valores de referência; e cada entrada do registro é
íntegra.
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
    j_lock = int(str(fr["janela"]).strip())
    num, den = str(fr["fracao_avx512f"]).split("/")
    p_lock = int(num) / int(den)

    # --- o registro existe e cada entrada é íntegra ---------------------
    doc = json.loads(REGISTRO.read_text(encoding="utf-8"))
    execucoes = doc["execucoes"]
    chk(doc["$schema"] == "estudio-suite/frota-gate@1",
        "o registro declara o esquema frota-gate@1")
    chk(len(execucoes) == 15,
        f"o registro leva as 15 execuções medidas (14 da era CP-013/014 "
        f"+ a pendente do head final da CP-014 — tem {len(execucoes)})")
    for e in execucoes:
        integro = (int(e["n"]) == len(e["copias"])
                   and int(e["avx512"]) == sum(
                       1 for v in e["copias"].values() if v == "avx512")
                   and bool(e["sem_amostra_decisiva"]) == (int(e["avx512"]) == 0))
        chk(integro,
            f"run {e['run']} t{e['tentativa']}: n={e['n']}, avx512="
            f"{e['avx512']}, sem_amostra={e['sem_amostra_decisiva']} "
            f"íntegros entre si")
        chk(bool(e.get("fonte")),
            f"run {e['run']} t{e['tentativa']}: a fonte é declarada")
    # o N da matrix é o DA ERA (8 na CP-013/014, 13 da CP-015 em diante) —
    # o fiscal vivo é o N da JANELA, não o histórico
    eras = {int(e["n"]) for e in execucoes}
    chk(eras == {8},
        f"as entradas históricas são da era N=8 (o lock anda em 13 desde "
        f"a CP-015 — eras registradas: {sorted(eras)})")
    sem_amostra = [e for e in execucoes if e["sem_amostra_decisiva"]]
    chk(len(sem_amostra) == 2
        and {e["run"] for e in sem_amostra} == {"36075600630", "36091333340"}
        and all(e["tentativa"] == 1 for e in sem_amostra),
        "as DUAS SEM_AMOSTRA_DECISIVA reais (36075600630 t1 da CP-013 e "
        "36091333340 t1 da CP-014 — ambas devolvidas pelo rerun) estão "
        "registradas com a fonte declarada")
    pendente = [e for e in execucoes if e["run"] == "36092359210"]
    chk(len(pendente) == 1 and pendente[0]["avx512"] == 2
        and pendente[0]["sem_amostra_decisiva"] is False
        and pendente[0].get("head_do_pr") == "f545dde",
        "a execução pendente do head final da CP-014 entrou no registro "
        "(run 36092359210: 2 AVX-512 idênticas, 6 avx2, verde; head_do_pr "
        "f545dde declarado — a fronteira do regresso cumprida)")

    # --- o cálculo gravado == o cálculo recalculado ---------------------
    calc = ind.calcular_do_registro(doc)
    gravado = doc["calculo"]
    chk(gravado == calc,
        "o bloco calculo gravado == o recalculado por "
        "calcular_do_registro (o caminho único — nada é afirmado)")

    # --- a JANELA MÓVEL e o fiscal do N ---------------------------------
    ja = calc["janela"]
    chk(ja["j"] == j_lock and ja["execucoes_na_janela"] == 15
        and ja["janela_incompleta"] is True,
        f"a janela é J={j_lock} do lock; com 15 execuções ela declara "
        f"INCOMPLETA e usa TODAS — nunca inventa fração")
    chk(ja["copias_na_janela"] == 120 and ja["avx512_na_janela"] == 32
        and abs(ja["fracao"] - 32 / 120) < 1e-5,
        "a fração da janela soma as cópias das 15 execuções: 32/120 = "
        f"{32 / 120:.5f}")
    chk(ja["n_recalculado"] == 13 and ja["n_do_lock"] == n_lock == 13
        and ja["n_conforme"] is True
        and abs(ja["p_zero_no_n"] - (1 - 32 / 120) ** 13) < 1e-4,
        f"o N recalculado da janela é {ja['n_recalculado']} "
        f"(P(zero)={ja['p_zero_no_n']:.5f} <= 2%) e BATE com o lock "
        f"({n_lock}) — o fiscal não reprova")
    chk(ja["nota"].startswith("o N do lock bate"),
        "a nota da janela declara a conformidade (o teste reprovaria 'N "
        "desatualizado' se divergisse)")

    # --- o fiscal: lock com outro N -> "N desatualizado" ----------------
    calc_desat = ind.calcular(execucoes, p_lock, 8, janela=j_lock)
    chk(calc_desat["janela"]["n_desatualizado"] is True
        if "n_desatualizado" in calc_desat["janela"] else
        calc_desat["veredito"]["n_desatualizado"] is True,
        "lock com N=8 (o valor antigo) contra a janela que calcula 13 -> "
        "N DESATUALIZADO — o fiscal reprova; a mudança é PR de manutenção")
    chk("N DESATUALIZADO" in calc_desat["janela"]["nota"],
        "a nota do fiscal nomeia o caminho: PR de manutenção, commit "
        "automático jamais")

    # --- a função pura: fração 0,268 -> N=13 (o caso dos testes da CP) --
    chk(ind.menor_n_com_p_zero(0.268, 0.02) == 13,
        "menor N com P(zero) <= 2% para a fração 0,268 é 13 "
        "(0,732^12 = 2,37% > 2%; 0,732^13 = 1,74% <= 2%)")
    chk(ind.menor_n_com_p_zero(0.39175, 0.02) == 8,
        "a fração congelada 38/97 dá o N histórico 8 — a origem da CP-013 "
        "reproduzida pela MESMA função")
    try:
        ind.menor_n_com_p_zero(0.0, 0.02)
        chk(False, "fração 0 levanta (sem N honesto)")
    except ValueError:
        chk(True, "fração fora de (0,1) levanta — nunca inventa N")

    # --- a borda: menos de J -> usa todas, declara incompleta -----------
    sinteticas3 = [{"n": 8, "avx512": 2, "sem_amostra_decisiva": False,
                    "copias": {f"c{i}": ("avx512" if i < 2 else "avx2")
                               for i in range(8)}} for _ in range(3)]
    calc3 = ind.calcular(sinteticas3, p_lock, n_lock, janela=20)
    j3 = calc3["janela"]
    chk(j3["execucoes_na_janela"] == 3 and j3["janela_incompleta"] is True
        and j3["copias_na_janela"] == 24 and j3["fracao"] == round(6 / 24, 5),
        "registro com 3 execuções e J=20: usa as 3, declara INCOMPLETA, a "
        "fração vem das cópias que existem — nunca inventada")

    # --- o diagnóstico da CP-015, conferido ------------------------------
    t = calc["taxa_sem_amostra"]
    chk(t["k"] == 2 and t["n"] == 15,
        "2 SEM_AMOSTRA em 15 execuções (as duas históricas; a pendente é "
        "verde — o desenho novo ainda não sorteou duas ondas vazias)")
    chk(abs(t["valor"] - 2 / 15) < 1e-5,
        "a taxa é 2/15 = 13,33%")
    chk(t["ic_wilson_95"][0] > 0.02,
        "o IC de Wilson está INTEIRO acima de 2% (limite inferior "
        f"{t['ic_wilson_95'][0]:.2%}) — sozinho, dispararia")
    chk(t["ic_clopper_pearson_95"][0] <= 0.02,
        "o IC de Clopper-Pearson CRUZA 2% (limite inferior "
        f"{t['ic_clopper_pearson_95'][0]:.2%}) — é ele que segura a regra "
        "dos DOIS ICs: o QUASE é o estado registrado, não um segredo")
    v = calc["veredito"]
    chk(v["nao_independente_dispara"] is False,
        "NAO_INDEPENDENTE NÃO dispara (os dois ICs acima é a regra)")
    # a fronteira honesta: uma ocorrência a mais (3 em 16) cruza os DOIS
    chk(ind.ic_clopper_pearson(3, 16)[0] > 0.02
        and ind.ic_wilson(3, 16)[0] > 0.02,
        "a fronteira medida: 3 SEM_AMOSTRA em 16 execuções põem os DOIS "
        "ICs acima de 2% e a parada dispara — a uma ocorrência de "
        "distância, e o registro diz isso")

    # --- a correlação intra-execução: homogeneidade com n por execução --
    c = calc["correlacao_intra_execucao"]
    chk(c["p_valor_homogeneidade"] > 0.05,
        f"homogeneidade sem sobredispersão (p={c['p_valor_homogeneidade']:.3f} "
        f"> 0,05): as cópias de um mesmo run são sorteios independentes")
    chk(abs(c["quiquad_homogeneidade"] - 19.006) < 0.01
        and c["graus_de_liberdade"] == 14,
        f"o qui-quadrado de homogeneidade é {c['quiquad_homogeneidade']} "
        f"em 14 g.l. (15 execuções — o diagnóstico da CP foi declarado "
        f"com as 14 primeiras: 18,94 em 13 g.l., p≈0,12; a pendente "
        f"entra e o número é RECALCULADO, nunca afirmado)")
    chk(c["fracao_da_janela"] < c["fracao_congelada_do_lock"]
        and c["p_cauda_binomial_total"] < 0.05,
        "a fração da janela (%.1f%%) está ABAIXO da congelada (%.1f%%), "
        "cauda binomial %.4f — pool vivo registrado: o POOL mudou, o "
        "sorteio não" % (100 * c["fracao_da_janela"],
                         100 * c["fracao_congelada_do_lock"],
                         c["p_cauda_binomial_total"]))

    # --- a regra da diretiva, provada nos dois sentidos ------------------
    # caso sintético: 6 SEM_AMOSTRA em 10 — taxa 60%, IC inferior >> 2%
    sinteticas = ([{"n": 8, "avx512": 0, "sem_amostra_decisiva": True,
                    "copias": {f"c{i}": "avx2" for i in range(8)}}
                  for _ in range(6)] +
                 [{"n": 8, "avx512": 2, "sem_amostra_decisiva": False,
                   "copias": {**{f"c{i}": "avx512" for i in range(2)},
                              **{f"c{i}": "avx2" for i in range(2, 8)}}}
                  for _ in range(4)])
    calc2 = ind.calcular(sinteticas, p_lock, n_lock, janela=j_lock)
    chk(calc2["veredito"]["nao_independente_dispara"] is True,
        "6/10 com os DOIS ICs acima de 2%: NAO_INDEPENDENTE DISPARA (a "
        "regra da diretiva, provada no sentido que para)")
    chk(calc2["taxa_sem_amostra"]["ic_wilson_95"][0] > 0.02
        and calc2["taxa_sem_amostra"]["ic_clopper_pearson_95"][0] > 0.02,
        "no caso que dispara, os DOIS ICs estão acima de 2%")
    # taxa acima de 2% com IC ABAIXO (poucas execuções) NÃO dispara
    poucas = ([{"n": 8, "avx512": 0, "sem_amostra_decisiva": True,
                "copias": {f"c{i}": "avx2" for i in range(8)}}] +
              [{"n": 8, "avx512": 2, "sem_amostra_decisiva": False,
                "copias": {**{f"c{i}": "avx512" for i in range(2)},
                           **{f"c{i}": "avx2" for i in range(2, 8)}}}
               for _ in range(4)])
    calc3b = ind.calcular(poucas, p_lock, n_lock, janela=j_lock)
    chk(calc3b["taxa_sem_amostra"]["valor"] > 0.02
        and calc3b["taxa_sem_amostra"]["ic_clopper_pearson_95"][0] <= 0.02
        and calc3b["veredito"]["nao_independente_dispara"] is False,
        "taxa 20% (1/5) com o IC conservador cruzando 2%: NÃO dispara — "
        "a regra exige os DOIS ICs acima; poder baixo não é evidência")

    # --- os ICs batem com valores de referência ------------------------
    chk(abs(ind.ic_wilson(1, 11)[0] - 0.01623) < 2e-4
        and abs(ind.ic_wilson(1, 11)[1] - 0.37736) < 2e-4,
        "Wilson 1/11 ≈ [1,62%; 37,74%]")
    chk(abs(ind.ic_clopper_pearson(1, 11)[0] - 0.00231) < 2e-4,
        "Clopper-Pearson 1/11 lower ≈ 0,23%")
    chk(abs(ind.ic_clopper_pearson(0, 10)[1] - (1 - 0.025 ** 0.1)) < 1e-9,
        "Clopper-Pearson 0/10 upper = 1-(0,025)^(1/10) — a borda exata")
    chk(abs(ind.ic_clopper_pearson(10, 10)[0] - 0.025 ** 0.1) < 1e-9,
        "Clopper-Pearson 10/10 lower = (0,025)^(1/10)")
    chk(abs(ind._p_quiquad(10.0, 10) - 0.4405) < 1e-3,
        "p(chi2 10 >= 10) ≈ 0,4405 (tabela)")
    chk(abs(ind._p_quiquad(3.841, 1) - 0.05) < 1e-3,
        "p(chi2 1 >= 3,841) ≈ 0,05 (tabela)")
    k, n = 1, 11
    p_hi = ind.ic_clopper_pearson(k, n)[1]
    chk(abs(ind._binom_cdf_ate(k, n, p_hi) - 0.025) < 1e-6,
        "no limite superior da CP, P(X<=k) = 0,025 exato (a definição)")

    # --- o registro cresce por PR de manutenção -------------------------
    chk("commit automático" in doc["como_cresce"].lower(),
        "o registro declara como cresce: por PR de manutenção, sem commit "
        "automático no main")
    chk("fronteira" in doc["como_cresce"],
        "a fronteira do regresso é declarada: o PR que fecha o registro "
        "leva as execuções medidas até o seu último commit; a do commit "
        "final entra no próximo PR de manutenção")

    print(f"  {len(ok)} verificações da independência e da janela (CP-014/"
          f"CP-015).")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  a janela calcula 13 e o lock ancora 13: CONFORME. A taxa 2/15")
    print("  com o Wilson acima e o CP cruzando segue a uma ocorrência de")
    print("  distância; sem sobredispersão; fração da janela abaixo da")
    print("  congelada: o pool mudou, o sorteio não — vigiado com número.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
