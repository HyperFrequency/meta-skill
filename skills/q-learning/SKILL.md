---
name: q-learning
version: 0.1.0
description: Tabular Q-learning — the canonical off-policy temporal-difference control algorithm. Standalone NumPy implementation, no library required. Use when the state and action spaces are both small and discrete (e.g., 3-position trading {flat, long, short} over a discretized signal bucket), when you want a transparent baseline before reaching for DQN, or when you need a pedagogical reference for the Bellman update. For continuous or high-cardinality state spaces, switch to the `deep-q-learning` skill.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: MIT
metadata:
    skill-author: HyperFrequency
---

# Tabular Q-Learning

## When to use

Reach for tabular Q-learning when **both** the state space and action space are small, discrete, and enumerable:

- Toy trading envs with bucketed indicators (e.g., RSI quintile x position x trend regime, ~50-500 states)
- Gridworld-style decision problems
- Sanity-checking a reward function before scaling to DQN
- Teaching / writing exposition where you need to show the Bellman update transparently

Skip this skill — go to `deep-q-learning` — when state is continuous (prices, returns), high-dimensional (order book), or when the table would exceed ~10^5 entries. Tabular Q-learning has no generalization: it learns each (s, a) cell independently.

## Install / setup

No library required beyond NumPy. Optional Gymnasium for the env interface.

```bash
uv pip install numpy
uv pip install gymnasium   # optional, only for the env stub
```

## Minimal example

A 3-state toy trading env. State ∈ {0: cash, 1: long, 2: short}. Action ∈ {0: hold, 1: flip to long, 2: flip to short}. Reward is the (sign-adjusted) next-bar return of a synthetic mean-reverting series.

```python
import numpy as np

rng = np.random.default_rng(0)
N_STATES, N_ACTIONS = 3, 3
Q = np.zeros((N_STATES, N_ACTIONS))

# Hyperparameters
alpha = 0.1          # learning rate
gamma = 0.95         # discount
eps_start, eps_end = 1.0, 0.05
eps_decay = 0.995    # geometric decay per episode
n_episodes, n_steps = 2_000, 200

# Synthetic price series — AR(1) mean reversion; returns flip sign each bar
def make_returns(n):
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = -0.4 * x[t - 1] + 0.01 * rng.standard_normal()
    return x

def step(state, action, ret):
    # Action determines the *next* position; reward = position * ret - tiny cost on flip
    next_state = action
    cost = 0.0005 if action != state else 0.0
    pos_sign = {0: 0.0, 1: 1.0, 2: -1.0}[next_state]
    reward = pos_sign * ret - cost
    return next_state, reward

eps = eps_start
for ep in range(n_episodes):
    rets = make_returns(n_steps)
    s = 0
    for t in range(n_steps - 1):
        # Epsilon-greedy action selection
        if rng.random() < eps:
            a = rng.integers(N_ACTIONS)
        else:
            a = int(np.argmax(Q[s]))
        s_next, r = step(s, a, rets[t + 1])
        # Bellman update: Q(s,a) <- Q(s,a) + alpha * (r + gamma * max_a' Q(s',a') - Q(s,a))
        td_target = r + gamma * np.max(Q[s_next])
        Q[s, a] += alpha * (td_target - Q[s, a])
        s = s_next
    eps = max(eps_end, eps * eps_decay)

print("Learned Q-table:\n", Q.round(4))
print("Greedy policy per state:", np.argmax(Q, axis=1).tolist())
```

What to look at in the output:

- After ~2k episodes, `np.argmax(Q, axis=1)` should converge to a stable greedy policy (the actual policy depends on the seed and the mean-reversion strength — this is illustrative, not a production strategy).
- `Q.max() - Q.min()` should be on the order of the expected per-step reward times `1/(1-gamma)`; if it explodes, lower `alpha` or `gamma`.

## Key API surface

There is no library here — the surface is the algorithm itself. Memorize this:

| Symbol | Meaning | Typical value |
|---|---|---|
| `Q[s, a]` | Action-value estimate | initialized to zeros (or small random) |
| `alpha` | Learning rate | 0.01-0.5; smaller for stochastic envs |
| `gamma` | Discount factor | 0.9-0.99 for finite horizon, ~0.999 for long-horizon |
| `epsilon` | Exploration rate | start at 1.0, decay to 0.01-0.1 |
| `td_target` | r + γ · max_a' Q(s', a') | the bootstrapped target |
| `td_error` | td_target − Q(s, a) | the update signal |

The single update line is the whole algorithm:

```python
Q[s, a] += alpha * (r + gamma * np.max(Q[s_next]) - Q[s, a])
```

For SARSA (on-policy variant), replace `np.max(Q[s_next])` with `Q[s_next, a_next]` where `a_next` is the actually chosen next action.

## Workflow patterns

