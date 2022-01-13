import errno
import os
import yaml
from invoke import task


config = yaml.load(open("./config.yaml"), yaml.FullLoader)


@task
def tf2onnx(ctx, model, cuda=0):
    target = os.path.join(config["path"]["tf"], model)
    if not os.path.exists(target):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), target)

    output = os.path.join(config["path"]["onnx"], model)
    print(os.path.dirname(output))
    os.makedirs(os.path.dirname(output), exist_ok=True)

    # Check if the model is compiled in NCHW format
    nchw = config["nchw"].get(model)

    if nchw is not None:
        cmd = f"CUDA_VISIBLE_DEVICES={cuda} python -m tf2onnx.convert --saved-model {target} --output {output} --inputs-as-nchw {nchw} --rename-inputs input --rename-outputs output"
    else:
        cmd = f"CUDA_VISIBLE_DEVICES={cuda} python -m tf2onnx.convert --saved-model {target} --output {output} --rename-inputs input --rename-outputs output"
    print(cmd)
    ctx.run(cmd)


@task
def onnx2trt(ctx, model, cuda=0, batch=128):
    bin_path = config["bin"]["trt"]
    target = os.path.join(config["path"]["onnx"], model)
    if not os.path.exists(target):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), target)

    output = os.path.join(config["path"]["trt"], model)
    os.makedirs(os.path.dirname(output), exist_ok=True)

    output = os.path.join(config["path"]["trt"], model)

    cmd = f"CUDA_VISIBLE_DEVICES={cuda} {bin_path} --onnx={target} --verbose"
    cmd += f" --explicitBatch --minShapes=input:{batch}x3x180x80"
    cmd += f" --optShapes=input:{batch}x3x180x80 --maxShapes=input:{batch}x3x180x80"
    cmd += f" --workspace=8500 --fp16 --saveEngine={output} --buildOnly"

    print(cmd)
    ctx.run(cmd)


@task
def tf2trt(ctx, model, cuda=0):
    tf2onnx(ctx, model, cuda)
    onnx2trt(ctx, model, cuda)
