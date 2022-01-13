import subprocess
import os

import yaml
import itertools as it
import time

import argparse

config = yaml.load(open("./config.yaml"), yaml.FullLoader)

CMD = "numactl -C 0-15 ./xvdec.sh {} {} {} {} {} {} {} > {}"


def call_proc(cmd):
    p = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, shell=True
    )
    _, err = p.communicate()
    return err


def generate_and_cmd(
    cc,
    minhits,
    maxage,
    video_path,
    model_path,
    infer_i,
    rnn_path,
    output_path,
):

    err = call_proc(
        CMD.format(
            cc, minhits, maxage, video_path, model_path, infer_i, rnn_path, output_path
        )
    )
    return err


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("LOG_FILE")
    args = parser.parse_args()

    results = []

    with open(args.LOG_FILE, "w", 1) as f:
        for t in config["target"]:
            for m in config["model"]:
                ds = config["dataset"][t]
                for video_path, gt_path in zip(ds["video"], ds["gt"]):
                    for cc, minhits in it.product(ds["cc"], ds["minhits"]):
                        for infer_i in ds["inferi"]:
                            day = os.path.splitext(os.path.basename(video_path))[0]
                            model_name = os.path.splitext(os.path.basename(m))[0]
                            prefix = f"{t}-{day}-{cc}-{minhits}-{infer_i}-{model_name}"
                            output_path = os.path.join("logs", prefix + ".txt")

                            start = time.time()
                            err = generate_and_cmd(
                                cc,
                                minhits,
                                minhits,
                                video_path,
                                ds["model"],
                                infer_i,
                                m,
                                output_path,
                            )
                            if err:
                                print(err.decode())

                            print(f"{prefix}: {time.time() - start}", file=f)
