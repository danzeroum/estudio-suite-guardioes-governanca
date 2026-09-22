#!/usr/bin/env python3
"""O normalizador de fala, provado no corpus vivido -- e nos dois sentidos.

Um normalizador que nunca transformou nada nao normaliza nada. Cada caso aqui
e uma legenda REAL dos filmes (ou o exemplo da CP-004), e a ultima secao roda
o corpus inteiro: nenhuma legenda normalizada pode sobrar com digito, com
"Art.", com quebra de linha ou com travessao.

O campo "quem" e provado nos DOIS sentidos, como manda o criterio de aceite
do Sprint 1: com ator do elenco passa, com ator inexistente reprova -- sobre
um filme fantasma que nasce e morre dentro do teste.
"""
import io
import json
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import fala                      # noqa: E402
from estudio_suite.comum import FILMES, filmes_existentes  # noqa: E402

ok, bad = [], []


def chk(c, msg):
    (ok if c else bad).append(msg)


# ---- o exemplo da CP-004 e o corpus vivido -------------------------------
CASOS = [
    # o exemplo nomeado na proposta
    ("(Art. 10)", "artigo dez"),
    # citacoes com ordinal grafico (o º e da tela, nao da fala)
    ("A lei dá nome a isso: dado pessoal.\n(Art. 5º)",
     "A lei dá nome a isso: dado pessoal. artigo cinco"),
    ("(Arts. 37 e 38)", "artigos trinta e sete e trinta e oito"),
    ("Sair da instrução o torna responsável\njunto. (Art. 39)",
     "Sair da instrução o torna responsável junto. artigo trinta e nove"),
    # siglas: a voz nao adivinha
    ("Ana digita o CPF num formulário.",
     "Ana digita o cê-pê-éfe num formulário."),
    ("A ANPD e o titular precisam ser avisados.",
     "A a-ene-pê-dê e o titular precisam ser avisados."),
    # travessão: pausa de ouvido, nao silencio
    ("com o dado dela — antes, não depois.",
     "com o dado dela, antes, não depois."),
    ("— da finalidade à prestação de contas.",
     "da finalidade à prestação de contas."),
    ("Nove hipóteses permitem isso —", "Nove hipóteses permitem isso"),
    # numeros soltos: cardinal, como fala o cidadao
    ("São 9 direitos, e o relógio corre.",
     "São nove direitos, e o relógio corre."),
    ("Consentimento é só uma das 10 rotas.",
     "Consentimento é só uma das dez rotas."),
    ("Isso é 70% do problema.", "Isso é setenta por cento do problema."),
]


def test_casos():
    for entrada, esperado in CASOS:
        saida = fala.normalizar(entrada)
        chk(saida == esperado,
            f"normalizar({entrada!r}) == {esperado!r} (saiu {saida!r})")
    # idempotencia: normalizar o ja normalizado nao muda nada
    for entrada, _ in CASOS:
        uma = fala.normalizar(entrada)
        chk(fala.normalizar(uma) == uma, f"normalizar e idempotente para {uma!r}")


def test_extenso():
    pares = [(0, "zero"), (5, "cinco"), (10, "dez"), (18, "dezoito"),
             (37, "trinta e sete"), (38, "trinta e oito"), (100, "cem"),
             (118, "cento e dezoito"), (200, "duzentos"),
             (1000, "mil"), (1100, "mil e cem"), (2345, "dois mil trezentos e quarenta e cinco")]
    for n, esperado in pares:
        chk(fala.por_extenso(n) == esperado,
            f"por_extenso({n}) == {esperado!r} (saiu {fala.por_extenso(n)!r})")
    try:
        fala.por_extenso(-1)
        chk(False, "por_extenso(-1) devia recusar")
    except ValueError:
        chk(True, "por_extenso recusa negativo")


