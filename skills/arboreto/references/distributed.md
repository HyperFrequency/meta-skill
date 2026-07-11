# Distributed Computing with Dask

Arboreto runs on Dask, so the same inference code scales from a single machine's
cores to a multi-node cluster. This file covers local execution, custom clients,
remote clusters, monitoring, and tuning. For the `dask` engine itself, see the
`dask` skill.

## Why It Parallelizes

Each target gene's regressor is independent of the others, so arboreto builds a
Dask **task graph** with one regression task per target and lets Dask schedule
those tasks across whatever workers are available. Nothing about your call
changes between a laptop and a cluster except the `client_or_address` you pass.

## Local Multiprocessing (default)

With no client argument, arboreto starts a local Dask cluster using all cores.
Sufficient for most datasets and needs no setup.

```python
from arboreto.algo import grnboost2

network = grnboost2(expression_data=expression_matrix, tf_names=tf_names)
```

## Custom Local Client

Create your own `LocalCluster` + `Client` to cap resources, open the dashboard,
or reuse one cluster across several runs.

```python
from distributed import LocalCluster, Client
from arboreto.algo import grnboost2

if __name__ == '__main__':
    local_cluster = LocalCluster(
        n_workers=10,
        threads_per_worker=1,     # 1 thread/worker avoids GIL contention in sklearn
        memory_limit=8e9,         # bytes per worker (8 GB)
    )
    client = Client(local_cluster)

    network = grnboost2(
        expression_data=expression_matrix,
        tf_names=tf_names,
        client_or_address=client,
    )

    client.close()
    local_cluster.close()
```

## Reusing One Client Across Runs (e.g. multi-seed consensus)

Spin the cluster up once and pass the same client to every call — the natural
pattern for consensus networks over seeds or comparing algorithms.

```python
from distributed import LocalCluster, Client
from arboreto.algo import grnboost2, genie3

if __name__ == '__main__':
    client = Client(LocalCluster(n_workers=8, threads_per_worker=1))

    networks = [
        grnboost2(expression_data=expression_matrix, tf_names=tf_names,
                  client_or_address=client, seed=s)
        for s in (42, 123, 777)
    ]
    # e.g. keep edges that appear with high importance across all seeds
    baseline = genie3(expression_data=expression_matrix, tf_names=tf_names,
                      client_or_address=client)

    client.close()
```

## Remote Cluster

For datasets too large for one machine, connect to a Dask scheduler running on a
cluster.

1. Start the scheduler on the head node:
   ```bash
   dask-scheduler
   # Scheduler at tcp://10.0.0.5:8786
   ```
2. Start workers on compute nodes (flag names vary by `distributed` version;
   `--nworkers`/`--nprocs` set processes per node):
   ```bash
   dask-worker tcp://10.0.0.5:8786 --nworkers 4 --nthreads 1 --memory-limit 16GB
   ```
3. Point arboreto at the scheduler:
   ```python
   from distributed import Client
   from arboreto.algo import grnboost2

   if __name__ == '__main__':
       client = Client('tcp://10.0.0.5:8786')
       network = grnboost2(expression_data=expression_matrix,
                           tf_names=tf_names, client_or_address=client)
       client.close()
   ```

You can also pass the scheduler address string directly as `client_or_address`.

## Monitoring

`Client()` prints a dashboard URL (default `http://localhost:8787/status`)
showing task progress, per-worker CPU/memory, the live task stream, and
bottlenecks. For a text log of inference progress, pass `verbose=True` to the
algorithm.

## Performance Tuning

- **`threads_per_worker=1`** — scikit-learn regression is CPU-bound and holds the
  GIL; prefer more single-threaded workers over fewer multi-threaded ones.
- **Narrow the regulators** — passing a `tf_names` list instead of `'all'` is the
  biggest single speedup, and it sharpens the biology.
- **Filter low-variance genes** before inference to shrink the problem.
- **Prefer a DataFrame** over a raw NumPy array for Dask efficiency.
- **Memory-bound?** raise `memory_limit` per worker; **CPU-bound?** add workers.
- Watch worker memory in the dashboard — workers that exceed their limit are
  killed and their tasks retried, which silently slows the run.
