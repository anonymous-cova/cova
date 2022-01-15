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

def generate_output_dir(output_root, dataset, day):
    output_dir = pathlib.Path(output_root) / f'{dataset}-{day}'
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
    parser.add_argument("track_port")
    parser.add_argument("dnn_port")
    parser.add_argument("cuda")
    parser.add_argument("maxage")
    parser.add_argument("minhit")
    parser.add_argument("--output-root", nargs='?', default='./logs')
    args = vars(parser.parse_args())


    os.environ["CUDA_VISIBLE_DEVICES"] = str(args['cuda'])
    output_dir = generate_output_dir(args['output_root'], args['dataset'], args['day'])
    new_config = output_dir / 'config.yaml'
    generate_config('config.yaml', new_config, **args)

    config = yaml.safe_load(open(new_config))

    agg = '../../bbox_aggregator/target/release/bbox_aggregator -c -d {dnn_port} -t {track_port} -g {cuda} {output_dir} {maxage}'
    agg = subprocess.Popen(shlex.split(agg.format(output_dir=str(output_dir), **args)))

    with open(output_dir / 'log.txt', 'w+') as f:
        pipeline = CovaPipeline(config, f=f)
        print("Created Pipeline")
        pipeline.start()

    time.sleep(30)
    agg.terminate()
