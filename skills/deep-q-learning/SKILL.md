---
name: deep-q-learning
version: 0.1.0
description: Deep Q-Network (DQN) — value-based deep RL for environments with discrete action spaces, using `stable-baselines3`. Use when the state space is continuous or high-dimensional (price tensors, order-book snapshots, indicator vectors) but the action space is small and discrete (e.g., {flat, long, short} or {sell, hold, buy}). This skill is the DQN-specific deep dive; for general SB3 use (algorithm selection, callbacks, vectorized envs, custom envs), see the existing `stable-baselines3` skill in `k-dense-scientific-agent-skills/`. Do not use for continuous actions (→ SAC/TD3) or extremely sparse rewards (→ HER); for algorithm selection matrix, see `stable-baselines3` skill.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: MIT
metadata:
    skill-author: HyperFrequency
---

# Deep Q-Learning (DQN) with stable-baselines3

## When to use

DQN is the right choice when:

- The action space is discrete and small (≤ ~20 actions). For continuous actions use SAC/TD3/DDPG.
- The state space is continuous or large (e.g., a window of returns, a feature vector, an image-like grid).
- You want an off-policy algorithm — DQN reuses experience via a replay buffer, so it is sample-efficient compared to on-policy PG methods.
- You can tolerate the sensitivity to hyperparameters that DQN is known for (target update frequency, exploration schedule, replay buffer size).

Do not reach for DQN when:

- Actions are continuous → SAC/TD3.
- Reward is extremely sparse and you have a goal representation → HER + SAC.
- You need to learn a stochastic policy (e.g., for partial observability) → PPO.

For the broader algorithm-selection table and SB3 framework conventions, defer to the existing `stable-baselines3` skill in `k-dense-scientific-agent-skills/`. This skill assumes you already chose DQN and want the DQN-specific knobs.

## Install / setup

```bash
uv pip install "stable-baselines3[extra]" gymnasium
```

`[extra]` pulls in TensorBoard, OpenCV (for image envs), and progress-bar deps. Optional but recommended.

GPU is helpful for image observations; for low-dimensional feature vectors, `device="cpu"` is often faster due to CPU↔GPU transfer overhead.

## Minimal example

```python
import gymnasium as gym
from stable_baselines3 import DQN
from stable_baselines3.common.evaluation import evaluate_policy

# CartPole-v1 is the canonical smoke-test env for DQN.
# To swap in a custom trading env, see the note below.
env = gym.make("CartPole-v1")

model = DQN(
    "MlpPolicy",
    env,
    learning_rate=1e-4,
    buffer_size=100_000,          # replay buffer capacity (in transitions)
    learning_starts=1_000,        # warmup: collect this many transitions before any gradient step
    batch_size=32,                # minibatch for each gradient step
    tau=1.0,                      # 1.0 = hard target update; <1.0 = Polyak averaging
    gamma=0.99,                   # discount
    train_freq=4,                 # gradient step every N env steps
    gradient_steps=1,             # how many gradient steps per train_freq
    target_update_interval=1_000, # how often (env steps) to copy online → target net
    exploration_fraction=0.1,     # over the first 10% of training, anneal epsilon
    exploration_initial_eps=1.0,
    exploration_final_eps=0.05,
    verbose=1,
)

model.learn(total_timesteps=50_000, progress_bar=True)
model.save("dqn_cartpole")

# Evaluate
mean_reward, std_reward = evaluate_policy(model, model.get_env(), n_eval_episodes=10)
print(f"DQN mean reward: {mean_reward:.2f} +/- {std_reward:.2f}")

# Plugging in a custom trading env:
#   class TradingEnv(gymnasium.Env):
#       def __init__(self, ...):
#           self.action_space = gym.spaces.Discrete(3)       # {sell, hold, buy}
#           self.observation_space = gym.spaces.Box(...)     # feature vector
#       def reset(self, seed=None, options=None): ...
#       def step(self, action): ...                          # -> obs, reward, terminated, truncated, info
# Then: env = TradingEnv(...); model = DQN("MlpPolicy", env, ...)
# Always run stable_baselines3.common.env_checker.check_env(env) first.
```

## Key API surface

`DQN(policy, env, **kwargs)` — relevant kwargs you will actually tune:

