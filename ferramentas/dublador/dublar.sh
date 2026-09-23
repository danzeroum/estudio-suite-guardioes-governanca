#!/bin/sh
# O dublar portatil (CP-008): a imagem que materializa o voz.lock.
#
#   ./ferramentas/dublador/dublar.sh <id-do-filme>
#
# Constrói a imagem (com cache de camadas do docker) e roda
# `python3 -m estudio_suite dublar <id>` DENTRO dela, com:
#   - o repositorio montado em /app: o codigo que roda e o do checkout, e
#     o audio regenerado cai no lugar de sempre (filmes/<id>/audio/);
#   - workspace/voz em volume, para nao baixar o modelo a cada vez:
#     * com ESTUDIO_VOZ_CACHE=<dir-do-host> (o CI usa: cache restaurado),
#       a pasta e bind-mountada;
#     * sem a variavel, um volume nomeado (estudio-suite-voz) persiste o
#       modelo entre execucoes na maquina local.
#     workspace/amostras segue no repositorio (gitignored) -- e cache do
#     CI por conta propria.
#
# O build e SEMPRE --platform linux/amd64: a ancora do lock e a
# arquitetura que sintetizou os filmes publicados, e dublar em outra
# arquitetura produziria outros bytes (o dublar recusa, de dentro). Em
# host arm64 a imagem roda emulada -- lento, mas ancora-conforme.
#
# Requisitos: docker com buildx (padrao em instalacoes atuais). Sem
# docker, dublar direto so funciona se o ambiente da maquina bater com o
# voz.lock -- e o dublar mesmo quem confere e recusa.
set -eu

fid="${1:-}"
if [ -z "$fid" ]; then
    echo "uso: ferramentas/dublador/dublar.sh <id-do-filme>" >&2
    exit 64
fi

# A raiz do repositorio a partir deste script (ferramentas/dublador/).
RAIZ=$(cd "$(dirname "$0")/../.." && pwd)
DOCKERFILE="$RAIZ/ferramentas/dublador/Dockerfile"
IMG=estudio-dublador:voz-lock

if ! command -v docker >/dev/null 2>&1; then
    echo "ERRO: docker nao encontrado. Sem ele, o caminho e ter o ambiente" >&2
    echo "      do voz.lock na propria maquina (o dublar confere e recusa" >&2
    echo "      na divergencia, nomeando pacote e correcao)." >&2
    exit 2
fi

echo "== construindo $IMG (cache de camadas; instantaneo se nada mudou)"
if docker buildx version >/dev/null 2>&1; then
    docker buildx build --platform linux/amd64 --load \
        -t "$IMG" -f "$DOCKERFILE" "$RAIZ"
else
    docker build --platform linux/amd64 -t "$IMG" -f "$DOCKERFILE" "$RAIZ"
fi

# O volume do modelo: caminho do CI (bind) ou volume nomeado (local).
VOZ_ARGS="-v estudio-suite-voz:/app/workspace/voz"
if [ -n "${ESTUDIO_VOZ_CACHE:-}" ]; then
    mkdir -p "$ESTUDIO_VOZ_CACHE"
    VOZ_ARGS="-v $ESTUDIO_VOZ_CACHE:/app/workspace/voz"
fi

echo "== dublando $fid dentro da imagem (ambiente do lock conferido pelo dublar)"
exec docker run --rm --platform linux/amd64 \
    -v "$RAIZ":/app \
    $VOZ_ARGS \
    -w /app \
    "$IMG" \
    python3 -m estudio_suite dublar "$fid"
