from invoke import task
import itertools


dataset = [
        ('amsterdam', 50, 30),
        ('archie', 80, 50),
        ('jackson', 50, 30),
        ('shinjuku', 80, 40),
        ('taipei', 80, 40),
        ('venice', 50, 30),
        ]

@task
def explore(ctx, force=False, start_port=8080):
    day = [1, 2, 3]
    cuda = [0, 1, 2, 3]

    track_port = start_port
    dnn_port = start_port + 1
    cuda_idx = 0
    for (ds, maxage, minhit), d in itertools.product(dataset, day):
        c = cuda[cuda_idx]
        cuda_idx  = (cuda_idx + 1) % len(cuda)
        ctx.run(f"python launch.py {ds} {d} {track_port} {dnn_port} {c} {maxage} {minhit}", echo=True, disown=True, dry=not force)
        track_port += 2
        dnn_port += 2


@task
def terminate(ctx, dry=False):
    for ds, *_ in dataset:
        ctx.run(f"pkill -f 'python launch.py {ds}.*'", echo=True, dry=dry, warn=True)
    ctx.run("pkill -f 'bbox_aggregator*'", echo=True, dry=dry, warn=True)


