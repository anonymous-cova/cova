#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
IMAGE=jinwooh/deepstream
TAG=py3.7

if [ "$#" -eq 2 ]; then
    echo "Usage: $0 TAG_NAME CONTAINER_NAME"
    TAG="$1"
    NAME="$2"
fi

set -x

docker run -it --net=host \
    --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
    --gpus 'all,"capabilities=compute,utility,video"' \
    -v ${SCRIPT_DIR}/..:/workspace \
    -v /mnt/ssd4:/ssd4 \
    -e DISPLAY=$DISPLAY \
    --shm-size="47G" \
    ${IMAGE}:${TAG} zsh
