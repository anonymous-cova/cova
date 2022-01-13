#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 BATCH_SIZE WORKSPACE_MiB"
    exit 1
fi

BATCH_SIZE=$1
WORKSPACE_MiB=$2

CUDA_VISIBLE_DEVICES=1 ~/TensorRT-7.0.0.11/bin/trtexec --verbose --explicitBatch \
    --shapes='"'"'input_tensor:0'"'"':"$BATCH_SIZE"x11x1x270x480 \
    --minShapes='"'"'input_tensor:0'"'"':"$BATCH_SIZE"x11x1x270x480 \
    --optShapes='"'"'input_tensor:0'"'"':"$BATCH_SIZE"x11x1x270x480 \
    --maxShapes='"'"'input_tensor:0'"'"':"$BATCH_SIZE"x11x1x270x480 \
    --loadEngine=b"$BATCH_SIZE".trt  --fp16 \
    --iterations=1000 --avgRuns=1000 --workspace="$WORKSPACE_MiB"

