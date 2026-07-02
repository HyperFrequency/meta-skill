# Ray Tune Hyperparameter Optimization

Ray Tune drives distributed hyperparameter sweeps and composes directly with
Ray Train. A `Tuner` wraps either a plain function trainable or a `TorchTrainer`
(any Ray Train `Trainer`), runs many trials in parallel across the cluster, and
selects the best result.

> API note: the modern Ray (2.x, verified against 2.40+) namespace is
> `ray.tune` for tuning and `ray.train` for training. `RunConfig`,
> `CheckpointConfig`, and `FailureConfig` are exposed under `ray.tune.*`
> (and the equivalents under `ray.train.*` for the inner Trainer). `tune.report`
> / `ray.train.report` replace the older `tune.track.log`.

## Search space

Define the space as a dict of `tune` samplers passed via `param_space`:

```python
from ray import tune

param_space = {
    "lr": tune.loguniform(1e-5, 1e-2),       # log-uniform float
    "batch_size": tune.choice([16, 32, 64]),  # categorical
    "dropout": tune.uniform(0.0, 0.5),        # uniform float
    "num_layers": tune.randint(2, 8),         # integer
    "optimizer": tune.grid_search(["adam", "sgd"]),  # exhaustive grid
}
```

`grid_search` is multiplied across every other sampler; `choice`/`uniform`/etc.
are sampled `num_samples` times.

## Schedulers (early stopping)

Schedulers stop unpromising trials early to reallocate compute.

### ASHA (Async HyperBand) — the default workhorse

```python
from ray.tune.schedulers import ASHAScheduler

scheduler = ASHAScheduler(
    time_attr="training_iteration",
    max_t=100,          # max iterations per trial
    grace_period=10,    # minimum iterations before a trial can be stopped
    reduction_factor=2, # keep top 1/2 at each rung
)
```

Pass `metric` / `mode` on `TuneConfig` (preferred) rather than on the scheduler.

## Search algorithms

Schedulers decide *when to stop*; search algorithms decide *what to try next*.
Default is random/grid search. Bayesian optimizers explore smarter.

### Optuna (recommended general-purpose; `pip install optuna`)

```python
from ray.tune.search.optuna import OptunaSearch

search_alg = OptunaSearch()  # TPE sampler by default
```

### HyperOpt (`pip install hyperopt`)

```python
from ray.tune.search.hyperopt import HyperOptSearch

search_alg = HyperOptSearch()  # define space via tune samplers or hyperopt hp.*
```

Other built-ins: `BayesOptSearch`, `BOHB` (`TuneBOHB` + `HyperBandForBOHB`),
`AxSearch`, `BasicVariantGenerator` (default). Wrap any of them in
`ConcurrencyLimiter` to cap simultaneous trials a Bayesian optimizer evaluates.

## Putting it together

```python
from ray import tune
from ray.tune.schedulers import ASHAScheduler
from ray.tune.search.optuna import OptunaSearch

tuner = tune.Tuner(
    train_func,  # or a TorchTrainer instance for distributed-per-trial training
    param_space=param_space,
    tune_config=tune.TuneConfig(
        metric="loss",
        mode="min",
        num_samples=50,                 # trials to sample
        scheduler=ASHAScheduler(),
        search_alg=OptunaSearch(),
        max_concurrent_trials=8,        # cap parallel Train driver processes
    ),
    run_config=tune.RunConfig(
        name="my-sweep",
        # Multi-node: point storage at shared S3 / NFS so all nodes can read.
        # storage_path="s3://my-bucket/ray_results",
    ),
)

results = tuner.fit()
best = results.get_best_result(metric="loss", mode="min")
print(best.config, best.metrics)
```

## Tune + Ray Train (distributed training per trial)

Each Tune trial can itself be a distributed Ray Train run. The recommended
pattern launches the `TorchTrainer` inside a Tune driver function so Tune
manages the sweep and Train manages the workers:

```python
import ray.train, ray.train.torch, ray.tune
from ray.tune.integration.ray_train import TuneReportCallback

def train_fn_per_worker(train_loop_config):
    lr = train_loop_config["lr"]
    # ... ray.train.torch.prepare_model(...), training loop ...
    ray.train.report({"loss": loss})

def train_driver_fn(config):
    trainer = ray.train.torch.TorchTrainer(
        train_fn_per_worker,
        train_loop_config=config["train_loop_config"],
        scaling_config=ray.train.ScalingConfig(num_workers=config["num_workers"], use_gpu=True),
        run_config=ray.train.RunConfig(
            name=f"train-trial_id={ray.tune.get_context().get_trial_id()}",
            callbacks=[TuneReportCallback()],  # forward metrics to the Tuner
        ),
    )
    trainer.fit()

tuner = ray.tune.Tuner(
    train_driver_fn,
    param_space={
        "num_workers": ray.tune.choice([2, 4]),
        "train_loop_config": {"lr": ray.tune.grid_search([1e-3, 3e-4])},
    },
    tune_config=ray.tune.TuneConfig(max_concurrent_trials=2),
)
tuner.fit()
```

## Population-Based Training (PBT)

PBT evolves hyperparameters *during* training: it periodically copies weights
from top performers to bottom performers and perturbs their hyperparameters.
Great for schedules (e.g. learning-rate) that no static value captures.

```python
from ray.tune.schedulers import PopulationBasedTraining

perturbation_interval = 5
pbt = PopulationBasedTraining(
    time_attr="training_iteration",
    perturbation_interval=perturbation_interval,
    quantile_fraction=0.5,      # bottom half exploits the top half
    resample_probability=0.5,
    hyperparam_mutations={
        "lr": tune.loguniform(1e-5, 1e-2),
        "momentum": tune.uniform(0.8, 0.99),
    },
)

tuner = tune.Tuner(
    train_func,
    tune_config=tune.TuneConfig(metric="accuracy", mode="max", num_samples=8, scheduler=pbt),
    run_config=tune.RunConfig(
        # Align checkpointing with perturbation so PBT exploits fresh weights.
        checkpoint_config=tune.CheckpointConfig(checkpoint_frequency=perturbation_interval, num_to_keep=4),
    ),
    param_space={"lr": 1e-3, "momentum": 0.9},
)
tuner.fit()
```

Key PBT rule: make `checkpoint_frequency` equal to (or a divisor of)
`perturbation_interval`, otherwise PBT resumes from stale checkpoints.

## Resuming a sweep

```python
tuner = tune.Tuner.restore(path="~/ray_results/my-sweep", trainable=train_func)
tuner.fit()
```
