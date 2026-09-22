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


def _fiscais():
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

    return [("lei ancorada", lei),
            ("roteiros e jogos", _rot.main),
            ("artefatos derivados", lambda: _sinc.main())]


def main(argv=None) -> int:
    argv = list(argv or [])
    sys.argv = [sys.argv[0], "--check"]          # o sincronizador so confere aqui
    pior = 0
    for nome, fn in _fiscais():
        cod, saida = _passo(nome, fn)
        marca = "ok  " if cod == 0 else ("FALHOU" if cod == 1 else "NAO RODOU")
        print(f"[{marca}] {nome}")
        for l in saida.rstrip().split("\n"):
            if l.strip():
                print(f"    {l.strip()}")
        pior = max(pior, cod)
    print()
    print({0: "  conforme.", 1: "  DIVERGENCIA entre o declarado e o real.",
           2: "  algum fiscal NAO CONSEGUIU fiscalizar."}[pior])
    return pior


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