**Discretizing a trading observation.** A common pattern is to take ~3 continuous indicators (e.g., RSI, log-return z-score, regime tag), bucket each into 3-5 quantiles, and use the cartesian product as the state. Keep the total state count under ~1000 and confirm by counting non-zero rows in `Q` after training that ≥ 50% of states are visited. If coverage is poor, drop a dimension or merge bins.

**Choosing alpha and gamma jointly.** Effective horizon ≈ `1 / (1 - gamma)`. With `gamma=0.99` that's ~100 steps; with `gamma=0.95` it's ~20. Pick gamma to match the actual reward-delay scale in your env. Then pick alpha such that the rolling change in `|Q|` is small but non-zero — start at 0.1 and halve if the table jitters.

**Diagnostic plots.** After training: (1) plot `argmax(Q, axis=1)` per state to inspect the greedy policy; (2) plot `Q.max(axis=1)` to see which states the agent thinks are valuable; (3) plot cumulative episode reward over training to confirm monotone improvement. Lack of monotone improvement is usually an `alpha` or `epsilon` schedule problem, not a Bellman bug.

**Tabular → DQN handoff.** When you outgrow the table, the canonical handoff is: keep the same env, change `Q[s, a]` to `q_net(s)[a]` where `q_net` is a small MLP, add a replay buffer + target network, and switch to the `deep-q-learning` skill. The reward function and env API stay the same.

## Common pitfalls

1. **Learning rate too high → divergence.** With `alpha = 0.5` and noisy rewards, Q-values oscillate and never converge. Default to 0.1 and lower if the table is jittering between episodes.

2. **Epsilon schedule too greedy too fast.** Decaying to `eps_end=0` deterministically locks in whatever the table looks like at the time, which is usually wrong. Keep a floor of 0.01-0.05 even at convergence, or use a longer geometric/linear decay.

3. **State space explosion on discretization.** Naively bucketing N continuous indicators into K bins each yields K^N states — five 10-bin indicators is already 100,000 cells, most of which never get visited. If your table is >90% zeros after training, you have a coverage problem, not a learning rate problem. Drop dimensions or move to function approximation (DQN).

4. **Reward shaping leaks future info.** Using next-bar return as the reward (as in the example) is fine for a pedagogical env but is *not* causally valid in real trading — the agent at time t cannot observe `ret[t+1]` to decide its action. Make sure the reward only depends on quantities knowable at the decision time.

5. **No generalization across similar states.** Tabular Q has zero inductive bias: visiting state 17 teaches the agent nothing about state 18. If your states are naturally similar (e.g., adjacent price buckets), you are leaving sample efficiency on the table — that is exactly the problem DQN solves.

## Convergence checklist

Before declaring training "done", confirm:

- [ ] Average episode reward over the last 100 episodes is stable (rolling std < 10% of rolling mean).
- [ ] The greedy policy `argmax(Q, axis=1)` is unchanged over the last 100 episodes for ≥ 90% of states.
- [ ] At least 80% of visited states have been visited more than ~50 times (check with a `visit_count` table alongside `Q`).
- [ ] Holdout evaluation with `epsilon=0` on a fresh seed gives reward within 1 standard deviation of training-time reward — otherwise the policy is overfit to the training trajectory distribution.

## Q-learning vs SARSA — when to use which

The two tabular TD control algorithms differ in one line:

```python
# Q-learning (off-policy):
td_target = r + gamma * np.max(Q[s_next])       # uses the optimal next action

# SARSA (on-policy):
td_target = r + gamma * Q[s_next, a_next]       # uses the actually-chosen next action
```

| | Q-learning | SARSA |
|---|---|---|
| Learns | optimal Q* even while exploring | Q for the *behavior* policy (epsilon-greedy) |
| Risk preference | aggressive (assumes future actions are optimal) | conservative (accounts for exploration risk) |
| Cliff-walking | walks the edge — gets pushed off by exploration | takes a safer interior path |
| Trading parallel | acts as if no slippage / no exploration in execution | accounts for trading frictions in the policy |

For a real trading env where the deployed policy will still have noise (broker latency, slippage, intentional exploration), SARSA is often the more honest target.

## Reward-shaping notes

A few rules that apply broadly to tabular RL on trading-style envs:

1. **Per-step reward should be small and zero-mean-ish.** Raw dollar PnL of $1000 per bar makes Q-values huge and learning unstable. Use returns, log-returns, or PnL scaled by an ATR-like volatility estimate.
2. **Penalize churn.** Add a small flip cost in the reward when the action changes the position. Without it, the policy will discover that maximum churn captures every up-tick and produces unrealistic backtests.
3. **Avoid sparse terminal-only reward.** "+1 if I'm profitable at end of day, 0 otherwise" gives almost no learning signal; the credit-assignment problem dominates. Dense per-step reward is fine unless you specifically need to evaluate end-of-horizon objectives (Sharpe, max drawdown).
4. **Reward must be Markov in the chosen state.** If the optimal action genuinely depends on history (e.g., last N returns), the state must include that history. Otherwise the env is partially observable, no Q* exists in your state representation, and the table will oscillate.
5. **No look-ahead in reward computation.** Already mentioned in pitfalls — repeated here because it is the single most common subtle bug. Compute reward from quantities knowable at decision time `t`; do not peek at `t+1` data when selecting the action at `t`.
6. **Reward scaling stability.** Multiplying all rewards by a constant rescales Q-values proportionally without changing the optimal policy — useful if Q-values are blowing up numerically.

