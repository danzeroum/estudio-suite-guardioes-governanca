#!/usr/bin/env python3
"""O gate unico. Falhou aqui, falha no CI -- e o contrario tambem.

Dois codigos de falha, de proposito:
  1  divergencia entre o declarado e o real (roteiro errado, derivado fora de dia)
  2  algum fiscal NAO CONSEGUIU fiscalizar (lei ausente, dado ilegivel)

Colapsar os dois faria "estou sem a lei" e "o roteiro esta errado" ficarem
indistinguiveis, e a leitura barata venceria: 'deve ser a rede'.

O teste de navegador NAO entra aqui: ele precisa de Chromium e leva minutos.
O CI o roda num job separado, pela mesma razao de ordem por custo que o
repositorio de origem ja usava -- o que e barato falha primeiro.
"""
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite.comum import ErroDeDados   # noqa: E402


def _passo(nome, fn):
    """Roda um fiscal e devolve (codigo, saida). Nunca deixa excecao escapar."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            cod = fn()
        return int(cod or 0), buf.getvalue()
    except ErroDeDados as e:
        return 2, buf.getvalue() + f"  ERRO: {e}\n"
    except Exception as e:                      # fiscal quebrado e exit 2, nao 1
        return 2, buf.getvalue() + f"  ERRO: {nome} nao conseguiu rodar: {e}\n"


def _fiscais(com_lei=True):
    from estudio_suite import lei as _lei
    from estudio_suite import roteiro as _rot
    import importlib
    _sinc = importlib.import_module("ci.sincronizar_derivados")

    def lei():
        _lei.materializar()
        a = _lei.ancora()
        print(f"  lei {a['repo']} @ {a['sha'][:12]} conferida "
              f"({len(a['arquivos'])} arquivos).")
        return 0

    from estudio_suite import orcamento as _orc
    _aud = importlib.import_module("ci.auditar_melhorias")
    from estudio_suite import amostras as _am
    from estudio_suite.comum import FILMES, filmes_existentes
    from estudio_suite.pipeline import fiscal_redublagem

    def redublagem():
        """A dublagem de TODOS os filmes, fiscalizada sem lei e sem piper.

        O fiscal compara texto, tempo, timbre, prosodia e ambiente
        (CP-007) — nada de sintese aqui, so o manifesto contra o dado.
        Entrou no conjunto que nao depende da lei (CP-007): divida de
        dublagem aparecia so no test_dublar do CI, nunca no gate unico —
        e gate que nao roda o fiscal deixa a divida para quem OUVE.
        """
        pior = 0
        for fid in filmes_existentes():
            if not (FILMES / fid / "audio" / "audio.json").exists():
                print(f"  {fid}: filme mudo — camada aditiva, nada a fiscalizar")
                continue
            achados = fiscal_redublagem(fid)
            if achados:
                pior = 1
                for a in achados:
                    print(f"  {fid}: {a}")
            else:
                print(f"  {fid}: dublagem em dia com legendas, timbre e voz.lock")
        return pior

    # Os dois primeiros PRECISAM da lei; os ultimos, nao. Rodar so os
    # ultimos e uma medicao MENOR, e ela e anunciada como tal -- o que nao se
    # pode e chamar de verde uma validacao que nao mediu o que importa.
    com = [("lei ancorada", lei), ("roteiros e jogos", _rot.main)]
    sem = [("orcamento de tamanho", _orc.main),
           ("modulo de automelhorias", _aud.main),
           ("sons ancorados", _am.checar),
           ("redublagem dos filmes", redublagem),
           ("artefatos derivados", lambda: _sinc.main())]
    return (com + sem) if com_lei else sem


def main(argv=None) -> int:
    argv = list(argv or [])
    com_lei = "--sem-lei" not in argv
    sys.argv = [sys.argv[0], "--check"]          # o sincronizador so confere aqui
    if not com_lei:
        print("  ATENCAO: rodando SEM a lei. Citacao de artigo e atribuicao de")
        print("  guardiao NAO foram medidas nesta execucao. Isto e uma validacao")
        print("  PARCIAL, e dizer que passou seria dizer menos do que parece.")
        print()
    pior = 0
    for nome, fn in _fiscais(com_lei):
        cod, saida = _passo(nome, fn)
        marca = "ok  " if cod == 0 else ("FALHOU" if cod == 1 else "NAO RODOU")
        print(f"[{marca}] {nome}")
        for l in saida.rstrip().split("\n"):
            if l.strip():
                print(f"    {l.strip()}")
        pior = max(pior, cod)
    print()
    sufixo = "" if com_lei else "  (PARCIAL: sem a lei)"
    print({0: "  conforme." + sufixo,
           1: "  DIVERGENCIA entre o declarado e o real." + sufixo,
           2: "  algum fiscal NAO CONSEGUIU fiscalizar."}[pior])
    return pior


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
