import sys, os
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from cova import CovaPipeline
from timeit import default_timer as timer
import os
import pathlib

def generate_output_dir(output_root):
    output_root = pathlib.Path(output_root)
    output_root.mkdir(exist_ok=True, parents=True)
    i = 0
    while True:
        output_dir = output_root / f'trial-{i}'
        if not output_dir.exists():
            break
        i += 1

    output_dir.mkdir()
    return output_dir


if __name__ == "__main__":
    import argparse
    import yaml
    import shutil

    parser = argparse.ArgumentParser()
    parser.add_argument("CONFIG_FILE", nargs='?', default='./config.yaml')
    args = parser.parse_args()

    config = yaml.safe_load(open(args.CONFIG_FILE))

    output_dir = generate_output_dir(config['output_root'])
    shutil.copy(args.CONFIG_FILE, output_dir)

    with open(output_dir / 'log.txt', 'w+') as f:
        pipeline = CovaPipeline(config, f=f)
        print("Created Pipeline")
        pipeline.start()
