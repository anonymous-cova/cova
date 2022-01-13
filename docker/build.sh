#!/bin/bash

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 TAG_NAME"
    exit 1
fi

DOCKER_BUILDKIT=1 docker build . -t jinwooh/deepstream:$1
# DOCKER_BUILDKIT=1 docker build --progress=plain .
