---
name: policy-gradients
description: Policy-gradient methods — direct optimization of a parameterized stochastic policy via the score-function (REINFORCE) estimator and its variance-reduced descendants (A2C, PPO). Includes a hand-rolled REINFORCE for pedagogy and a 10-line PPO via `stable-baselines3` for production. Use when actions are continuous, when you need a stochastic policy (partial observability, exploration), or when you want lower-variance, more stable training than vanilla DQN at the cost of sample efficiency. For general SB3 use (callbacks, vectorized envs, custom envs), see the existing `stable-baselines3` skill in `k-dense-scientific-agent-skills/`.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: MIT
metadata:
    skill-author: HyperFrequency
---

# Policy Gradient Methods

## When to use

Reach for policy gradients (PG) when:

- The action space is continuous (position sizing in [-1, 1], not just {sell, hold, buy}). Value-based methods like DQN cannot represent a continuous argmax.
- You need a stochastic policy — for exploration, for partial observability where the optimal policy is genuinely randomized, or for multi-agent settings.
- Stability matters more than sample efficiency. On-policy PG methods (PPO, A2C) are generally more stable than DQN but require more environment interaction.

The math, in one line: for trajectory τ and reward-to-go R_t,

    ∇_θ J(θ) = E_τ [ Σ_t ∇_θ log π_θ(a_t | s_t) · R_t ]

This is the **score-function estimator** (a.k.a. REINFORCE / log-derivative trick). It is unbiased but very high variance — every modern PG algorithm (A2C, PPO, TRPO, SAC) is fundamentally a variance-reduction or trust-region trick on top of this estimator.

For the broader algorithm-selection table and SB3 framework conventions, defer to the existing `stable-baselines3` skill in `k-dense-scientific-agent-skills/`. This skill covers the PG family specifically.

## Install / setup

```bash
uv pip install torch gymnasium                    # for the hand-rolled REINFORCE
uv pip install "stable-baselines3[extra]"         # for PPO / A2C
```

## Minimal example

### 1. Hand-rolled REINFORCE on `CartPole-v1`

This is a teaching reference, not a production trainer — but it converges on CartPole in a few thousand episodes and shows the score-function estimator with nothing hidden.

```python
import torch
import torch.nn as nn
import gymnasium as gym

env = gym.make("CartPole-v1")
obs_dim = env.observation_space.shape[0]
n_actions = env.action_space.n

policy = nn.Sequential(nn.Linear(obs_dim, 64), nn.ReLU(), nn.Linear(64, n_actions))
opt = torch.optim.Adam(policy.parameters(), lr=1e-2)
gamma = 0.99

for episode in range(500):
    obs, _ = env.reset()
    log_probs, rewards = [], []
    done = False
    while not done:
        logits = policy(torch.as_tensor(obs, dtype=torch.float32))
        dist = torch.distributions.Categorical(logits=logits)
        action = dist.sample()
        log_probs.append(dist.log_prob(action))
        obs, r, term, trunc, _ = env.step(action.item())
        rewards.append(r)
        done = term or trunc
    # Reward-to-go (discounted return from each step onward)
    R, returns = 0.0, []
    for r in reversed(rewards):
        R = r + gamma * R
        returns.insert(0, R)
    returns = torch.tensor(returns)
    # CRITICAL: normalize returns for variance reduction. Without this, REINFORCE crawls.
    returns = (returns - returns.mean()) / (returns.std() + 1e-8)
    loss = -(torch.stack(log_probs) * returns).sum()  # negate -> gradient ascent on J
    opt.zero_grad(); loss.backward(); opt.step()
```

### 2. Production PPO via `stable-baselines3` (10 lines)

When you actually want to train something, do this:

```python
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env

# n_envs=4 collects rollouts in parallel — PPO is on-policy so throughput matters
vec_env = make_vec_env("CartPole-v1", n_envs=4)
model = PPO("MlpPolicy", vec_env, learning_rate=3e-4, n_steps=2048, batch_size=64,
            n_epochs=10, gamma=0.99, gae_lambda=0.95, clip_range=0.2, verbose=1)
model.learn(total_timesteps=25_000, progress_bar=True)
model.save("ppo_cartpole")
```

A2C is the same call with `from stable_baselines3 import A2C` and tighter `n_steps` (5 is default).

## Key API surface

### Conceptual surface (REINFORCE → modern PG)

| Component | REINFORCE | A2C | PPO |
|---|---|---|---|
| Return estimate | Monte-Carlo (full rollout) | n-step bootstrapped | GAE (λ-weighted) |
| Baseline | none (or running mean) | learned value V(s) | learned value V(s) |
| Policy update | one gradient step per traj | one gradient step per rollout | multiple epochs with clip |
| On / off policy | on | on | on |
| Variance | very high | medium | medium (clip stabilizes) |

