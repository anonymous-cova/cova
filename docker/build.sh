#!/bin/bash

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 TAG_NAME"
    exit 1
fi

# DOCKER_BUILDKIT=1 docker build --progress=plain . -t cova:$1
DOCKER_BUILDKIT=1 docker build . -t cova:$1
