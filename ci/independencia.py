#!/usr/bin/env python3
"""A independência das cópias, CALCULADA do registro (CP-014, passo 5).

A diretiva do dono (25/09/2026): "monitorar a independência das cópias"
— o N=8 do lock nasce de P(zero cópia AVX-512) <= 2% com a fração 38/97
REGISTRADA, mas fração é estimativa de um pool vivo; as execuções reais
do gate é que dizem se o modelo descreve a frota de verdade. Este módulo
lê harness/frota/execucoes-gate.json (o registro versionado, uma entrada
por TENTATIVA de run do gate) e calcula:

  A TAXA OBSERVADA DE SEM_AMOSTRA       k/n (tentativas com zero cópias
                                        AVX-512 sobre o total)
  O IC DE 95% DA TAXA                   Wilson (padrão) e
                                        Clopper-Pearson (exata,
                                        conservadora) — implementados em
                                        math puro, sem scipy
  A CORRELAÇÃO INTRA-EXECUÇÃO           as cópias AVX-512 por execução
                                        comparadas à binomial com p =
                                        38/97 (a fração do lock): a
                                        DISPERSÃO (variância observada x
                                        variância binomial; o componente
                                        de dispersão do qui-quadrado com
                                        os graus de liberdade) e a MÉDIA
                                        (fração observada x fração do
                                        lock, com o binomial exato do
                                        total)
  O VEREDITO                            NAO_INDEPENDENTE dispara SÓ se a
                                        taxa passar de 2% COM o IC de
                                        95% acima de 2% (limite inferior
                                        acima de 2%) — a regra da
                                        diretiva, aplicada aos dois ICs;
                                        e o N RECAlculado a partir da
                                        taxa observada (o que o lock
                                        deveria ancorar SE a tendência
                                        se confirmar — proposta, nunca
                                        aplicação unilateral acima de
                                        50%)

O número é reproduzível: o teste (tests/test_independencia.py) refaz
toda a aritmética a partir do registro e confere o bloco "calculo" que
está gravado nele — nada aqui é afirmado, tudo é recalculável.

Uso: ci/independencia.py [--registro harness/frota/execucoes-gate.json]
"""
import argparse
import json
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import voz                    # noqa: E402

Z95 = 1.959963984540054          # quantil 97,5% da normal padrão
ALFA = 0.05


# ---- intervalos de confiança, math puro ------------------------------------
def ic_wilson(k: int, n: int, z: float = Z95) -> tuple:
    """IC de Wilson para uma proporção — o padrão de casa."""
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1.0 + z * z / n
    centro = (p + z * z / (2 * n)) / denom
    meia = (z / denom) * math.sqrt(
        p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centro - meia), min(1.0, centro + meia))


def _binom_pmf(k: int, n: int, p: float) -> float:
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def _binom_cdf_ate(k: int, n: int, p: float) -> float:
    return sum(_binom_pmf(i, n, p) for i in range(k + 1))


def _solve(f, alvo, lo, hi, decrescente=False):
    """bisseção com direção: f crescente (default) ou decrescente."""
    for _ in range(200):
        meio = (lo + hi) / 2
        abaixo = f(meio) < alvo if not decrescente else f(meio) > alvo
        if abaixo:
            lo = meio
        else:
            hi = meio
    return (lo + hi) / 2


def ic_clopper_pearson(k: int, n: int, alfa: float = ALFA) -> tuple:
    """IC exato por busca binária nas caudas da binomial — conservador."""
    if n <= 0:
        return (0.0, 0.0)
    if k == 0:
        return (0.0, 1.0 - (alfa / 2) ** (1.0 / n))
    if k == n:
        return ((alfa / 2) ** (1.0 / n), 1.0)

    # P(X >= k | p) = alfa/2 (crescente em p)  →  limite inferior
    p_lo = _solve(lambda p: 1.0 - _binom_cdf_ate(k - 1, n, p), alfa / 2,
                  0.0, 1.0)
    # P(X <= k | p) = alfa/2 (decrescente em p)  →  limite superior
    p_hi = _solve(lambda p: _binom_cdf_ate(k, n, p), alfa / 2,
                  0.0, 1.0, decrescente=True)
    return (p_lo, p_hi)


# ---- a comparação com a binomial do lock ------------------------------------
def estatisticas_por_execucao(execucoes: list) -> dict:
    """contagens de AVX-512 por tentativa, e o básico delas."""
    contagens = [int(e.get("avx512", 0)) for e in execucoes]
    n_copias = [int(e.get("n", 0)) for e in execucoes]
    sem_amostra = [bool(e.get("sem_amostra_decisiva")) for e in execucoes]
    n = len(contagens)
    media = sum(contagens) / n if n else 0.0
    var_obs = (sum((c - media) ** 2 for c in contagens) / (n - 1)
               if n > 1 else 0.0)
    return {"contagens": contagens, "n_execucoes": n,
            "copias_por_execucao": sorted(set(n_copias)),
            "total_avx512": sum(contagens),
            "total_copias": sum(n_copias),
            "sem_amostra": sum(1 for s in sem_amostra if s),
            "media_avx512_por_execucao": round(media, 3),
            "variancia_observada": round(var_obs, 3)}


