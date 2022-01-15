import sys, os
import inspect
import time

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from cova import CovaPipeline
from timeit import default_timer as timer
import os
import pathlib

def generate_output_dir(output_root, output_name):
    output_dir = pathlib.Path(output_root) / output_name
    output_dir.mkdir(exist_ok=True, parents=True)
    return output_dir

def generate_config(src, dst, **kwargs):
    with open(src) as fsrc, open(dst, 'w') as fdst:
        for line in fsrc:
            fdst.write(line.format(**kwargs))


if __name__ == "__main__":
    import argparse
    import yaml
    import subprocess
    import shlex

    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("day")
    parser.add_argument("maxage")
    parser.add_argument("minhit")
    parser.add_argument("alpha")
    parser.add_argument("beta")
    parser.add_argument("--output-root", nargs='?', default='./logs')
    parser.add_argument("--config-file", nargs="?", default="alpha-beta.yaml")
    args = vars(parser.parse_args())


    os.environ["CUDA_VISIBLE_DEVICES"] = str(args['cuda'])
    output_dir = generate_output_dir(
            args['output_root'],
            f"{args['dataset']}-{args['day']}-{args['alpha']}-{args['beta']}")
    new_config = output_dir / 'config.yaml'
    generate_config('config.yaml', new_config, **args)

    config = yaml.safe_load(open(new_config))

    with open(output_dir / 'log.txt', 'w+') as f:
        pipeline = CovaPipeline(config, f=f)
        print("Created Pipeline")
        pipeline.start()

    time.sleep(30)
