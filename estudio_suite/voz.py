"""A voz e ancorada por SHA, materializada efemera, conferida byte a byte.

Mesma arquitetura do lei.lock, pro mesmo motivo: dublar com outro modelo
produziria OUTRO audio do que o revisado -- silenciosamente. O voz.lock
declara modelo e hashes; o modelo mora em workspace/voz/, que o .gitignore
recusa; e a conferencia roda SEMPRE, inclusive quando nada foi baixado.

Diferenca de proposito em relacao a lei: a lei tem dono externo
(guardioes-governanca); a voz e um bem publico (piper-voices, MIT). O que o
lock ancora nao e "de quem e", e "EXATAMENTE qual pesos produziram esta
dublagem" -- o audio commitado e a evidencia, e o lock e o que torna a
evidencia reproduzivel.

CP-007: pesos iguais nao bastam. O byte final de um .opus assinam tambem
o piper, o onnxruntime, o numpy/scipy do motor de timbre, o fonemizador
embutido no wheel e o ffmpeg+libopus do mix -- medido em outra maquina,
as duracoes deslocam ate +0,08 s com o MESMO modelo. O bloco `ambiente:`
do lock ancora essas versoes; conferir_ambiente() as mede e recusa dublar
na divergencia, antes de escrever qualquer arquivo.

CP-008: a ARQUITETURA entra na mesma ancora (platform.machine()). O
onnxruntime escolhe kernels pela arquitetura da CPU: bytes gerados em
x86_64 nao sao provados por uma conferencia que passou em arm64. Lock
sem arquitetura e lock INCOMPLETO -- o dublar recusa em vez de assumir
x86_64 por padrao, e o caminho portavel e a imagem que materializa o
lock (ferramentas/dublador/dublar.sh, sempre linux/amd64).

CP-009: as THREADS entram na mesma ancora, pelo mesmo motivo: o GEMM do
onnxruntime e particionado pelo numero de threads e a ordem das somas
parciais em float muda com a particao -- medido nas 42 FALAS REAIS dos
dois filmes: 1, 2 e 3 assinam TRES resultados distintos (4 falas mudam
entre 1 e 2, 33 entre 2 e 3; a frase curta do experimento inicial era
regime-insensivel e mentiu por amostragem pequena). O default segue os
nucleos FISICOS da maquina: o mesmo codigo sintetiza regimes diferentes
em runners de classes diferentes, e o gate dublador oscilava com a
sorte da frota. Lock sem threads e lock INCOMPLETO (conferir_threads
recusa); o ENV de threads (OMP/OpenBLAS/MKL) e a face externa da mesma
ancora -- ausente ou divergente, o ambiente nao e o que o lock declara.
A sessao em si e conferida pelo dublar, lendo DE VOLTA o numero EFETIVO
da sessao construida com o valor do lock (dublar._conferir_threads_da_
sessao): o valor lido e o que vale.

CP-011: a CLASSE DE SIMD e a ultima variavel viva entre runners de
mesma arquitetura e mesmas threads -- medido: com threads ancoradas e
LIDAS em 8/8 execucoes, 7 divergiram em AMD EPYC (sem avx512f no lscpu)
e 1 reproduziu em Intel Xeon 8370C (com AVX-512, sem AMX). A classe
entra na mesma ancora como classe_simd, derivada de FLAGS MEDIDAS
(lscpu, /proc/cpuinfo como fallback), nunca do nome do fabricante:
"Intel" e "AMD" nao separam quem reproduz de quem diverge. O
classificador mora AQUI (um lugar so) e e usado pelo dublar, pelo job
e pelos testes. Lock sem classe_simd e lock INCOMPLETO (conferir_classe
recusa). O dublar NAO recusa classe divergente: ele registra o MEDIDO
no audio.json (ambiente.classe_simd, como ja faz com as threads) e os
GATES decidem -- o fiscal de redublagem aponta dublagem commitada de
classe divergente, e o job aplica a prova por classe (bytes na classe
da ancora; tolerancia com teto medido nas demais). A tolerancia mora no
bloco `tolerancia:` do lock (residuo_max_dbfs, margem, ponto, base):
sem esse bloco, a doutrina e a antiga -- bytes em toda classe.
"""
import ctypes
import hashlib
import importlib.metadata
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from .comum import ErroDeDados, RAIZ, WORKSPACE

LOCK = RAIZ / "voz.lock"
DESTINO = WORKSPACE / "voz"