def calcular(execucoes: list, p_lock: float, n_lock: int,
             p_zero_alvo: float = 0.02) -> dict:
    """O cálculo inteiro, do registro ao veredito."""
    est = estatisticas_por_execucao(execucoes)
    n_exec = est["n_execucoes"]
    k_sem = est["sem_amostra"]

    taxa = (k_sem / n_exec) if n_exec else 0.0
    wil = ic_wilson(k_sem, n_exec)
    cp = ic_clopper_pearson(k_sem, n_exec)

    # ---- correlação intra-execução: binomial(n_lock, p_lock) -------------
    # o N por execução conferido: registro e lock têm de concordar
    n_por_exec = set(est["copias_por_execucao"])
    media_esp = n_lock * p_lock
    var_esp = n_lock * p_lock * (1 - p_lock)
    # componente de dispersão do qui-quadrado (desvio ao REDOR da média
    # observada — o que sobra depois de tirar o componente de média):
    cont = est["contagens"]
    media_obs = est["media_avx512_por_execucao"]
    disp = (sum((c - media_obs) ** 2 for c in cont) / var_esp
            if var_esp and n_exec > 1 else 0.0)
    gl_disp = n_exec - 1 if n_exec > 1 else 0
    # componente de média (desvio da média observada à esperada):
    comp_media = (n_exec * (media_obs - media_esp) ** 2 / var_esp
                  if var_esp else 0.0)
    # p-valor do qui-quadrado por sobrevivência da função gama incompleta
    p_disp = _p_quiquad(disp, gl_disp) if gl_disp else 1.0

    # a fração observada x a fração do lock (binomial exato do total)
    total_avx, total_copias = est["total_avx512"], est["total_copias"]
    p_frac_obs = (total_avx / total_copias) if total_copias else 0.0
    # P(X <= observado) sob Bin(total, p_lock) — cauda inferior
    p_cauda_frac = _binom_cdf_ate(total_avx, total_copias, p_lock) \
        if total_copias else 1.0

    # ---- o veredito da diretiva -------------------------------------------
    dispara_wilson = taxa > p_zero_alvo and wil[0] > p_zero_alvo
    dispara_cp = taxa > p_zero_alvo and cp[0] > p_zero_alvo
    nao_independente = dispara_wilson and dispara_cp

    # N recalculado a partir da taxa observada (a frota medida): o menor N
    # com P(zero) <= alvo usando a FRAÇÃO OBSERVADA por cópia
    fracao_obs = p_frac_obs
    if 0.0 < fracao_obs < 1.0:
        n_obs = 1
        while (1.0 - fracao_obs) ** n_obs > p_zero_alvo:
            n_obs += 1
        aumento = (n_obs - n_lock) / n_lock if n_lock else None
    else:
        n_obs, aumento = None, None

    return {
        "execucoes": est,
        "taxa_sem_amostra": {
            "valor": round(taxa, 5),
            "k": k_sem, "n": n_exec,
            "ic_wilson_95": [round(wil[0], 5), round(wil[1], 5)],
            "ic_clopper_pearson_95": [round(cp[0], 5), round(cp[1], 5)],
        },
        "correlacao_intra_execucao": {
            "referencia": f"binomial(N={n_lock}, p={p_lock:.5f})",
            "variancia_binomial": round(var_esp, 3),
            "variancia_observada": est["variancia_observada"],
            "razao_variancia": (round(est["variancia_observada"] / var_esp, 3)
                                if var_esp else None),
            "estatistica_quiquad_dispersao": round(disp, 3),
            "graus_de_liberdade": gl_disp,
            "p_valor_dispersao": round(p_disp, 4),
            "leitura_dispersao": (
                "sem sobredispersão detectada — as cópias de um mesmo run "
                "comportam-se como sorteios independentes"
                if p_disp > 0.05 else
                "SOBREDISPERSÃO: as cópias de um mesmo run não são "
                "sorteios independentes — correlação intra-execução"),
            "media_esperada": round(media_esp, 3),
            "media_observada": est["media_avx512_por_execucao"],
            "componente_quiquad_media": round(comp_media, 3),
            "fracao_avx512_observada": round(fracao_obs, 5),
            "fracao_do_lock": round(p_lock, 5),
            "p_cauda_binomial_total": round(p_cauda_frac, 5),
        },
        "veredito": {
            "nao_independente_dispara": nao_independente,
            "regra": ("taxa > 2% E o limite inferior do IC de 95% (Wilson e "
                      "Clopper-Pearson) acima de 2%"),
            "n_do_lock": n_lock,
            "n_recalculado_da_taxa_observada": n_obs,
            "aumento_percentual_n": (round(aumento * 100, 1)
                                     if aumento is not None else None),
            "nota": (
                f"NAO_INDEPENDENTE NÃO dispara com estes dados — a taxa "
                f"pontual está acima de 2% mas o IC cruza o limiar (limite "
                f"inferior de Wilson {wil[0]:.2%} e de Clopper-Pearson "
                f"{cp[0]:.2%}, ambos <= 2%): com {n_exec} execuções o poder "
                f"é baixo; registrar e vigiar, não concluir. A vigilância "
                f"operacional segue sendo a da CP-013: 3 disparos SEGUIDOS "
                f"de SEM_AMOSTRA recalculam o N por CP com medição nova"
                if not nao_independente else
                "NAO_INDEPENDENTE — registrar, recalcular N e propor por "
                "CP; aplicação unilateral proibida se o N subir mais de "
                "50%"),
        },
    }


