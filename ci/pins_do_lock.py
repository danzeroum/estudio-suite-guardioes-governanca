#!/usr/bin/env python3
"""Os pins do voz.lock, para quem monta ambiente: CI, imagem, quem for.

O voz.lock e a UNICA fonte de versoes (CP-008): o workflow nao digita
numero de python/numpy/scipy em lugar nenhum, a imagem dubladora nao digita
piper/onnxruntime em nenhum RUN -- os dois perguntam AQUI, e aqui pergunta
ao PARSER de estudio_suite/voz.py (sem YAML, sem regex duplicada: o lock e
contrato com um leitor so).

Comportamento:
  --so numpy,scipy        imprime "numpy==2.1.3 scipy==1.14.1" (para o
                          $(pip install ...) do workflow e do Dockerfile)
  --python                imprime a serie do lock (ex. 3.12) para o
                          setup-python -- o CI roda o python da ancora,
                          nao o python da moda
  --threads               imprime o numero de threads da ancora (CP-009)
                          para o --build-arg da imagem dubladora e o ENV
                          do job — o numero nunca e digitado em segundo
                          lugar
  --classe-simd           imprime a classe de SIMD da ancora (CP-011)
                          para o job decidir qual prova aplicar — a classe
                          vem do lock, de nenhum outro lugar; lock sem a
                          linha e lock INCOMPLETO (saida 2, nunca chute)
  --teto-residuo          imprime o teto de residuo em dBFS (CP-011, bloco
                          tolerancia do lock) — a tolerancia so existe
                          com teto registrado; sem o bloco, saida 2
                          nomeando (o job exige bytes em toda classe)
  --conferir python,numpy,scipy
                          mede o ambiente EFETIVO (o mesmo
                          ambiente_instalado() do dublar) e confere as
                          chaves pedidas contra o lock; divergencia
                          derruba o passo (saida 1) nomeando chave,
                          ancora e medido

Saidas: 0 conforme · 1 divergencia entre o ambiente e a ancora · 2 o
pedido nao da para responder (pacote ausente no lock, ou chave que nao e
pacote pip). As duas ultimas sao estados diferentes de proposito: "nao
consegui ler o contrato" e "li o contrato e o ambiente nao cumpre".
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estudio_suite import voz                    # noqa: E402

# Chaves ancoradas que NAO sao pacote pip: python e runtime, espeak-ng
# vem EMBUTIDO no wheel do piper (ancora por sha256 dos dados), ffmpeg e
# libopus sao do apt, arquitetura e a CPU, threads e o numero que a
# SESSAO do onnxruntime tem de carregar (CP-009 — lido pelo dublar com
# get_session_options, espelhado no ENV OMP/OpenBLAS/MKL da imagem),
# classe_simd e a classe de SIMD que o job compara com a do runner
# (CP-011) e teto_residuo e o bloco tolerancia do lock (CP-011).
# Pedir pin pip para elas seria imprimir um comando que nao existe -- o
# erro nomeia a confusao.
NAO_PIP = {"python", "espeak-ng", "ffmpeg", "libopus", "arquitetura",
           "threads", "classe_simd", "teto_residuo"}


def _lock() -> dict:
    """O bloco ambiente do lock -- pelo parser de voz.py, nunca por regex daqui."""
    return voz.ancora()["ambiente"]


def _separar(arg: str) -> list:
    return [p.strip() for p in arg.split(",") if p.strip()]


def pins(so: list) -> int:
    amb = _lock()
    pedidos, problemas = [], []
    for nome in so:
        if nome in NAO_PIP:
            problemas.append(
                f"{nome}: nao e pacote pip -- {nome} e ancorado por "
                f"{'runtime' if nome == 'python' else 'outro mecanismo'} "
                f"no voz.lock, nao por versao de wheel")
        elif nome not in amb:
            problemas.append(
                f"{nome}: ausente no bloco ambiente do voz.lock -- pin sem "
                f"ancora e versao digitada a mao, o defeito que este "
                f"script existe para impedir")
        else:
            pedidos.append(f"{nome}=={amb[nome]}")
    if problemas:
        print("ERRO: pins impossiveis:\n  " + "\n  ".join(problemas),
              file=sys.stderr)
        return 2
    print(" ".join(pedidos))
    return 0


def conferir(chaves: list) -> int:
    amb = _lock()
    instalado = voz.ambiente_instalado()
    problemas = []
    for nome in chaves:
        if nome not in amb:
            print(f"ERRO: {nome}: ausente no bloco ambiente do voz.lock -- "
                  f"nao ha ancora para conferir", file=sys.stderr)
            return 2
        esp, inst = amb[nome], instalado.get(nome)
        marca = "ok" if esp == inst else "DIVERGE"
        print(f"  {nome:12s} ancora {esp:16s} medido {inst}  [{marca}]")
        if esp != inst:
            problemas.append(f"{nome}: o lock ancora {esp}, o ambiente "
                             f"mediu {inst} -- este job roda fora da ancora")
    fora = sorted(set(amb) - set(chaves) - set())
    print(f"  (fora desta conferencia: {', '.join(fora)} -- "
          f"{'o job nao dubla' if chaves != sorted(amb) else 'conferidos acima'})")
    if problemas:
        print("\nERRO: ambiente divergente da ancora:\n  "
              + "\n  ".join(problemas), file=sys.stderr)
        return 1
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    acoes = ("--so", "--python", "--threads", "--classe-simd",
             "--teto-residuo", "--conferir")
    if not argv or argv[0] not in acoes:
        print("uso: pins_do_lock.py --so numpy,scipy | --python | --threads | "
              "--classe-simd | --teto-residuo | "
              "--conferir python,numpy,scipy", file=sys.stderr)
        return 64
    flag = argv[0]
    if flag == "--python":
        if len(argv) != 1:
            print("ERRO: --python nao recebe valor — a serie vem do lock",
                  file=sys.stderr)
            return 64
        amb = _lock()
        if "python" not in amb:
            print("ERRO: voz.lock sem python no bloco ambiente -- o CI nao "
                  "sabe qual runtime a ancora pede", file=sys.stderr)
            return 2
        print(amb["python"])
        return 0
    if flag == "--threads":
        # CP-009: o ENV de threads da imagem e o build-arg vem DAQUI — o
        # numero tem uma fonte so, e ela e o lock. Lock sem threads e
        # lock INCOMPLETO: a saida e 2 nomeando, nunca um numero chutado.
        if len(argv) != 1:
            print("ERRO: --threads nao recebe valor — o numero vem do lock",
                  file=sys.stderr)
            return 64
        amb = _lock()
        if "threads" not in amb:
            print("ERRO: voz.lock sem threads no bloco ambiente -- lock "
                  "INCOMPLETO (CP-009): o ENV da imagem e a sessao do "
                  "dublar nao sabem o que carregar", file=sys.stderr)
            return 2
        try:
            n = int(str(amb["threads"]).strip())
        except ValueError:
            print(f"ERRO: a ancora de threads nao e inteiro "
                  f"({amb['threads']!r}) — lock ilegivel", file=sys.stderr)
            return 2
        if n < 1:
            print(f"ERRO: ancora de threads {n} < 1 — lock ilegivel",
                  file=sys.stderr)
            return 2
        print(n)
        return 0
    if flag == "--classe-simd":
        # CP-011: a classe da ancora vem DAQUI — o job compara a classe do
        # runner (medida pelo MESMO classificador de estudio_suite/voz.py)
        # contra este valor. Lock sem classe_simd e lock INCOMPLETO: a
        # saida e 2 nomeando, nunca um chute.
        if len(argv) != 1:
            print("ERRO: --classe-simd nao recebe valor — a classe vem do lock",
                  file=sys.stderr)
            return 64
        amb = _lock()
        if "classe_simd" not in amb:
            print("ERRO: voz.lock sem classe_simd no bloco ambiente -- lock "
                  "INCOMPLETO (CP-011): o job dublador nao sabe qual classe "
                  "exige bytes e qual exige tolerancia; recusa nomeada, nunca "
                  "chute", file=sys.stderr)
            return 2
        classe = str(amb["classe_simd"]).strip()
        if classe not in voz.CLASSES_SIMD:
            print(f"ERRO: ancora de classe_simd {classe!r} fora das classes "
                  f"conhecidas {voz.CLASSES_SIMD} — lock ilegivel",
                  file=sys.stderr)
            return 2
        print(classe)
        return 0
    if flag == "--teto-residuo":
        # CP-011: o teto da tolerancia vem do bloco `tolerancia:` do lock —
        # a UNICA morada do numero. Sem o bloco, a saida e 2 nomeando: o
        # job cai na doutrina antiga (bytes em toda classe), nunca numa
        # tolerancia sem numero.
        if len(argv) != 1:
            print("ERRO: --teto-residuo nao recebe valor — o teto vem do lock",
                  file=sys.stderr)
            return 64
        tol = voz.tolerancia()
        if "residuo_max_dbfs" not in tol:
            print("ERRO: voz.lock sem o bloco tolerancia.residuo_max_dbfs -- "
                  "tolerancia SEM teto e afrouxar fiscal com palavra bonita: "
                  "o job exige bytes em toda classe ate o teto ser MEDIDO na "
                  "frota e registrado aqui por CP", file=sys.stderr)
            return 2
        try:
            teto = float(str(tol["residuo_max_dbfs"]).strip())
        except ValueError:
            print(f"ERRO: o teto de residuo ({tol['residuo_max_dbfs']!r}) nao e "
                  f"um numero em dBFS — lock ilegivel", file=sys.stderr)
            return 2
        if teto >= -60.0:
            print(f"ERRO: o teto de residuo ({teto:g} dBFS) nao fica abaixo de "
                  f"-60 dBFS — resíduo audivel e RESIDUO_AUDIVEL: tolerancia "
                  f"alguma so existe abaixo do silencio de ouvido humano; "
                  f"corrija o lock por CP com medicao", file=sys.stderr)
            return 2
        print(f"{teto:g}")
        return 0
    if len(argv) != 2:
        print("ERRO: " + flag + " exige a lista de chaves (ex. numpy,scipy)",
              file=sys.stderr)
        return 64
    chaves = _separar(argv[1])
    if not chaves:
        print("ERRO: nenhuma chave pedida", file=sys.stderr)
        return 64
    if flag == "--so":
        return pins(chaves)
    return conferir(chaves)


if __name__ == "__main__":
    sys.exit(main())