## References

### Primary library (the algorithm itself)
- This skill implements tabular Q-learning from scratch in ~30 lines of NumPy — there is no upstream package to pin. The reference implementation lives inside the skill body above.
- For the deep variant, see the [`deep-q-learning`](../deep-q-learning/SKILL.md) skill.
- For SB3-based RL, see the existing [`stable-baselines3`](https://stable-baselines3.readthedocs.io/) skill in `k-dense-scientific-agent-skills/`.

### Deep-dive docs (specific pages worth bookmarking)
- [Gymnasium documentation](https://gymnasium.farama.org/) — the standard environment API (`env.reset()`, `env.step()`); the right wrapper to build your custom trading env around
- [Gymnasium custom environment tutorial](https://gymnasium.farama.org/tutorials/gymnasium_basics/environment_creation/) — how to wrap a price series as an `Env` with discrete actions and a reward function
- [Sutton & Barto, *Reinforcement Learning: An Introduction* (2nd ed., free PDF)](http://incompleteideas.net/book/the-book-2nd.html) — Chapter 6 (Temporal-Difference Learning), §6.5 introduces Q-learning and proves its convergence under standard step-size conditions
- [Stable Baselines3 DQN docs](https://stable-baselines3.readthedocs.io/en/master/modules/dqn.html) — the discrete-action neural extension; useful to read alongside this skill to see what you give up by staying tabular

### Adjacent / alternative libraries
- [`gymnasium`](https://github.com/Farama-Foundation/Gymnasium) — modern fork of OpenAI Gym; the de facto env API for everything RL
- [`stable-baselines3`](https://github.com/DLR-RM/stable-baselines3) — DQN / PPO / SAC / A2C as drop-in algorithms when tables stop being enough
- [`river`](https://github.com/online-ml/river) — online-learning library; the `river.reinforcement` module fits when state space is large but the agent must still update incrementally
- [`pufferlib`](https://github.com/PufferAI/PufferLib) — fast vectorised env wrapper; useful when you graduate to DQN/PPO and need throughput
- [`finrl`](https://github.com/AI4Finance-Foundation/FinRL) — RL-for-quant ecosystem; ships pre-built trading envs you can swap into the same `q_learning_update` loop

### Academic papers
- Watkins, C. J. C. H. & Dayan, P. (1992). "Q-learning." *Machine Learning* 8(3), 279–292. [doi:10.1007/BF00992698](https://doi.org/10.1007/BF00992698) — the proof of convergence to the optimal action-value function under bounded reward + standard step-size conditions
- Watkins, C. J. C. H. (1989). "Learning from Delayed Rewards." PhD thesis, King's College, Cambridge. [PDF](https://www.cs.rhul.ac.uk/~chrisw/new_thesis.pdf) — the original introduction of the Q-learning algorithm
- Sutton, R. S. (1988). "Learning to predict by the methods of temporal differences." *Machine Learning* 3, 9–44. [doi:10.1007/BF00115009](https://doi.org/10.1007/BF00115009) — the TD foundation Q-learning builds on
- Tsitsiklis, J. N. (1994). "Asynchronous Stochastic Approximation and Q-Learning." *Machine Learning* 16, 185–202. [doi:10.1007/BF00993306](https://doi.org/10.1007/BF00993306) — convergence proof for the asynchronous (single-trajectory) update used in this skill

### Tutorials & write-ups
- [Lilian Weng — "A (Long) Peek into Reinforcement Learning"](https://lilianweng.github.io/posts/2018-02-19-rl-overview/) — the standard one-pager for the TD / Q-learning / Bellman vocabulary
- [David Silver's RL course (DeepMind / UCL, free)](https://www.davidsilver.uk/teaching/) — Lecture 4 + 5 cover model-free prediction and control; the canonical lecture pair for this skill
- [Spinning Up in Deep RL (OpenAI, free)](https://spinningup.openai.com/en/latest/) — bridges from tabular Q to deep variants; the diagrams are worth bookmarking

### Standard environments
- `CartPole-v1` — [gymnasium](https://gymnasium.farama.org/environments/classic_control/cart_pole/) — discrete-action toy; not directly useful for quant but the canonical sanity-check that your Q-learning loop works
- `FrozenLake-v1` (`is_slippery=False`) — [gymnasium](https://gymnasium.farama.org/environments/toy_text/frozen_lake/) — stochastic gridworld; the standard "does my tabular Q converge" test

### Last cross-checked
2026-05-20 — Sutton & Barto edition 2 + Gymnasium docs + Watkins 1992 / 1989. No primary library to Context7-pin (algorithm-only skill).
