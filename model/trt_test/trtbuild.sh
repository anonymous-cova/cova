#!/bin/bash

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 BATCH_SIZE WORKSPACE_MB CUDA_VISIBLE_DEVICES"
    exit 1
fi

BATCH_SIZE=$1
WORKSPACE_MB=$2


CUDA_VISIBLE_DEVICES=$3 ~/TensorRT-7.0.0.11/bin/trtexec --onnx=model.onnx --verbose --explicitBatch \
    --shapes='"'"'input_tensor:0'"'"':"$BATCH_SIZE"x11x1x270x480 \
    --minShapes='"'"'input_tensor:0'"'"':"$BATCH_SIZE"x11x1x270x480 \
    --optShapes='"'"'input_tensor:0'"'"':"$BATCH_SIZE"x11x1x270x480 \
    --maxShapes='"'"'input_tensor:0'"'"':"$BATCH_SIZE"x11x1x270x480 \
    --workspace="$WORKSPACE_MB" \
    --buildOnly --saveEngine=b"$BATCH_SIZE".trt  --fp16