| kwarg | what it does | when to change it |
|---|---|---|
| `policy` | `"MlpPolicy"` for vectors, `"CnnPolicy"` for images, `"MultiInputPolicy"` for dict obs | match your obs space |
| `learning_rate` | Adam LR for the online Q-net | 1e-4 default; lower (5e-5) if Q-values explode |
| `buffer_size` | Replay buffer capacity | 50k-1M; trade off RAM vs diversity |
| `learning_starts` | Warm-up steps before training | ≥ batch_size; larger for noisy envs |
| `train_freq` | Env steps between gradient updates | 4 (default) or `(1, "step")`/`(1, "episode")` tuples |
| `target_update_interval` | Env steps between hard target-net copies | 500-10k; larger = more stable, slower to react |
| `tau` | Polyak factor for soft target updates | 1.0 = hard copy (canonical DQN); 0.005 if you switch to soft |
| `exploration_fraction` / `_final_eps` | ε-greedy schedule | anneal over first 10-30% of training |
| `gamma` | Discount | 0.99 default; 0.999 for very long horizons |

**Two architectural pieces to understand:**

1. **Experience replay.** DQN does not learn from the trajectory it just walked; it samples a random minibatch from a circular buffer of past transitions. This breaks temporal correlation in the training signal and lets one transition contribute to many gradient steps. Buffer size is a hyperparameter — too small and you forget useful states; too large and old transitions from a worse policy distort training.

2. **Target network.** The Bellman target `r + γ · max_a' Q_target(s', a')` is computed with a *frozen* copy of the Q-network (`target_update_interval` steps stale). Without this, the target moves with the network you are training and the regression diverges. `tau=1.0` does a hard copy every `target_update_interval` steps (canonical DQN); `tau<1.0` does Polyak averaging every step.

**Inspection:**

```python
model.q_net          # online Q-network
model.q_net_target   # frozen target Q-network
model.replay_buffer  # current buffer (not saved with the model by default)
```

## DQN deep-dive: the two stabilizing tricks

DQN is built on top of vanilla Q-learning with neural function approximation. Two issues arise when you naively swap `Q[s, a]` for `q_net(s)[a]`:

1. **Correlated samples.** Successive transitions in an episode are highly correlated; SGD assumes iid samples. Solution: a replay buffer that mixes recent and old transitions, broken into random minibatches.

2. **Moving target.** The Bellman target `r + γ · max_a' Q(s', a'; θ)` is computed with the same network θ that you are updating, so the regression target moves with every gradient step — a recipe for divergence. Solution: a target network θ⁻ that is a frozen copy of θ, updated every `target_update_interval` steps. The Bellman target uses θ⁻; only θ takes gradient steps.

These are the only architectural differences between vanilla Q-learning and DQN. Everything else (Double DQN, Dueling DQN, Prioritized Experience Replay, Rainbow) is a variance- or bias-reduction add-on. SB3's `DQN` is plain DQN; for Double DQN, use `sb3-contrib`'s `QRDQN` or implement the change manually.

## Workflow patterns

**Custom trading env checklist before training.**

```python
from stable_baselines3.common.env_checker import check_env
check_env(env)   # raises if obs / action spaces are malformed
```

Common failures: action space is `Box` instead of `Discrete`; observation contains NaN at episode start; reward is a list instead of a float; the env returns the old 4-tuple instead of the gymnasium 5-tuple `(obs, reward, terminated, truncated, info)`.

**Monitoring.** Pipe TensorBoard with `tensorboard_log="./tb/"` and watch:

- `rollout/ep_rew_mean` — should rise monotonically (with noise).
- `train/loss` — should decrease then plateau; sustained increase = instability.
- `rollout/exploration_rate` — should follow your epsilon schedule.
- `train/n_updates` — sanity check that gradient steps are actually happening.

**Eval cadence.** Use `EvalCallback` with `eval_freq=5000` and `n_eval_episodes=10`. Save the best model separately from the latest model — DQN can regress after hitting a peak.

## Common pitfalls

1. **Replay buffer too small.** With `buffer_size=10_000` and `learning_starts=1_000`, the buffer cycles roughly every 9k env steps — the agent effectively forgets early experience. For real trading envs default to 100k-1M.

2. **Target update too frequent.** Setting `target_update_interval=100` (or `tau` close to 1) makes the target nearly identical to the online net, defeating its stabilizing purpose. Q-values oscillate and the loss curve looks chaotic. Use ≥ 500 for canonical DQN, and watch `train/loss` for signs of instability.