def _bloco_raso(txt: str, nome: str) -> dict:
    """Pares 'chave: valor' de um bloco topologico 'nome:' — raso, sem YAML.

    Mesma disciplina do parser dos pesos: o lock e contrato lido por
    regex, porque um parser de YAML aqui seria uma dependencia a mais
    para interpretar um arquivo que ninguem deveria editar a mao. A
    secao comeca na chave de coluna zero e acaba na proxima.
    """
    m = re.search(rf"^{nome}:\s*$", txt, re.M)
    if not m:
        return {}
    resto = txt[m.end():]
    fim = re.search(r"^\S", resto, re.M)
    secao = resto[:fim.start()] if fim else resto
    return dict(re.findall(r"^  ([\w.-]+):\s*(\S+)\s*$", secao, re.M))


def ancora() -> dict:
    """Le voz.lock sem dependencia de YAML: formato fixo e raso, como lei.lock."""
    if not LOCK.exists():
        raise ErroDeDados(
            "voz.lock nao existe. Sem ancora, nao ha dublagem: cada maquina "
            "sintetizaria com o modelo que tivesse a mao, e o audio commitado "
            "nao seria reproduzivel. Crie o lock ANTES de dublar.")
    txt = LOCK.read_text(encoding="utf-8")
    nome = re.search(r"^\s*nome:\s*(\S+)\s*$", txt, re.M)
    origem = re.search(r"^\s*origem:\s*(\S+)\s*$", txt, re.M)
    arquivos = dict(re.findall(r"^  (\S+):\n    sha256:\s*([0-9a-f]{64})", txt, re.M))
    if not (nome and origem):
        raise ErroDeDados("voz.lock sem modelo.nome / modelo.origem legiveis.")
    if not arquivos:
        raise ErroDeDados("voz.lock nao lista nenhum arquivo com sha256.")
    ambiente = _bloco_raso(txt, "ambiente")
    if not ambiente:
        raise ErroDeDados(
            "voz.lock sem o bloco ambiente (CP-007). So os pesos nao "
            "reproduzem um .opus: piper, onnxruntime, numpy/scipy, o "
            "fonemizador do wheel e o ffmpeg/libopus do mix tambem assinam "
            "os bytes -- dublar sem essa ancora e reproduzir de ouvido. "
            "Avancar o lock e change-proposal, como qualquer ancora.")
    return {"nome": nome.group(1), "origem": origem.group(1),
            "arquivos": arquivos, "ambiente": ambiente}


# ---- o ambiente de sintese (CP-007) ----------------------------------------
# A lista e a de tudo que toca os bytes entre a legenda e o .opus. python
# entra como major.minor: patch de CPython nao muda o resultado das
# extensoes C (quem roda os numeros e numpy/scipy), mas a serie sim.
PACOTES = ("piper-tts", "onnxruntime", "numpy", "scipy")

# CP-009: o ENV de threads e a face externa da ancora `threads` do lock.
# OMP rege o pool do onnxruntime quando o SessionOptions nao fixa (o dublar
# FIXA, mas ambiente mentido deriva em diagnostico mentido); OPENBLAS e MKL
# regem as BLAS que numpy/scipy carregam -- o motor de timbre roda nelas.
# Um so numero no lock governa as tres variaveis: threads vem do lock, de
# nenhum outro lugar.
THREADS_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")

# ---- a classe de SIMD da CPU (CP-011) --------------------------------------
# A chave da classe sao FLAGS MEDIDAS, nunca o nome do fabricante: "Intel"
# e "AMD" nao separam quem reproduz de quem diverge -- o lscpu e que separa
# (7/8 divergentes eram AMD sem avx512f LEGIVEL no lscpu do runner; o unico
# verde era Intel com avx512f; o AMX nao e a chave: o 8370C nao tem e
# reproduz). Se um dia um runner com avx512f divergir, a chave precisa de
# MAIS UMA FLAG -- descoberta por medicao (diff das flags de quem passa x
# quem falha), nunca por precaucao: CLASSE_MAL_DEFINIDA e o nome dessa
# parada. As classes conhecidas:
CLASSES_SIMD = ("avx512", "avx2")
# avx512  <- avx512f presente (a classe da maquina que sintetizou o
#            commitado -- confirmada por medicao; o Xeon 8370C que
#            reproduz byte a byte tambem a declara)
# avx2    <- avx2 sem avx512f (a maioria da frota ubuntu-latest hoje)