def test_corpus_inteiro():
    """Toda legenda de todo filme sai falavel: sem digito, sem 'Art.', sem
    quebra de linha, sem travessao. E o teste que o Sprint 2 depende -- dublar
    nao pode descobrir no meio da sintese que uma legenda escapou."""
    total = 0
    for fid in filmes_existentes():
        from estudio_suite.comum import dados_do_filme
        for P in dados_do_filme(fid)["planos"]:
            for L in P.get("legendas") or []:
                total += 1
                f = fala.normalizar(L["txt"])
                chk(not any(c.isdigit() for c in f),
                    f"{fid}/{P['id']}: sem digitos depois de normalizar ({f!r})")
                chk("Art" not in f, f"{fid}/{P['id']}: sem 'Art.' depois de normalizar")
                chk("\n" not in f and "—" not in f,
                    f"{fid}/{P['id']}: sem quebra de linha nem travessao")
                chk(f == f.strip() and f != "", f"{fid}/{P['id']}: sai limpa e nao vazia")
    chk(total >= 40, f"corpus com {total} legendas -- o teste precisa de corpo")


FANTASMA = "teste-quem-fantasma"


def _escrever_filme_fantasma(quem):
    d = FILMES / FANTASMA
    d.mkdir(parents=True, exist_ok=True)
    legenda = {"em": 0.3, "ate": 5.5, "txt": "Um teste de quem fala."}
    if quem is not None:
        legenda["quem"] = quem
    filme = {
        "id": FANTASMA, "titulo": "Filme fantasma do teste", "duracao": 6,
        "elenco": {"ana": {"rig": "raposa", "papel": "Titular"}},
        "planos": [{
            "id": "p01", "titulo": "Teste", "dur": 6, "guardiao": "coruja",
            "cenario": "vazio", "poster": 3, "arts": [],
            "entra": {"ana": {"x": 300, "y": 620}},
            "legendas": [legenda],
        }],
    }
    (d / f"{FANTASMA}.filme.js").write_text(
        "window.ESTUDIO_FILMES=window.ESTUDIO_FILMES||{};"
        "window.ESTUDIO_FILMES[\"" + FANTASMA + "\"]=\n" +
        json.dumps(filme, ensure_ascii=False, indent=1) + "\n;\n",
        encoding="utf-8")
    return d


def test_quem_nos_dois_sentidos():
    """O campo opcional 'quem': com ator do elenco passa, com ator inexistente
    reprova, e sem o campo nao reclama. A lei e fantasma (vazia) para o teste
    rodar sem rede -- o que se prova aqui e o fiscal do 'quem', nao a lei."""
    from estudio_suite import roteiro as _rot
    import tempfile

    orig = (_rot._lei.carregar, _rot._lei.materializar,
            _rot.filmes_existentes, _rot.jogos_existentes)
    with tempfile.TemporaryDirectory() as tmp:
        fake_lei = Path(tmp) / "lei"
        (fake_lei / "docs/assets/css").mkdir(parents=True)
        (fake_lei / "docs/assets/css/theme.css").write_text("", encoding="utf-8")
        try:
            _rot._lei.carregar = lambda: ({}, {})
            _rot._lei.materializar = lambda: fake_lei
            _rot.filmes_existentes = lambda: [FANTASMA]
            _rot.jogos_existentes = lambda: []

            for quem, deve_falhar in [("ana", False), (None, False),
                                      ("inexistente", True), ("dado", True)]:
                _escrever_filme_fantasma(quem)
                _rot.falhas.clear()
                _rot.avisos.clear()
                import contextlib
                with redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    cod = _rot.main()
                achou = any("quem=" in f for f in _rot.falhas)
                chk(achou == deve_falhar,
                    f"legenda com quem={quem!r}: {'reprova' if deve_falhar else 'passa'} "
                    f"(falhas: {_rot.falhas})")
                if deve_falhar:
                    chk(cod == 1, f"quem={quem!r} devolve vermelho (exit 1)")
        finally:
            _rot._lei.carregar, _rot._lei.materializar = orig[0], orig[1]
            _rot.filmes_existentes, _rot.jogos_existentes = orig[2], orig[3]
            _rot.falhas.clear()
            _rot.avisos.clear()
            shutil.rmtree(FILMES / FANTASMA, ignore_errors=True)


def main():
    test_casos()
    test_extenso()
    test_corpus_inteiro()
    test_quem_nos_dois_sentidos()

    for m in ok:
        pass
    print(f"  {len(ok)} verificacoes do normalizador de fala.")
    if bad:
        for m in bad:
            print(f"  ERRO: {m}", file=sys.stderr)
        print(f"\n  {len(bad)} falha(s).", file=sys.stderr)
        return 1
    print("  a legenda vira fala, e o 'quem' responde pelo elenco.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
