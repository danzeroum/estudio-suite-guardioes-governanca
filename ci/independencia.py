#!/usr/bin/env python3
"""A independência das cópias e o N DA JANELA MÓVEL, CALCULADOS do
registro (CP-014 passo 5; CP-015 passos 2 e 3).

A diretiva do dono (25/09/2026): "N pela fração da janela móvel da
frota; segunda onda automática quando a primeira não tiver AVX-512;
rerun humano deixa de ser o caminho de volta." Este módulo lê
harness/frota/execucoes-gate.json (o registro versionado, uma entrada
por TENTATIVA de run do gate) e calcula:

  A JANELA MÓVEL                  as últimas J execuções do registro (J
                                  do bloco frota do voz.lock — um lugar
                                  só). Com menos de J execuções, o
                                  cálculo usa TODAS e declara "janela
                                  incompleta" — nunca inventa fração.
  A FRAÇÃO DA JANELA              avx512/copias das execuções da janela
                                  — a fração VIVA da frota (a 38/97 do
                                  lock é a origem congelada da CP-013).
  O N RECALCULADO                 o menor N com P(zero AVX-512) <= 2%
                                  sobre a fração da janela — e o FISCAL:
                                  o N do lock tem de BATER com ele, senão
                                  "N desatualizado" (o teste reprova; a
                                  mudança entra por PR de manutenção).
  A TAXA OBSERVADA DE SEM_AMOSTRA k/n sobre TODAS as tentativas
                                  registradas (histórico; com a segunda
                                  onda, SEM_AMOSTRA só nasce após duas
                                  ondas vazias).
  O IC DE 95% DA TAXA             Wilson (padrão) e Clopper-Pearson
                                  (exata, conservadora) — math puro.
  A CORRELAÇÃO INTRA-EXECUÇÃO     as cópias AVX-512 por execução da
                                  janela comparadas à binomial com p =
                                  fração da janela: o qui-quadrado de
                                  HOMOGENEIDADE com o n de CADA execução
                                  (execuções de eras diferentes têm n
                                  diferente — 8, 13, 26 com duas ondas —
                                  e o teste padrão por execução é o que
                                  soma certinho); e a MÉDIA (fração da
                                  janela x fração congelada do lock,
                                  com o binomial exato do total).
  O VEREDITO                      NAO_INDEPENDENTE dispara SÓ se a taxa
                                  passar de 2% COM os DOIS ICs de 95%
                                  acima de 2% (limite inferior acima de
                                  2%) — a regra da CP-014, intocada; e o
                                  N desatualizado é apontado sem disparar
                                  parada (a correção é PR de manutenção).

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


# ---- o N da janela móvel (CP-015, passo 3) ---------------------------------
def menor_n_com_p_zero(p: float, alvo: float = 0.02) -> int:
    """O menor N com P(zero AVX-512 em N cópias) <= alvo, dado p — a
    definição literal da diretiva. p fora de (0,1) não tem resposta
    honesta: levanta (o chamador nomeia)."""
    if not (0.0 < p < 1.0):
        raise ValueError(f"fração {p!r} fora de (0,1) — sem N honesto")
    n = 1
    while (1.0 - p) ** n > alvo:
        n += 1
    return n


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


# ---- a comparação com a binomial da janela ---------------------------------
def estatisticas_por_execucao(execucoes: list) -> dict:
    """contagens de AVX-512 por tentativa (com o n de cada uma), e o básico."""
    contagens = [int(e.get("avx512", 0)) for e in execucoes]
    n_copias = [int(e.get("n", 0)) for e in execucoes]
    sem_amostra = [bool(e.get("sem_amostra_decisiva")) for e in execucoes]
    n = len(contagens)
    media = sum(contagens) / n if n else 0.0
    var_obs = (sum((c - media) ** 2 for c in contagens) / (n - 1)
               if n > 1 else 0.0)
    return {"contagens": contagens, "n_execucoes": n,
            "n_por_execucao": n_copias,
            "total_avx512": sum(contagens),
            "total_copias": sum(n_copias),
            "sem_amostra": sum(1 for s in sem_amostra if s),
            "media_avx512_por_execucao": round(media, 3),
            "variancia_observada": round(var_obs, 3)}


def calcular(execucoes: list, p_lock: float, n_lock: int,
             janela: int = None, p_zero_alvo: float = 0.02) -> dict:
    """O cálculo inteiro, do registro ao veredito.

    p_lock/n_lock: a fração CONGELADA (origem CP-013, 38/97) e o N atual
    do lock — o fiscal "N desatualizado" compara o N da janela com este.
    janela: J do lock; None usa todas as execuções (sem janela declarada).
    """
    est = estatisticas_por_execucao(execucoes)
    n_exec = est["n_execucoes"]
    k_sem = est["sem_amostra"]

    # ---- a janela móvel (CP-015): as últimas J execuções ----------------
    j = int(janela) if janela else None
    if j and j > 0:
        janela_execs = execucoes[-j:]
        incompleta = len(execucoes) < j
    else:
        janela_execs = execucoes
        incompleta = False
    est_j = estatisticas_por_execucao(janela_execs)
    total_avx_j, total_copias_j = est_j["total_avx512"], est_j["total_copias"]
    p_janela = (total_avx_j / total_copias_j) if total_copias_j else None

    # o N recalculado da fração da janela — e o FISCAL do lock
    if p_janela is not None and 0.0 < p_janela < 1.0:
        n_janela = menor_n_com_p_zero(p_janela, p_zero_alvo)
        p_zero_no_n = (1.0 - p_janela) ** n_janela
        n_conforme = (n_janela == n_lock)
    else:
        n_janela, p_zero_no_n, n_conforme = None, None, False

    taxa = (k_sem / n_exec) if n_exec else 0.0
    wil = ic_wilson(k_sem, n_exec)
    cp = ic_clopper_pearson(k_sem, n_exec)

    # ---- correlação intra-execução: binomial(p = fração da janela) ------
    # qui-quadrado de HOMOGENEIDADE com o n de CADA execução da janela
    # (X² = Σ (obs−n·p)²/(n·p·(1−p)), g.l. = E−1): execuções de eras
    # diferentes têm n diferente (8, 13, 26 com duas ondas) e este é o
    # teste que soma certinho; a fração pooled é o estimador, então o
    # componente de média é zero por construção — sobrou só dispersão
    cont_j = est_j["contagens"]
    n_por_exec_j = est_j["n_por_execucao"]
    homog = dispersao = None
    gl = len(cont_j) - 1 if len(cont_j) > 1 else 0
    if p_janela is not None and 0.0 < p_janela < 1.0 and gl > 0:
        homog = sum((o - ni * p_janela) ** 2 / (ni * p_janela * (1 - p_janela))
                    for o, ni in zip(cont_j, n_por_exec_j) if ni > 0)
        p_homog = _p_quiquad(homog, gl)
        # a leitura histórica (CP-014): dispersão ao redor da MÉDIA
        # observada contra a variância binomial do lock com n_lock — só
        # faz sentido quando a janela é toda do mesmo n; publicada como
        # referência de era quando for o caso
        if len(set(n_por_exec_j)) == 1 and n_por_exec_j[0] == n_lock:
            var_esp = n_lock * p_lock * (1 - p_lock)
            media_obs_j = est_j["media_avx512_por_execucao"]
            dispersao = (sum((c - media_obs_j) ** 2 for c in cont_j) / var_esp
                         if var_esp else 0.0)
    else:
        p_homog = 1.0

    # a fração da janela x a fração congelada do lock (binomial exato)
    p_cauda_frac = (_binom_cdf_ate(total_avx_j, total_copias_j, p_lock)
                    if total_copias_j else 1.0)

    # ---- o veredito da diretiva -------------------------------------------
    dispara_wilson = taxa > p_zero_alvo and wil[0] > p_zero_alvo
    dispara_cp = taxa > p_zero_alvo and cp[0] > p_zero_alvo
    nao_independente = dispara_wilson and dispara_cp

    janela_doc = {
        "j": j,
        "execucoes_na_janela": est_j["n_execucoes"],
        "janela_incompleta": bool(incompleta),
        "copias_na_janela": total_copias_j,
        "avx512_na_janela": total_avx_j,
        "fracao": round(p_janela, 5) if p_janela is not None else None,
        "p_zero_no_n": round(p_zero_no_n, 5) if p_zero_no_n is not None else None,
        "n_recalculado": n_janela,
        "n_do_lock": n_lock,
        "n_conforme": bool(n_conforme),
        "nota": (
            "o N do lock bate com o recalculado da janela (CP-015: o teste "
            "reprova 'N desatualizado' se divergir)"
            if n_conforme else
            f"N DESATUALIZADO: o lock ancora {n_lock} e a janela calcula "
            f"{n_janela} com a fração {p_janela:.5f} — PR de manutenção é o "
            f"caminho, commit automático jamais" if n_janela is not None else
            "sem cópias na janela: fração indefinida — nada afirmado"),
    }

    return {
        "execucoes": est,
        "taxa_sem_amostra": {
            "valor": round(taxa, 5),
            "k": k_sem, "n": n_exec,
            "ic_wilson_95": [round(wil[0], 5), round(wil[1], 5)],
            "ic_clopper_pearson_95": [round(cp[0], 5), round(cp[1], 5)],
        },
        "janela": janela_doc,
        "correlacao_intra_execucao": {
            "referencia": (f"binomial(p={p_janela:.5f} da janela, "
                           f"n por execução)" if p_janela is not None
                           else "sem janela"),
            "quiquad_homogeneidade": (round(homog, 3)
                                      if homog is not None else None),
            "graus_de_liberdade": gl,
            "p_valor_homogeneidade": round(p_homog, 4),
            "leitura_dispersao": (
                "sem sobredispersão detectada — as cópias de um mesmo run "
                "comportam-se como sorteios independentes"
                if p_homog > 0.05 else
                "SOBREDISPERSÃO: as cópias de um mesmo run não são "
                "sorteios independentes — correlação intra-execução"),
            "dispersao_vs_lock_da_era": (round(dispersao, 3)
                                         if dispersao is not None else None),
            "fracao_da_janela": (round(p_janela, 5)
                                 if p_janela is not None else None),
            "fracao_congelada_do_lock": round(p_lock, 5),
            "p_cauda_binomial_total": round(p_cauda_frac, 5),
        },
        "veredito": {
            "nao_independente_dispara": nao_independente,
            "regra": ("taxa > 2% E o limite inferior do IC de 95% (Wilson e "
                      "Clopper-Pearson) acima de 2%"),
            "n_do_lock": n_lock,
            "n_recalculado_da_janela": n_janela,
            "n_desatualizado": bool(n_janela is not None
                                    and n_janela != n_lock),
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


def calcular_do_registro(doc: dict) -> dict:
    """O bloco 'calculo' inteiro de um registro — J, N e p_zero do LOCK
    (o lugar único), p_lock da origem congelada. É esta função que o
    ci/atualizar_registro_frota.py usa para regravar o bloco e o teste
    usa para reconferir: um caminho só, número reproduzível."""
    fr = voz.frota()
    n_lock = int(str(fr["amostragem"]).strip())
    frac = str(fr.get("fracao_avx512f", "")).strip()
    num, den = frac.split("/")
    p_lock = int(num) / int(den)
    p_zero = float(str(fr.get("p_zero_2pct", "0.02")).strip() or "0.02")
    j = int(str(fr.get("janela", "0")).strip() or "0") or None
    return calcular(doc["execucoes"], p_lock, n_lock, janela=j,
                    p_zero_alvo=p_zero)


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
    j = int(str(fr.get("janela", "0")).strip() or "0") or None

    calc = calcular(doc["execucoes"], p_lock, n_lock, janela=j)
    print("== INDEPENDÊNCIA DAS CÓPIAS E N DA JANELA (CP-014/CP-015 — do "
          f"registro {Path(args.registro).name})")
    t = calc["taxa_sem_amostra"]
    print(f"   taxa SEM_AMOSTRA (histórico do registro): "
          f"{t['k']}/{t['n']} = {t['valor']:.3%}")
    print(f"   IC95 Wilson:        [{t['ic_wilson_95'][0]:.2%}, "
          f"{t['ic_wilson_95'][1]:.2%}]")
    print(f"   IC95 Clopper-Pearson: [{t['ic_clopper_pearson_95'][0]:.2%}, "
          f"{t['ic_clopper_pearson_95'][1]:.2%}]")
    ja = calc["janela"]
    incompleta = (" (JANELA INCOMPLETA — o cálculo usa todas, nunca "
                  "inventa fração)" if ja["janela_incompleta"] else "")
    print(f"   janela: J={ja['j']} | {ja['execucoes_na_janela']} execuções"
          f"{incompleta} | fração {ja['fracao']}")
    print(f"   N da janela: {ja['n_recalculado']} (P(zero)="
          f"{ja['p_zero_no_n']}) x N do lock {ja['n_do_lock']} — "
          f"{'CONFORME' if ja['n_conforme'] else 'N DESATUALIZADO'}")
    c = calc["correlacao_intra_execucao"]
    print(f"   homogeneidade: qui-quadrado {c['quiquad_homogeneidade']} em "
          f"{c['graus_de_liberdade']} g.l., p={c['p_valor_homogeneidade']:.3f}"
          f" — {c['leitura_dispersao']}")
    print(f"   fração da janela {c['fracao_da_janela']} x congelada "
          f"{c['fracao_congelada_do_lock']} (cauda "
          f"{c['p_cauda_binomial_total']:.4f})")
    v = calc["veredito"]
    print(f"   VEREDITO: NAO_INDEPENDENTE dispara = "
          f"{v['nao_independente_dispara']}"
          + (" | N DESATUALIZADO — PR de manutenção é o caminho"
             if v["n_desatualizado"] else ""))
    print(f"   {v['nota']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