def flags_do_lscpu_json(txt: str) -> set:
    """O conjunto de flags do `lscpu --json` (o mesmo formato que o job publica).

    O parser e deterministico de proposito: campo 'Flags' do JSON de saida,
    sem grep em texto traduzido. Ilegivel devolve conjunto vazio -- quem
    chama decide se recusa (a recusa e nomeada, nunca um chute).
    """
    import json
    try:
        d = json.loads(txt)
        for e in d.get("lscpu", []):
            if (e.get("field") or "").rstrip(":").strip() == "Flags":
                return set((e.get("data") or "").split())
    except Exception:
        pass
    return set()


def flags_do_proc_cpuinfo(txt: str) -> set:
    """O conjunto de flags da primeira linha 'flags' do /proc/cpuinfo.

    O fallback do lscpu: a imagem dubladora e slim e pode nao carregar o
    util-linux; /proc/cpuinfo e a MESMA fonte do kernel que o lscpu le,
    disponivel em qualquer Linux. Os nomes das flags sao os mesmos.
    """
    for linha in txt.splitlines():
        if linha.startswith("flags") and ":" in linha:
            return set(linha.split(":", 1)[1].split())
    return set()


def flags_simd_medidas() -> set:
    """As flags SIMD da CPU onde este processo roda, MEDIDAS na hora.

    lscpu --json primeiro (a mesma medição que o job publica no artefato
    de identidade); /proc/cpuinfo quando o lscpu nao existe ou nao fala
    (a mesma fonte do kernel). As duas falarem e recusa nomeada: sem
    flags nao existe classe, e sem classe a prova por classe nao existe
    -- nunca palpite.
    """
    try:
        r = subprocess.run(["lscpu", "--json"], capture_output=True,
                           text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        r = None
    if r is not None and r.returncode == 0:
        flags = flags_do_lscpu_json(r.stdout)
        if flags:
            return flags
    try:
        txt = Path("/proc/cpuinfo").read_text(encoding="utf-8")
    except OSError as e:
        raise ErroDeDados(
            f"nao consegui medir as flags de SIMD desta CPU (lscpu indisponivel "
            f"e /proc/cpuinfo ilegivel: {e}). A classe_simd e parte da ancora "
            f"de voz desde a CP-011: sem medi-la, nao ha prova por classe -- "
            f"recusa nomeada, nunca palpite.") from None
    flags = flags_do_proc_cpuinfo(txt)
    if not flags:
        raise ErroDeDados(
            "/proc/cpuinfo sem linha de flags legivel nesta maquina -- a classe "
            "de SIMD (CP-011) nao pode ser medida, e sem classe nao ha prova "
            "por classe. Recusa nomeada; nunca palpite.")
    return flags


def classe_simd_de_flags(flags) -> str:
    """A classe de SIMD de um conjunto de flags MEDIDAS (avx512 | avx2).

    A chave e a presenca de avx512f (a flag que separou, na frota medida,
    quem reproduz de quem diverge); sem ela, avx2. Sem nenhuma das duas,
    recusa nomeada: 'classe indeterminada' com chute seria ancorar por
    coincidencia -- o erro que esta ancora existe para fechar.
    """
    flags = set(flags or ())
    if "avx512f" in flags:
        return "avx512"
    if "avx2" in flags:
        return "avx2"
    raise ErroDeDados(
        f"as flags de SIMD medidas nao definem classe nenhuma ({sorted(flags)[:12]}... "
        f"sem avx512f e sem avx2): classe indeterminada e RECUSA nomeada (CP-011) "
        f"-- assumir uma classe seria palpite, e palpite nao ancora nada.")


def classe_simd_medida() -> str:
    """A classe de SIMD desta máquina, medida agora (flags -> classificador)."""
    return classe_simd_de_flags(flags_simd_medidas())


def conferir_classe(ancora: dict) -> str:
    """A classe do lock contra a MEDIDA nesta máquina — e devolve a medida.

    Lock SEM classe_simd e lock INCOMPLETO: recusado antes de qualquer
    sintese, como lock sem threads e lock sem arquitetura — assumir a
    classe da máquina que roda seria ancorar por coincidência. Valor de
    classe fora das conhecidas e lock ilegível, também recusado.

    A classe MEDIDA DIVERGENTE da âncora NÃO é recusa aqui — e decisão de
    projeto registrada na CP-011: a divergência não é corrigível com
    pacote ou ENV (é o hardware), o dublar registra o MEDIDO no
    audio.json (ambiente.classe_simd, como faz com as threads efetivas)
    e quem DECIDE é o gate: o fiscal de redublagem aponta dublagem
    commitada de classe divergente, e o job dublador aplica a prova por
    classe (bytes na classe âncora; tolerância com teto medido nas
    demais). Sintetizar na classe divergente é exatamente o que a prova
    de tolerância precisa MEDIR.
    """
    if "classe_simd" not in ancora:
        raise ErroDeDados(
            "voz.lock sem classe_simd no bloco ambiente (CP-011) — lock "
            "INCOMPLETO: com as threads fechadas, a última variável viva "
            "entre runners é a classe de SIMD, que decide quais kernels o "
            "onnxruntime despacha (7/8 execuções divergiram em AMD sem "
            "avx512f; 1/8 reproduziu em Intel com avx512f — medido, CP-009). "
            "Assumir "
            "a classe da máquina que roda seria ancorar por coincidência. "
            "Ancore por change-proposal, como qualquer âncora.")
    declarada = str(ancora["classe_simd"]).strip()
    if declarada not in CLASSES_SIMD:
        raise ErroDeDados(
            f"a ancora de classe_simd do voz.lock ({declarada!r}) não é uma "
            f"classe conhecida ({', '.join(CLASSES_SIMD)}) — lock ilegível e "
            f"recusado antes de qualquer síntese; corrija o lock por "
            f"change-proposal.")
    return classe_simd_medida()


def tolerancia() -> dict:
    """O bloco `tolerancia:` do lock (CP-011) — o teto da prova por classe.

    Raso, lido pelo mesmo parser dos outros blocos: residuo_max_dbfs,
    margem_db, ponto, base. AUSENTE devolve {} — e a ausência é
    significado, não esquecimento: sem teto medido e registrado, a
    doutrina é a antiga (bytes em TODA classe, vermelho honesto na
    classe divergente); tolerância sem número é afrouxar fiscal com
    palavra bonita, e não existe aqui.
    """
    if not LOCK.exists():
        raise ErroDeDados(
            "voz.lock nao existe. Sem ancora, nao ha dublagem: cada maquina "
            "sintetizaria com o modelo que tivesse a mao, e o audio commitado "
            "nao seria reproduzivel. Crie o lock ANTES de dublar.")
    return _bloco_raso(LOCK.read_text(encoding="utf-8"), "tolerancia")


def frota() -> dict:
    """O bloco `frota:` do lock (CP-013) — a amostragem da prova da frota.

    Raso, lido pelo mesmo parser dos outros blocos: amostragem (N),
    fracao_avx512f, p_zero_2pct. O N e o numero de copias de cada
    disparo do job dublador, DERIVADO da fracao medida (38/97) como o
    menor N com P(nenhuma copia AVX-512) <= 2% — a decisao do dono
    (24/09/2026, saida (e)): sem amostra decisiva e vermelho nomeado,
    nunca verde por omissao, e o tamanho da amostra e calculo
    registrado (harness/frota/execucoes.json), nao afirmado. AUSENTE
    devolve {} — e quem precisa do N recusa nomeado (lock incompleto),
    nunca chuta um numero.
    """
    if not LOCK.exists():
        raise ErroDeDados(
            "voz.lock nao existe. Sem ancora, nao ha dublagem: cada maquina "
            "sintetizaria com o modelo que tivesse a mao, e o audio commitado "
            "nao seria reproduzivel. Crie o lock ANTES de dublar.")
    return _bloco_raso(LOCK.read_text(encoding="utf-8"), "frota")


def _versao_pacote(nome: str) -> str:
    try:
        return importlib.metadata.version(nome)
    except importlib.metadata.PackageNotFoundError:
        return "ausente"


def _sha_espeak() -> str:
    """A ancora do fonemizador: sha256 dos dados que o wheel do piper embute.

    O espeak-ng mora DENTRO do wheel (espeak-ng-data + a ponte C) e a
    biblioteca nao expoe numero de versao -- o que da para PROVAR e o
    digest dos dados de fonemizacao. Sem isso, wheel reconstruido ou
    dado trocado fonemizariam diferente com a mesma etiqueta de versao.
    """
    try:
        from piper.phonemize_espeak import ESPEAK_DATA_DIR
    except Exception:
        return "ausente"
    if not ESPEAK_DATA_DIR.is_dir():
        return "ausente"
    h = hashlib.sha256()
    for f in sorted(p for p in ESPEAK_DATA_DIR.rglob("*") if p.is_file()):
        rel = f.relative_to(ESPEAK_DATA_DIR).as_posix().encode()
        dados = f.read_bytes()
        h.update(len(rel).to_bytes(4, "big")); h.update(rel)
        h.update(len(dados).to_bytes(8, "big")); h.update(dados)
    return "sha256:" + h.hexdigest()


def _versao_ffmpeg() -> str:
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True,
                           text=True, timeout=60)
    except Exception:
        return "ausente"
    m = re.search(r"ffmpeg version (\S+)", r.stdout or "")
    return m.group(1) if m else "nao legivel"


