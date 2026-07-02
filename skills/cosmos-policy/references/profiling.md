# Inference profiling

Measure Cosmos Policy action-prediction latency and throughput on a cluster or
local GPU. This uses standard, framework-level timing — no repo-private flags —
so it stays valid across `cosmos-policy` releases.

## Prerequisites

Set the same headless rendering and cache environment used for evaluation
(`CUDA_VISIBLE_DEVICES`, `MUJOCO_EGL_DEVICE_ID`, `MUJOCO_GL=egl`,
`PYOPENGL_PLATFORM=egl`) so the policy loads on the intended GPU.

## Wall-clock baseline

The cheapest signal is the smoke-eval wall time. Run the LIBERO smoke command
(see `libero-commands.md`) with `--num_trials_per_task 1` and divide elapsed
time by the number of denoising steps to get a rough per-action cost. Use this
to confirm the GPU is actually engaged before doing fine-grained timing.

## GPU-accurate per-call timing

`torch.cuda.Event` gives device-accurate latency (CPU timers miss async kernel
launches). Wrap the policy's action prediction call. `synchronize()` before and
after each measured region; record steady-state numbers, discarding the first
few warmup iterations (CUDA graph capture, autotuning, and cache fills inflate
them).

```python
import torch

def time_action_inference(predict_fn, observation, warmup=5, iters=50):
    """predict_fn(observation) -> action chunk. Returns mean/p50/p95 ms."""
    for _ in range(warmup):
        predict_fn(observation)
    torch.cuda.synchronize()

    start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    samples_ms = []
    for _ in range(iters):
        start.record()
        predict_fn(observation)
        end.record()
        torch.cuda.synchronize()
        samples_ms.append(start.elapsed_time(end))

    samples_ms.sort()
    n = len(samples_ms)
    return {
        "mean_ms": sum(samples_ms) / n,
        "p50_ms": samples_ms[n // 2],
        "p95_ms": samples_ms[int(n * 0.95)],
    }
```

Latency scales with `--num_denoising_steps_action` (diffusion action head) and
`--chunk_size` (actions produced per forward pass). Throughput in actions/sec is
`chunk_size / per_call_seconds` when running open-loop; profile both the smaller
LIBERO config (`--chunk_size 16`) and the larger RoboCasa config
(`--chunk_size 32`) since they exercise different kernel shapes.

## Memory profiling

```python
import torch
torch.cuda.reset_peak_memory_stats()
predict_fn(observation)
torch.cuda.synchronize()
print(f"peak VRAM: {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")
```

Compare peak VRAM against the Compute requirements table in `SKILL.md`
(~16 GB LIBERO, ~18 GB RoboCasa). A large gap usually means a different
checkpoint precision or batch shape than the reference setup.

## Kernel-level traces

For kernel-level bottlenecks, wrap the eval process in NVIDIA Nsight Systems:

```bash
nsys profile -o cosmos_policy_libero_trace \
  python -m cosmos_policy.experiments.robot.libero.run_libero_eval ...  # eval flags
```

Open the `.nsys-rep` in the Nsight UI to separate render (MuJoCo/EGL) time from
policy GPU time. On headless nodes, keep rendering on the same device as the
policy to avoid cross-device copies that distort the trace.
