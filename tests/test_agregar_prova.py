#!/usr/bin/env python3
"""O agregador da prova por amostragem, provado com artefatos sintéticos (CP-013).

A aceite da CP-013 é literal:
  - {1 AVX-512 idêntica + 11 AVX2}                -> verde
  - {0 AVX-512}                                   -> SEM_AMOSTRA_DECISIVA
  - {2 idênticas + 1 divergente}                  -> DIVERGENCIA_AVX512 nomeando a cópia
  - artefato ausente ou corrompido                -> reprova ("amostra ilegível"),
                                                     nunca conta como neutra
  - uma cópia AVX2 termina sem build e sem gate   -> classe no artefato, neutra

O que se prova aqui: o veredito do RUN é da AMOSTRAGEM, não da cópia —
nenhuma cópia decide sozinha; a divergência é nomeada com a cópia; a
falta de amostra decisiva é vermelho nomeado (o rerun é o caminho de
volta); a cópia avx2 não contribui, não bloqueia e não é neutra POR
OMISSÃO — é neutra por classe declarada; e o que não se pode ler,
reprova. E o contrato estrutural do workflow: a cópia avx2 NÃO constroi
(sem passos de build na condição dela), o job segue obrigatório (sem
continue-on-error), o veredito.json é publicado sempre e a matrix nasce
do lock.
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


def copia_veredito(copia, classe, veredito, cpu="AMD EPYC 9V74 80-Core Processor",
                   detalhe="detalhe de teste", extra=None):
    doc = {"copia": copia, "cpu": cpu, "classe": classe,
           "prova": ("bytes-pcm+codec-sob-teto" if classe == "avx512"
                     else "observacao-ancora"),
           "veredito": veredito, "detalhe": detalhe}
    if extra:
        doc.update(extra)
    return doc


def montar(dir_raiz, docs, nomes=None):
    """Um subdiretório por artefato, como o download-artifact@v4 deixa."""
    for i, doc in enumerate(docs):
        sub = dir_raiz / (nomes[i] if nomes else
                          f"identidade-{doc['copia']}-run1")
        sub.mkdir(parents=True, exist_ok=True)
        (sub / "veredito.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def rodar(artefatos, copias, conferir_n=False):
    cmd = [sys.executable, "ci/agregar_prova.py",
           "--artefatos", str(artefatos),
           "--copias", json.dumps(copias),
           "--saida", str(artefatos / "agregado")]
    if conferir_n:
        cmd.append("--conferir-n")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=RAIZ)


def caso(nome):
    d = Path(tempfile.mkdtemp(prefix=f"agreg-{nome}-"))
    return d


def main():
    # --- a aceite, caso 1: {1 AVX-512 identica + 11 AVX2} -> verde --------
    d = caso("c1")
    docs = ([copia_veredito("copia-12", "avx512", "identica")] +
            [copia_veredito(f"copia-{i}", "avx2", "observacao")
             for i in range(1, 12)])
    montar(d, docs)
    copias = [f"copia-{i}" for i in range(1, 13)]
    r = rodar(d, copias)
    chk(r.returncode == 0 and "verde" in r.stdout,
        f"1 AVX-512 idêntica + 11 AVX2 -> verde (exit {r.returncode})")
    ag = json.loads((d / "agregado" / "agregado.json").read_text())
    chk(ag["identicas_avx512"] == ["copia-12"]
        and len(ag["observacoes_avx2"]) == 11 and not ag["ilegiveis"],
        "o agregado registra quem é idêntica, quem observa e ninguém ilegível")
    chk("| cópia | CPU | classe | prova | veredito |" in r.stdout
        and "copia-12" in r.stdout and "observacao" in r.stdout,
        "o resumo lista cópia, CPU, classe, prova e veredito de TODAS")

    # --- a aceite, caso 2: {0 AVX-512} -> SEM_AMOSTRA_DECISIVA ------------
    d = caso("c2")
    docs = [copia_veredito(f"copia-{i}", "avx2", "observacao")
            for i in range(1, 9)]
    montar(d, docs)
    r = rodar(d, [f"copia-{i}" for i in range(1, 9)])
    chk(r.returncode == 1 and "SEM_AMOSTRA_DECISIVA" in r.stdout
        and "RERUN" in r.stdout,
        f"zero AVX-512 -> SEM_AMOSTRA_DECISIVA vermelho nomeado, rerun "
        f"(exit {r.returncode})")

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
    r = rodar(d, [f"copia-{i}" for i in range(1, 9)])
    chk(r.returncode == 1 and "DIVERGENCIA_AVX512" in r.stdout
        and "copia-3" in r.stdout and "-30.1" in r.stdout,
        f"2 idênticas + 1 divergente -> DIVERGENCIA_AVX512 nomeando a "
        f"copia-3 com os números (exit {r.returncode})")
    ag = json.loads((d / "agregado" / "agregado.json").read_text())
    chk(ag["divergentes_avx512"] == ["copia-3"]
        and ag["identicas_avx512"] == ["copia-1", "copia-2"],
        "o agregado separa idênticas de divergentes, com os nomes")

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
    (d / "identidade-copia-2-run1" / "veredito.json").write_text(
        "{isto não é json", encoding="utf-8")
    r = rodar(d, ["copia-1", "copia-2"])
    chk(r.returncode == 1 and "corrompido" in (r.stderr + r.stdout),
        f"artefato corrompido -> reprova nomeando (exit {r.returncode})")

    # --- veredito.json legível mas SEM os campos -> ilegível --------------
    d = caso("c6")
    sub = d / "identidade-copia-2-run1"
    sub.mkdir(parents=True)
    (sub / "veredito.json").write_text(
        json.dumps({"copia": "copia-2", "cpu": "x"}), encoding="utf-8")
    sub2 = d / "identidade-copia-1-run1"
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

    # --- avx2 SEM BUILD e SEM GATE: o contrato estrutural do workflow ----
    wf = (RAIZ / ".github" / "workflows" / "dublador.yml").read_text(
        encoding="utf-8")
    passos_avx512 = ("O builder com cache de camadas",
                     "A imagem que materializa o lock",
                     "As threads efetivas da sessão",
                     "Dublar quem declara audio (rodada 1)",
                     "Dublar quem declara audio (rodada 2)",
                     "O determinismo interno da imagem",
                     "A prova por classe (dentro da imagem)")
    for passo in passos_avx512:
        trecho = wf[wf.index(f"- name: {passo}"):]
        cond = trecho[:trecho.index("run:")].count(
            "if: env.CLASSE_DO_RUNNER == 'avx512'")
        chk(cond == 1,
            f"'{passo}' roda SÓ na classe avx512 (cópia avx2 sem build)")
    trecho_obs = wf[wf.index("A observação da âncora"):]
    chk("if: env.CLASSE_DO_RUNNER == 'avx2'" in trecho_obs[:trecho_obs.index("pipx")],
        "a observação roda SÓ na classe avx2 (sem build, sem gate)")
    import re as _re3
    chk(not _re3.search(r"^\s*continue-on-error:", wf, _re3.M),
        "o job dublador segue OBRIGATÓRIO: nenhum continue-on-error em passo "
        "nenhum — a tolerância da observação é um if/else que PUBLICA o "
        "status, não um continue-on-error que esconderia a falha")
    chk("- name: O veredito da cópia (CP-013)" in wf
        and "veredito.json" in wf,
        "a cópia publica o veredito.json (o contrato do agregador) sempre")
    chk("- name: O agregador da prova por amostragem (CP-013)" in wf
        and "download-artifact" in wf and "--conferir-n" in wf,
        "o job agregar baixa todos os artefatos e confere o N contra o lock")

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
    from estudio_suite import voz as _voz
    n_lock = int(_voz.frota()["amostragem"])
    chk(r.returncode == 1 and "AMOSTRA_ILEGIVEL" in (r.stderr + r.stdout)
        and f"N={n_lock}" in (r.stderr + r.stdout),
        f"matrix de 1 contra N={n_lock} do lock -> recusa nomeada "
        f"(exit {r.returncode}): o tamanho da amostra mora no lock")

    # --- cópia DUPLICADA (retry) -> ilegível nomeada ----------------------
    d = caso("c11")
    doc1 = copia_veredito("copia-1", "avx512", "identica")
    montar(d, [doc1], nomes=["identidade-copia-1-run1"])
    montar(d, [doc1], nomes=["identidade-copia-1-run2-tentativa"])
    r = rodar(d, ["copia-1"])
    chk(r.returncode == 1 and "DUPLICADO" in r.stdout,
        f"cópia com dois artefatos (retry) -> ilegível nomeada "
        f"(exit {r.returncode})")

    print(f"  {len(ok)} verificacoes do agregador da prova por amostragem.")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  o veredito do run e da amostragem: a cópia nao decide sozinha,")
    print("  a divergencia tem nome, e o que nao se le, reprova.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