def _versao_libopus() -> str:
    """A string do PROPRIO libopus, nao a etiqueta do pacote do sistema.

    O mixer chama a biblioteca que o ffmpeg carregou: mesmo binario de
    ffmpeg pode linkar libopus diferente em cada maquina, e o .opus muda
    com ela.
    """
    for nome in ("libopus.so.0", "libopus.so"):
        try:
            lib = ctypes.CDLL(nome)
        except OSError:
            continue
        try:
            lib.opus_get_version_string.restype = ctypes.c_char_p
            return lib.opus_get_version_string().decode().removeprefix("libopus ")
        except Exception:
            return "nao legivel"
    return "nao medivel"


def ambiente_instalado() -> dict:
    """As versoes EFETIVAS do ambiente de sintese — medidas, nunca assumidas.

    Cada chave e medida na hora, no caminho que o dublar de fato usa:
    importlib.metadata para os pacotes, o proprio espeak-ng-data do wheel,
    o binario do ffmpeg, a biblioteca libopus carregada. E a mesma lista
    do bloco ambiente do voz.lock -- quem crescer de um lado tem de
    crescer do outro, e a conferencia e bidirecional.
    """
    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        **{p: _versao_pacote(p) for p in PACOTES},
        "espeak-ng": _sha_espeak(),
        "ffmpeg": _versao_ffmpeg(),
        "libopus": _versao_libopus(),
        # CP-008: a CPU e parte do ambiente -- o onnxruntime despacha kernels
        # pela arquitetura, e a conferencia que passa em arm64 nao prova bytes
        # que nasceram em x86_64.
        "arquitetura": platform.machine(),
    }