The progression is variance reduction: REINFORCE → REINFORCE-with-baseline → actor-critic (A2C) → trust-region (TRPO) → clipped surrogate (PPO).

### `stable_baselines3.PPO` kwargs you will actually tune

| kwarg | meaning | typical |
|---|---|---|
| `n_steps` | rollout length per env before each update | 128-2048 |
| `batch_size` | minibatch size for the SGD epochs | 32-256, must divide `n_envs * n_steps` |
| `n_epochs` | passes over the rollout per update | 3-20 |
| `clip_range` | PPO's ratio clip ε | 0.1-0.3 |
| `gae_lambda` | bias-variance knob for advantage est. | 0.9-0.99 |
| `ent_coef` | entropy bonus | 0.0-0.01 (raise for exploration) |
| `vf_coef` | value-loss weight | 0.5 default |

### `stable_baselines3.A2C` differences

A2C is essentially PPO with `n_epochs=1` and no clipping. SB3's A2C defaults: `n_steps=5`, `learning_rate=7e-4`, runs best on CPU with `MlpPolicy` (set `device="cpu"`).

## The score-function estimator in 60 seconds

The key insight: although you cannot differentiate through `argmax` or through `env.step`, you can differentiate through the policy's *probability* of taking an action — and reweight that gradient by the resulting return. Formally,

    ∇_θ E_τ[R(τ)] = E_τ[ R(τ) · ∇_θ log π_θ(τ) ]
                  = E_τ[ Σ_t ∇_θ log π_θ(a_t | s_t) · R_t ]

where the last equality drops terms that do not depend on θ (the env transition probabilities). This is unbiased — the estimator's mean equals the true gradient — but the variance is so high that on anything non-trivial it would take an astronomical number of samples to converge. Every modern PG algorithm fights variance:

- **Baseline subtraction.** Subtract a state-dependent baseline `b(s_t)` from `R_t`. This is unbiased (since the baseline is independent of the action) and dramatically reduces variance when `b(s) ≈ V(s)`.
- **Advantage actor-critic (A2C).** Learn V(s) jointly; use `A(s, a) = R - V(s)` as the multiplier instead of raw return.
- **GAE.** Generalized Advantage Estimation: an exponentially-weighted blend of n-step advantages parameterized by `λ`. `λ=1` recovers Monte-Carlo, `λ=0` recovers TD(0).
- **Trust region (TRPO) / clipped surrogate (PPO).** Limit how far the new policy can move from the old one per update, so a single high-variance step cannot wreck the policy.

If you understand these four ideas, you understand the entire on-policy PG family.

## Workflow patterns

**PPO hyperparameter starting points by problem class.**

| Problem | learning_rate | n_steps | batch_size | n_epochs | clip_range | ent_coef |
|---|---|---|---|---|---|---|
| CartPole / toy | 3e-4 | 2048 | 64 | 10 | 0.2 | 0.0 |
| Continuous control (MuJoCo-scale) | 3e-4 | 2048 | 64 | 10 | 0.2 | 0.0 |
| Sparse reward / hard exploration | 3e-4 | 2048 | 64 | 10 | 0.2 | 0.005-0.01 |
| Custom trading env | 1e-4 to 3e-4 | 256-1024 | 64 | 4-10 | 0.1-0.2 | 0.001-0.01 |

