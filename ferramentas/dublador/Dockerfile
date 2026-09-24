# A imagem dubladora (CP-008): o voz.lock materializado em container.
#
# O lock e a UNICA fonte de versoes -- este Dockerfile nao digita versao de
# pacote Python nenhum: os pins vem de ci/pins_do_lock.py, que le o bloco
# ambiente do voz.lock pelo MESMO parser do dublar. Versao digitada em
# segundo lugar seria defeito, nao redundancia.
#
# Base: python:3.12-slim-trixie, PINADA POR DIGEST. Por que esta base: o
# bloco ambiente do lock foi medido numa maquina Debian 13 (trixie) com a
# serie 3.12 do python -- e e o trixie que serve o ffmpeg 7.1.5-0+deb13u1
# e o libopus 1.5.2 que o lock ancora (medido em 2026-09-23: deb.debian.org
# trixie/main amd64 serve exatamente 7:7.1.5-0+deb13u1 e libopus0 1.5.2-2).
# O digest congela a base inteira (glibc incluso); a tag fica ao lado para
# o humano ler. Digest do indice multi-arquitetura -- o build com
# --platform linux/amd64 resolve o manifest amd64 (44ff437bba879d49...).
FROM python:3.12-slim-trixie@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# CP-009: o ENV de threads da ancora. O numero NAO e digitado aqui: quem
# constroi a imagem le o voz.lock FORA (ci/pins_do_lock.py --threads) e
# entrega via --build-arg — threads vem do lock, de nenhum outro lugar.
# OMP rege o pool do onnxruntime, OPENBLAS/MKL regem as BLAS que o motor
# de timbre usa: as tres variaveis espelham a MESMA ancora. Build SEM o
# build-arg deixa o ENV vazio — e o dublar RECUSA na entrada (valor
# ausente e recusa nomeada, nao chute): imagem mal construida falha
# alto, imagem errada nao dubla em silencio.
ARG THREADS_DO_LOCK
ENV OMP_NUM_THREADS=${THREADS_DO_LOCK} \
    OPENBLAS_NUM_THREADS=${THREADS_DO_LOCK} \
    MKL_NUM_THREADS=${THREADS_DO_LOCK}

# O ffmpeg e o libopus do mix, na versao EXATA do lock. A familia libav*
# vem junto no mesmo pin: no Debian ela nasce do MESMO source package do
# ffmpeg e carrega a mesma versao -- pinar so o binario deixaria a porta
# aberta para um libav atualizado misturar-se a um ffmpeg antigo e mudar
# bytes com a mesma etiqueta de versao. Se o trixie deixar de servir estas
# versoes (security update, por ex.), o apt FALHA ALTO aqui -- e a correcao
# e datar o snapshot.debian.org neste RUN (plano B registrado na CP-008),
# nunca aceitar a versao nova em silencio.
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
        ffmpeg=7:7.1.5-0+deb13u1 \
        libavcodec61=7:7.1.5-0+deb13u1 \
        libavdevice61=7:7.1.5-0+deb13u1 \
        libavfilter10=7:7.1.5-0+deb13u1 \
        libavformat61=7:7.1.5-0+deb13u1 \
        libavutil59=7:7.1.5-0+deb13u1 \
        libswresample5=7:7.1.5-0+deb13u1 \
        libswscale8=7:7.1.5-0+deb13u1 \
        libopus0=1.5.2-2 \
    && rm -rf /var/lib/apt/lists/*

# O lock, o parser e o vocabulario que o parser carrega -- so o necessario
# para o build perguntar ao lock. comum.py le o vocabulario (acoes, easings,
# camadas) do motor JS em tempo de import: UMA fonte de verdade, e ela mora
# no motor -- a imagem tambem a le de la, nao de uma copia.
# O build context e a raiz do repositorio (ver .dockerignore: contexto
# minimo de proposito). Em RUNTIME o repositorio e montado por cima: o
# codigo que roda e o do checkout, a imagem so carrega o AMBIENTE.
COPY voz.lock /app/voz.lock
COPY estudio_suite/__init__.py /app/estudio_suite/__init__.py
COPY estudio_suite/comum.py /app/estudio_suite/comum.py
COPY estudio_suite/voz.py /app/estudio_suite/voz.py
COPY motor/js/filme.js motor/js/interp.js motor/js/palco.js /app/motor/js/
COPY ci/pins_do_lock.py /app/ci/pins_do_lock.py

# Os pins do lock: piper-tts (com o espeak-ng-data embutido -- o dublar
# confere o sha256 contra o lock DE DENTRO da imagem), onnxruntime e o
# numpy/scipy do motor de timbre. Aqui nao ha versao escrita a mao: quem
# disse 1.8.0/1.30.0/2.1.3/1.14.1 foi o voz.lock, so ele.
RUN pip install $(python3 /app/ci/pins_do_lock.py --so piper-tts,onnxruntime,numpy,scipy)

WORKDIR /app