def _correcao(pacote: str, esperado: dict) -> str:
    """O comando que alinha o ambiente com a ancora — o erro nao cala."""
    if pacote == "python":
        return f"rode com Python {esperado['python']} (a serie do runtime e ancora)"
    if pacote == "arquitetura":
        return ("a ancora e " + esperado["arquitetura"] +
                " — rode pela imagem ferramentas/dublador/dublar.sh <id> "
                "(build sempre linux/amd64), ou avance o lock por CP com "
                "medicao e redublagem completa, porque os bytes mudam")
    if pacote == "espeak-ng":
        return ("reinstale o wheel que embute o fonemizador: "
                f"pip install --force-reinstall piper-tts=={esperado.get('piper-tts', '?')}")
    if pacote == "ffmpeg":
        return f"instale ffmpeg {esperado['ffmpeg']} (a build inteira e a ancora)"
    if pacote == "libopus":
        return f"instale libopus {esperado['libopus']} (no Debian: apt install libopus0)"
    return f"pip install {pacote}=={esperado[pacote]}"


def conferir_threads(esperado: dict) -> int:
    """As threads do lock contra o ENV de entrada — na entrada, antes de tudo.

    Três recusas, uma por vez: (1) lock SEM a linha threads e lock
    INCOMPLETO — assumir "a maquina resolve" seria ancorar por
    coincidencia, e foi exatamente a loteria que esta ancora fecha; (2)
    ancora ilegivel (nao inteiro, menor que 1) e defeito de lock, nao de
    ambiente; (3) qualquer uma das variaveis de THREADS_ENV ausente ou
    divergente e ambiente divergente, com nome e comando que corrige —
    a saida nunca e sintetizar por cima. Devolve o numero INTEIRO para
    quem constroi a sessao (o dublar), que ainda le de volta o valor
    EFETIVO da sessao e compara de novo: ENV conferido e sessao lida sao
    provas diferentes da mesma ancora.
    """
    import os
    if "threads" not in esperado:
        raise ErroDeDados(
            "voz.lock sem o numero de threads no bloco ambiente (CP-009) — "
            "lock INCOMPLETO: o GEMM do onnxruntime e particionado pelo "
            "numero de threads, e a ordem das somas parciais em float muda "
            "com a particao (medido nas 42 falas reais dos dois filmes: 4 "
            "mudam entre 1 e 2, 33 entre 2 e 3). Assumir as threads da "
            "maquina que roda seria ancorar por coincidencia — e o gate "
            "dublador oscilando com a sorte da frota. Ancore por "
            "change-proposal, como qualquer ancora.")
    try:
        threads = int(str(esperado["threads"]).strip())
    except (TypeError, ValueError):
        raise ErroDeDados(
            f"a ancora de threads do voz.lock nao e um numero inteiro "
            f"({esperado['threads']!r}) — lock ilegivel e recusado antes de "
            f"qualquer sintese; corrija o lock por change-proposal.") from None
    if threads < 1:
        raise ErroDeDados(
            f"a ancora de threads do voz.lock e {threads} — threads < 1 nao "
            f"existe em maquina nenhuma; corrija o lock por change-proposal.")
    divergencias = []
    for var in THREADS_ENV:
        valor = os.environ.get(var, "").strip()
        if not valor:
            divergencias.append(
                f"{var}: ausente no ambiente — o ENV de threads e parte da "
                f"ancora (CP-009), nao enfeite: OpenBLAS/MKL/OMP leem daqui")
        elif valor != str(threads):
            divergencias.append(
                f"{var}: esperado {threads}, encontrado {valor}")
    if divergencias:
        raise ErroDeDados(
            "o ENV de threads NAO e o ancorado em voz.lock (bloco ambiente, "
            "CP-009) — dublar aqui deixaria o GEMM do onnxruntime e as BLAS "
            "do timbre particionados em outro regime, e o audio nasceria "
            "divergente do commitado sem ninguem ter editado nada.\n"
            "  O caminho portavel e a imagem que materializa o lock:\n"
            "      ferramentas/dublador/dublar.sh <id-do-filme>\n"
            "  Ou exporte o ENV da ancora nesta maquina:\n"
            "      export OMP_NUM_THREADS=" + str(threads) +
            " OPENBLAS_NUM_THREADS=" + str(threads) +
            " MKL_NUM_THREADS=" + str(threads) + "\n  "
            + "\n  ".join(divergencias) +
            "\n  O lock avanca por change-proposal; a saida nunca e dublar "
            "por cima da divergencia.")
    return threads