Use the RL Zoo (https://github.com/DLR-RM/rl-baselines3-zoo) as a source for tuned hyperparameters on standard envs.

**Tensorboard signals to watch (PPO):**

- `train/approx_kl` — KL between old and new policy. If this consistently exceeds ~0.02, your `clip_range` is letting too-large updates through; lower it or lower `n_epochs`.
- `train/clip_fraction` — fraction of samples that hit the clip. 0.1-0.3 is healthy; 0 means no clipping is firing (clip is too loose); >0.5 means too tight.
- `train/entropy_loss` — should decrease slowly. Sudden collapse to near-zero = entropy collapse, raise `ent_coef`.
- `train/explained_variance` — quality of the value function. Should rise from 0 toward 1.

**On-policy vs off-policy decision rule.** If env interaction is cheap (sim < 1ms/step), PPO is great. If env interaction is expensive (slow sim, market replay, or real trading), prefer off-policy (SAC/DQN) so you can reuse data via a replay buffer.

## Common pitfalls

1. **Forgetting to normalize returns / advantages.** Vanilla REINFORCE without return normalization has variance so high it often fails to learn at all on anything beyond a 2-state toy. Always center and scale returns (or advantages) within each batch — the example above shows the one-line fix.

2. **Catastrophic policy collapse.** Vanilla REINFORCE can take an over-aggressive gradient step that destroys the policy in one update; the next rollout is then near-uniform random and never recovers. This is the bug PPO/TRPO were invented to fix — use the clip mechanism (PPO) or a KL constraint (TRPO) for any non-toy env.

3. **Hyperparameter coupling in PPO.** `n_envs * n_steps` must be divisible by `batch_size`, otherwise SB3 silently drops samples. Also `n_steps * n_envs` is the effective rollout buffer per update — too small (e.g., 4 × 32 = 128) gives a noisy advantage estimate.

4. **On-policy means you cannot reuse old data.** Switching to a new policy invalidates the replay buffer; this is why PPO uses *rollout* buffers, not replay buffers. If sample efficiency dominates (e.g., expensive sim or real-money trading), prefer SAC / DQN — see the `stable-baselines3` skill for the full selection table.

5. **Entropy collapse.** As training proceeds, the policy gets sharper and explores less. If you see early plateaus and the entropy in `train/entropy_loss` collapses to near zero, raise `ent_coef` (0.005-0.01) to add an entropy bonus that keeps the policy stochastic.

## References

### Primary library
- [DLR-RM/stable-baselines3 on GitHub](https://github.com/DLR-RM/stable-baselines3) — upstream repo, issues, releases
- [Stable Baselines3 documentation](https://stable-baselines3.readthedocs.io/en/master/) — pinned to master as of cross-check
- [SB3 PPO module docs](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html) — full `PPO(...)` kwargs reference
- [SB3 A2C module docs](https://stable-baselines3.readthedocs.io/en/master/modules/a2c.html) — A2C specifics; `n_steps=5`, `device="cpu"` for MlpPolicy
- [SB3 Contrib (TRPO, RecurrentPPO, MaskablePPO)](https://github.com/Stable-Baselines-Team/stable-baselines3-contrib) — TRPO and recurrent / mask variants live here, not in core
- [RL Baselines3 Zoo](https://github.com/DLR-RM/rl-baselines3-zoo) — pre-tuned hyperparameters for every env in SB3; copy as starting points
- [gymnasium on GitHub](https://github.com/Farama-Foundation/Gymnasium) — the env interface SB3 expects (Gym's maintained successor)

### Deep-dive docs (specific pages worth bookmarking)
- [SB3 PPO docs page](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html) — kwargs table, recommended hyperparameters by domain, TensorBoard signal interpretation
- [SB3 A2C docs page](https://stable-baselines3.readthedocs.io/en/master/modules/a2c.html) — defaults, when to use SubprocVecEnv, CPU-vs-GPU guidance
- [SB3 Custom Policy Networks](https://stable-baselines3.readthedocs.io/en/master/guide/custom_policy.html) — `policy_kwargs=dict(net_arch=...)` patterns
- [SB3 Logging / TensorBoard](https://stable-baselines3.readthedocs.io/en/master/guide/tensorboard.html) — `approx_kl`, `clip_fraction`, `explained_variance`, `entropy_loss` definitions
- [SB3 Callbacks](https://stable-baselines3.readthedocs.io/en/master/guide/callbacks.html) — `EvalCallback`, `CheckpointCallback`, `StopTrainingOnRewardThreshold`
- [SB3 Vectorized envs](https://stable-baselines3.readthedocs.io/en/master/guide/vec_envs.html) — `DummyVecEnv` vs `SubprocVecEnv`; PPO needs vectorized envs for throughput
- [SB3-Contrib TRPO docs](https://sb3-contrib.readthedocs.io/en/master/modules/trpo.html) — when you actually want trust-region (rare in practice)
- [SB3-Contrib RecurrentPPO docs](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_recurrent.html) — LSTM/GRU policies; required for partial observability

### Adjacent / alternative libraries
- [Ray RLlib](https://github.com/ray-project/ray) — distributed RL; PPO/A2C/IMPALA at scale, multi-agent native
- [CleanRL](https://github.com/vwxyzjn/cleanrl) — single-file reference implementations; the cleanest pedagogical PPO/A2C in the wild
- [TorchRL](https://github.com/pytorch/rl) — PyTorch-native RL; lower-level than SB3, gives more control over policy + loss
- [Tianshou](https://github.com/thu-ml/tianshou) — modular PyTorch RL; nicer for custom training loops than SB3
- [JAX-based: Mava](https://github.com/instadeepai/Mava), [Stoix](https://github.com/EdanToledo/Stoix) — when JAX speed beats PyTorch ergonomics
- [PufferLib](https://github.com/PufferAI/PufferLib) — env wrappers that make SB3 / CleanRL much faster on many envs

### Academic papers
- Williams, R. J. (1992). "Simple Statistical Gradient-Following Algorithms for Connectionist Reinforcement Learning." *Machine Learning* 8, 229-256. [DOI: 10.1007/BF00992696](https://doi.org/10.1007/BF00992696) — the REINFORCE paper.
- Sutton, R. S., McAllester, D. A., Singh, S. P., & Mansour, Y. (2000). "Policy Gradient Methods for Reinforcement Learning with Function Approximation." *NIPS 1999*. [Proceedings PDF](https://proceedings.neurips.cc/paper_files/paper/1999/file/464d828b85b0bed98e80ade0a5c43b0f-Paper.pdf) — the policy-gradient theorem; the convergence proof for function-approximated PG.
- Konda, V. R., & Tsitsiklis, J. N. (2000). "Actor-Critic Algorithms." *NIPS 1999*. [Proceedings PDF](https://proceedings.neurips.cc/paper/1999/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html) — the formal actor-critic convergence result; the basis for A2C.
- Mnih, V., Badia, A. P., Mirza, M., Graves, A., Lillicrap, T., Harley, T., Silver, D., & Kavukcuoglu, K. (2016). "Asynchronous Methods for Deep Reinforcement Learning." *ICML 2016*, 1928-1937. [arXiv:1602.01783](https://arxiv.org/abs/1602.01783) — A3C / A2C; the deep-RL actor-critic baseline.
- Schulman, J., Levine, S., Abbeel, P., Jordan, M., & Moritz, P. (2015). "Trust Region Policy Optimization." *ICML 2015*. [arXiv:1502.05477](https://arxiv.org/abs/1502.05477) — TRPO; the trust-region predecessor to PPO.
- Schulman, J., Moritz, P., Levine, S., Jordan, M., & Abbeel, P. (2016). "High-Dimensional Continuous Control Using Generalized Advantage Estimation." *ICLR 2016*. [arXiv:1506.02438](https://arxiv.org/abs/1506.02438) — GAE; the bias-variance advantage estimator PPO uses.
- Schulman, J., Wolski, F., Dhariwal, P., Radford, A., & Klimov, O. (2017). "Proximal Policy Optimization Algorithms." [arXiv:1707.06347](https://arxiv.org/abs/1707.06347) — PPO; the clipped surrogate objective.
- Sutton, R. S., & Barto, A. G. (2018). *Reinforcement Learning: An Introduction* (2nd ed.). MIT Press. Ch. 13. [Free PDF](http://incompleteideas.net/book/the-book-2nd.html) — the canonical RL textbook; Ch. 13 covers policy gradients.
- Andrychowicz, M., Raichuk, A., Stańczyk, P., Orsini, M., Girgin, S., Marinier, R., Hussenot, L., Geist, M., Pietquin, O., Michalski, M., Gelly, S., & Bachem, O. (2020). "What Matters In On-Policy Reinforcement Learning? A Large-Scale Empirical Study." [arXiv:2006.05990](https://arxiv.org/abs/2006.05990) — empirical study of which PPO knobs actually matter; mandatory reading before tuning.
- Engstrom, L., Ilyas, A., Santurkar, S., Tsipras, D., Janoos, F., Rudolph, L., & Madry, A. (2020). "Implementation Matters in Deep RL: A Case Study on PPO and TRPO." *ICLR 2020*. [arXiv:2005.12729](https://arxiv.org/abs/2005.12729) — proves most of PPO's edge over TRPO comes from "code-level" optimizations, not the clipped surrogate; the implementation-details Bible.

### Tutorials & write-ups
- [SB3 tutorial notebooks](https://github.com/araffin/rl-tutorial-jnrr19) — official RL tutorial by SB3 maintainer; the cleanest "go from zero to PPO" walkthrough
- [Spinning Up in Deep RL (OpenAI)](https://spinningup.openai.com/en/latest/algorithms/ppo.html) — the canonical pedagogical reference; PPO derivation + minimal implementation
- [The 37 Implementation Details of PPO (Costa Huang)](https://iclr-blog-track.github.io/2022/03/25/ppo-implementation-details/) — empirical catalogue of every PPO trick that matters
- [CleanRL PPO walkthrough](https://github.com/vwxyzjn/cleanrl/blob/master/cleanrl/ppo.py) — single-file PPO with comments; the easiest reference implementation to read

### Standard datasets / benchmarks
- CartPole-v1 / MountainCar-v0 — Gymnasium classics; train in <1 minute, the "definitely works" sanity check
- Atari (Arcade Learning Environment) — the 57-game DRL benchmark; PPO converges on most in ~10M steps
- MuJoCo (HalfCheetah, Hopper, Walker2d, Humanoid) — continuous-control benchmark suite; the SB3 zoo has tuned hyperparameters for each
- DeepMind Control Suite — modern alternative to MuJoCo with same task spec
- Procgen — Cobbe et al. (2020) procedurally-generated suite testing generalization
- ProcGym / NeuralMMO / Gym Retro — broader env collections for harder generalization tests

### Last cross-checked
2026-05-20 — via Context7 `/dlr-rm/stable-baselines3` (309 snippets, High, benchmark 78.91) + WebSearch verification of all paper arXiv IDs / NeurIPS URLs.