3. **Exploration anneals too fast.** `exploration_fraction=0.05` over a 50k-step run means the agent stops exploring after only 2.5k steps, well before it has seen the state space. Default to 0.1-0.3 of `total_timesteps`, and keep `exploration_final_eps ≥ 0.02` to maintain off-policy coverage.

4. **DQN on a continuous-action problem.** SB3 raises `AssertionError` if the action space is not `Discrete`. The fix is to either bucket your continuous action (lossy) or switch algorithm — see the `stable-baselines3` skill for SAC/TD3 selection.

5. **Reward scale matters.** Q-values are unbounded; if your per-step reward is in the millions (raw dollar PnL), the Q-network struggles. Normalize rewards or use `VecNormalize` from `stable_baselines3.common.vec_env`.

6. **The replay buffer is not saved with `model.save()`.** This is intentional (it can be huge), but it means you cannot resume training from exactly where you left off without `save_replay_buffer()` and `load_replay_buffer()` calls.

## DQN vs SB3 alternatives — quick triage

| If your problem has... | Use |
|---|---|
| Discrete actions, low-dim obs | **DQN** (this skill) |
| Discrete actions, image obs | DQN with `"CnnPolicy"` |
| Continuous actions, deterministic optimum | TD3 (see `stable-baselines3` skill) |
| Continuous actions, want stochastic policy | SAC (see `stable-baselines3` skill) |
| Need policy directly (PG / on-policy) | PPO (see `policy-gradients` skill) |
| Multi-discrete or mixed | PPO (DQN does not support `MultiDiscrete` natively) |

For the algorithm-vs-problem matrix in full detail (action space, observation space, sample-efficiency notes), defer to the existing `stable-baselines3` skill in `k-dense-scientific-agent-skills/` — that skill is the canonical home for cross-algorithm comparison; this one focuses on the DQN-specific hyperparameter surface.

## References