def conferir_ambiente(esperado: dict) -> dict:
    """Confere o ambiente instalado contra o bloco ambiente do voz.lock.

    Levanta ErroDeDados nomeando TODAS as divergencias — pacote, versao
    esperada, versao instalada e o comando que corrige — e devolve o
    ambiente medido para o manifesto (nao sai daqui divergindo, entao o
    devolvido e o ancorado). Sem flag de contorno, de proposito: dublar
    em ambiente divergente produziria audio que ninguem ancorou, e a
    divergencia silenciosa e exatamente o que o lock existe para impedir.
    Bidirecional: componente medido sem ancora e lock atrasado; ancora
    sem medida e codigo atrasado. Os dois sao divida, nao preferencia.
    Excecao proposital (CP-008): lock SEM arquitetura e lock INCOMPLETO,
    nao "medida a mais" — assumir x86_64 por padrao seria ancorar por
    coincidencia, e a saida e recusar ate alguem medir e ancorar por CP.
    Excecao igual e proposital (CP-009): `threads` NAO entra neste loop —
    threads nao e propriedade instalada, e sim ancora LIDA DA SESSAO que
    o dublar constroi com o valor do lock (dublar le de volta o numero
    EFETIVO e compara de novo); a face externa dela no ambiente (OMP/
    OpenBLAS/MKL) tem conferencia propria em conferir_threads, na entrada.
    Excecao igual e proposital (CP-011): `classe_simd` tambem nao entra —
    classe de SIMD nao e propriedade instalada, e o hardware da maquina:
    o dublar a MEDE (flags) e grava o medido no audio.json, e o fiscal
    de redublagem compara o gravado contra o lock quando o audio e
    commitado. Divergencia de classe no ambiente de quem RODA nao e
    recusa de sintese (a prova por classe precisa medir na classe
    divergente); divergencia no audio COMMITADO e divida apontada.
    """
    instalado = ambiente_instalado()
    divergencias = []
    for pacote in sorted((set(esperado) | set(instalado)) - {"threads", "classe_simd"}):
        esp, inst = esperado.get(pacote), instalado.get(pacote)
        if esp == inst:
            continue
        if esp is None:
            if pacote == "arquitetura":
                divergencias.append(
                    f"arquitetura: o ambiente mede {inst}, mas o voz.lock nao "
                    f"ancorea arquitetura nenhuma — lock INCOMPLETO (CP-008): "
                    f"onnxruntime escolhe kernels pela arquitetura da CPU, e "
                    f"assumir {inst} por padrao seria ancorar por coincidencia. "
                    f"Meça platform.machine() na maquina que dublou e ancöre "
                    f"por change-proposal.")
            else:
                divergencias.append(
                    f"{pacote}: o ambiente mede {inst}, mas o voz.lock nao ancora — "
                    f"componente sem ancora e lock atrasado, nao medida a mais")
        elif inst is None:
            divergencias.append(
                f"{pacote}: o lock ancora, mas o ambiente_instalado() nao mede — "
                f"codigo e lock cresceram separados, e isso e divida de CP")
        else:
            divergencias.append(
                f"{pacote}: esperado {esp}, instalado {inst}. "
                f"Corrige: {_correcao(pacote, esperado)}")
    if divergencias:
        raise ErroDeDados(
            "o ambiente de sintese NAO e o ancorado em voz.lock (bloco "
            "ambiente, CP-007/CP-008/CP-009) — dublar aqui produziria audio divergente "
            "do commitado sem ninguem ter editado nada.\n"
            "  O caminho portatil e a imagem que materializa o lock:\n"
            "      ferramentas/dublador/dublar.sh <id-do-filme>\n"
            "  Ou corrija o ambiente desta maquina, pacote a pacote:\n  "
            + "\n  ".join(divergencias) +
            "\n  O lock avanca por change-proposal; a saida nunca e dublar "
            "por cima da divergencia.")
    return instalado


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _copiar_de(origem: Path, a: dict) -> bool:
    """Um download previo ao lado da suite evita rede. So serve se bater."""
    if not origem.is_dir():
        return False
    for rel in a["arquivos"]:
        f = origem / rel
        if not f.exists() or _sha256(f) != a["arquivos"][rel]:
            return False
    for rel in a["arquivos"]:
        alvo = DESTINO / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem / rel, alvo)
    return True