def _gammq(a: float, x: float) -> float:
    """Q(a, x) = gama incompleta regularizada superior (Numerical Recipes,
    série e fração contínua) — math puro, válida para todo a > 0, x >= 0."""
    if x < 0 or a <= 0:
        return 1.0
    if x == 0:
        return 1.0
    if x < a + 1.0:                       # série de P(a, x)
        # a série começa em 1/a (denominadores a·(a+1)·…), nunca em 1
        ap, soma, termo = a, 1.0 / a, 1.0 / a
        for _ in range(1000):
            ap += 1.0
            termo *= x / ap
            soma += termo
            if abs(termo) < abs(soma) * 1e-15:
                break
        p = soma * math.exp(-x + a * math.log(x) - math.lgamma(a))
        return max(0.0, min(1.0, 1.0 - p))
    # fração contínua de Q(a, x) (Lentz, como em Numerical Recipes)
    minimo, eps = 1e-300, 3e-16
    b = x + 1.0 - a
    c = 1.0 / minimo                   # enorme: an/c ~ 0 na 1ª iteração
    d = 1.0 / b if b != 0 else 1.0 / minimo
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < minimo:
            d = minimo
        c = b + an / c
        if abs(c) < minimo:
            c = minimo
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    q = math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    return max(0.0, min(1.0, q))


def _p_quiquad(x: float, gl: int) -> float:
    """p-valor do qui-quadrado com gl graus de liberdade (sobrevivência)."""
    if gl <= 0 or x <= 0:
        return 1.0
    return _gammq(gl / 2.0, x / 2.0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--registro", default=str(
        RAIZ / "harness" / "frota" / "execucoes-gate.json"))
    args = ap.parse_args()
    doc = json.loads(Path(args.registro).read_text(encoding="utf-8"))

    fr = voz.frota()
    n_lock = int(str(fr["amostragem"]).strip())
    frac = str(fr.get("fracao_avx512f", "")).strip()
    num, den = frac.split("/")
    p_lock = int(num) / int(den)

    calc = calcular(doc["execucoes"], p_lock, n_lock)
    print("== INDEPENDÊNCIA DAS CÓPIAS (CP-014 — do registro "
          f"{Path(args.registro).name})")
    t = calc["taxa_sem_amostra"]
    print(f"   taxa SEM_AMOSTRA: {t['k']}/{t['n']} = {t['valor']:.3%}")
    print(f"   IC95 Wilson:        [{t['ic_wilson_95'][0]:.2%}, "
          f"{t['ic_wilson_95'][1]:.2%}]")
    print(f"   IC95 Clopper-Pearson: [{t['ic_clopper_pearson_95'][0]:.2%}, "
          f"{t['ic_clopper_pearson_95'][1]:.2%}]")
    c = calc["correlacao_intra_execucao"]
    print(f"   dispersão: var obs {c['variancia_observada']} x binomial "
          f"{c['variancia_binomial']} (razão {c['razao_variancia']}) — "
          f"qui-quadrado de dispersão {c['estatistica_quiquad_dispersao']} "
          f"em {c['graus_de_liberdade']} g.l., p={c['p_valor_dispersao']:.3f}")
    print(f"   média: obs {c['media_observada']} x esperada "
          f"{c['media_esperada']} — fração obs "
          f"{c['fracao_avx512_observada']:.1%} x lock "
          f"{c['fracao_do_lock']:.1%} (cauda {c['p_cauda_binomial_total']:.4f})")
    v = calc["veredito"]
    print(f"   VEREDITO: NAO_INDEPENDENTE dispara = "
          f"{v['nao_independente_dispara']}")
    if v["n_recalculado_da_taxa_observada"]:
        print(f"   N recalculado da taxa observada: "
              f"{v['n_do_lock']} -> {v['n_recalculado_da_taxa_observada']} "
              f"(+{v['aumento_percentual_n']}%)")
    print(f"   {v['nota']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