### Primary library
- [DLR-RM/stable-baselines3](https://github.com/DLR-RM/stable-baselines3) — upstream repo (issues, releases, the canonical PyTorch DQN/PPO/SAC implementations)
- [SB3 docs](https://stable-baselines3.readthedocs.io/en/master/) — pinned channel (`master` ≈ current release)
- [Getting started](https://stable-baselines3.readthedocs.io/en/master/guide/quickstart.html) — minimal `model = DQN(...).learn(...)` pattern
- [`examples/` in the repo](https://github.com/DLR-RM/stable-baselines3/tree/master/docs/guide) — RL Zoo + custom-env walkthroughs
- [Changelog](https://stable-baselines3.readthedocs.io/en/master/misc/changelog.html) — DQN API was last revised in the `2.x` series; pin before upgrades

### Deep-dive docs (specific pages worth bookmarking)
- [DQN reference page](https://stable-baselines3.readthedocs.io/en/master/modules/dqn.html) — the parameter table (`buffer_size`, `learning_starts`, `target_update_interval`, `exploration_*`); the API contract for this skill
- [Custom policies](https://stable-baselines3.readthedocs.io/en/master/guide/custom_policy.html) — `MlpPolicy` / `CnnPolicy` / custom feature extractors; needed when your obs space isn't a flat Box
- [Vectorised environments](https://stable-baselines3.readthedocs.io/en/master/guide/vec_envs.html) — `VecEnv`, `SubprocVecEnv`, `VecNormalize`; obs normalisation is non-optional for quant
- [Custom callbacks](https://stable-baselines3.readthedocs.io/en/master/guide/callbacks.html) — `EvalCallback`, `CheckpointCallback`, custom logging; how to capture rolling-Sharpe during training
- [SB3 Contrib (`sb3-contrib`)](https://sb3-contrib.readthedocs.io/) — `QRDQN` (Quantile-Regression DQN) and `MaskablePPO` for action masking — both relevant for risk-aware trading
- [RL Baselines3 Zoo](https://github.com/DLR-RM/rl-baselines3-zoo) — pre-tuned hyperparams + training scripts; use this before hand-tuning DQN from scratch
- [Gymnasium custom environment API](https://gymnasium.farama.org/tutorials/gymnasium_basics/environment_creation/) — how to wrap a market simulator as an `Env` SB3 can consume

### Adjacent / alternative libraries
- [`gymnasium`](https://github.com/Farama-Foundation/Gymnasium) — modern fork of OpenAI Gym; SB3's env contract
- [`finrl`](https://github.com/AI4Finance-Foundation/FinRL) — trading-specific env library; ships pre-built `StockTradingEnv`, `PortfolioOptimizationEnv`
- [`tianshou`](https://github.com/thu-ml/tianshou) — alternative PyTorch RL framework; more flexible than SB3 for research, less batteries-included
- [`ray[rllib]`](https://docs.ray.io/en/latest/rllib/index.html) — distributed RL when single-process training stops being enough
- [`cleanrl`](https://github.com/vwxyzjn/cleanrl) — single-file reference implementations (DQN, PPO, SAC) — the right reference when you need to *understand* SB3's choices
- For tabular case: see [`q-learning`](../q-learning/SKILL.md) skill

### Academic papers
- Mnih, V. et al. (2015). "Human-level control through deep reinforcement learning." *Nature* 518, 529–533. [doi:10.1038/nature14236](https://doi.org/10.1038/nature14236) — the original DQN paper; defines experience replay, target network, the Atari benchmark
- Mnih, V. et al. (2013). "Playing Atari with Deep Reinforcement Learning." *NIPS Deep Learning Workshop*. [arXiv:1312.5602](https://arxiv.org/abs/1312.5602) — the workshop precursor to the Nature paper
- van Hasselt, H., Guez, A., Silver, D. (2016). "Deep Reinforcement Learning with Double Q-learning." *AAAI 2016*. [arXiv:1509.06461](https://arxiv.org/abs/1509.06461) — Double DQN (the overestimation-bias fix SB3 uses by default)
- Wang, Z. et al. (2016). "Dueling Network Architectures for Deep Reinforcement Learning." *ICML 2016*. [arXiv:1511.06581](https://arxiv.org/abs/1511.06581) — Dueling DQN (value + advantage decomposition)
- Schaul, T., Quan, J., Antonoglou, I., Silver, D. (2016). "Prioritized Experience Replay." *ICLR 2016*. [arXiv:1511.05952](https://arxiv.org/abs/1511.05952) — the replay-buffer prioritisation `sb3-contrib` ships
- Dabney, W., Rowland, M., Bellemare, M. G., Munos, R. (2018). "Distributional Reinforcement Learning with Quantile Regression." *AAAI 2018*. [arXiv:1710.10044](https://arxiv.org/abs/1710.10044) — QR-DQN, the quantile variant in `sb3-contrib`
- Hessel, M. et al. (2018). "Rainbow: Combining Improvements in Deep Reinforcement Learning." *AAAI 2018*. [arXiv:1710.02298](https://arxiv.org/abs/1710.02298) — the six-improvements bundle that defines the modern DQN baseline

### Tutorials & write-ups
- [Spinning Up in Deep RL — DQN page](https://spinningup.openai.com/en/latest/algorithms/dqn.html) — OpenAI's pedagogical reference (Spinning Up didn't ship DQN code but the page is the cleanest explanation outside of cleanrl)
- [Lilian Weng — "A (Long) Peek into Reinforcement Learning"](https://lilianweng.github.io/posts/2018-02-19-rl-overview/) — the modern roadmap from TD/Q to DQN/Rainbow
- [Costa Huang — `cleanrl/dqn_atari.py`](https://github.com/vwxyzjn/cleanrl/blob/master/cleanrl/dqn_atari.py) — single-file DQN reference; the cleanest implementation outside research papers

### Standard environments / benchmarks
- `CartPole-v1` — [gymnasium](https://gymnasium.farama.org/environments/classic_control/cart_pole/) — discrete-action toy; the universal sanity-check that DQN trains
- `LunarLander-v3` — [gymnasium](https://gymnasium.farama.org/environments/box2d/lunar_lander/) — slightly harder; the SB3 docs use this for end-to-end examples
- `ALE/Pong-v5` and friends — [Arcade Learning Environment](https://github.com/Farama-Foundation/Arcade-Learning-Environment) — the original DQN benchmark; you'll need `CnnPolicy` + frame-stacking wrappers

### Last cross-checked
2026-05-20 — via Context7 `/dlr-rm/stable-baselines3` (309 snippets) + `/stable-baselines-team/stable-baselines3-contrib` + upstream docs.