def _baixar(a: dict, base_url: str) -> None:
    for rel in a["arquivos"]:
        url = f"{base_url.rstrip('/')}/{rel}"
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                dados = r.read()
        except Exception as e:
            raise ErroDeDados(
                f"nao consegui baixar '{rel}' de {a['origem']}: {e}\n"
                f"  O modelo e bem publico (piper-voices). Baixe a mao, deixe os "
                f"arquivos em workspace/voz/, e rode de novo: o lock confere o "
                f"hash antes de usar."
            ) from None
        alvo = DESTINO / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(dados)


def materializar(forcar: bool = False) -> Path:
    """Garante workspace/voz/ com o modelo ancorado, e confere cada hash."""
    a = ancora()
    completo = all((DESTINO / rel).exists() for rel in a["arquivos"])
    if forcar or not completo:
        DESTINO.mkdir(parents=True, exist_ok=True)
        # Um vizinho com o modelo ja baixado evita rede (mesma graca de lei.py).
        candidatos = [RAIZ / "_voz-origem", RAIZ.parent / "piper-voices", WORKSPACE / "piper-voices"]
        if not any(_copiar_de(c, a) for c in candidatos):
            _baixar(a, a["origem"])

    divergem = []
    for rel, esperado in a["arquivos"].items():
        f = DESTINO / rel
        if not f.exists():
            divergem.append(f"{rel}: ausente")
        elif _sha256(f) != esperado:
            divergem.append(f"{rel}: {_sha256(f)[:12]} != {esperado[:12]} declarado")
    if divergem:
        raise ErroDeDados(
            "o modelo local NAO e o modelo ancorado em voz.lock:\n  "
            + "\n  ".join(divergem) +
            "\n  Dublar com pesos divergentes produziria um audio que ninguem "
            "declarou. Baixe o modelo do lock, ou avance o lock por "
            "change-proposal -- nunca dublar por cima da divergencia."
        )
    return DESTINO
