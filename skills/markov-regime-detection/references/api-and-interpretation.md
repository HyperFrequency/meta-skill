# Key API Surface

| Object / attribute | Purpose |
|---|---|
| `hmm.GaussianHMM(n_components, covariance_type, n_iter, tol, random_state)` | Continuous-emission HMM (the standard for returns) |
| `hmm.CategoricalHMM(n_components, n_features)` | Discrete-emission HMM; observations are integer indices in `[0, n_features)` |
| `hmm.GMMHMM(n_components, n_mix)` | Gaussian-mixture emissions per state (richer than `GaussianHMM`) |
| `hmm.PoissonHMM(n_components)` | Count-data emissions |
| `model.fit(X, lengths=None)` | EM via Baum-Welch; `lengths` for multiple independent sequences |
| `model.predict(X)` | Viterbi-decoded most likely state sequence |
| `model.predict_proba(X)` | Smoothed posterior `P(state | data)`, shape `(n_samples, n_components)` |
| `model.score(X)` | Log-likelihood of `X` under the fitted model |
| `model.score_samples(X)` | Log-likelihood + per-sample posteriors |
| `model.decode(X, algorithm='viterbi'\|'map')` | State sequence + decoding score |
| `model.sample(n)` | Generate `(observations, states)` from the fitted model |
| `model.startprob_` / `transmat_` / `means_` / `covars_` / `emissionprob_` | Fitted parameters; can also be hand-set before `fit()` to fix structure |
| `model.monitor_.converged` / `.history` | EM convergence flag and per-iteration log-likelihood trace |
| `model.n_features` | Set automatically by `GaussianHMM` from `X.shape[1]`; must be set manually for `CategoricalHMM` before `fit` |

# Interpreting the Output

**Did EM converge?** Always check `model.monitor_.converged`. If `False`, increase `n_iter`
(try 500–1000) or restart with a different `random_state`. EM is **highly sensitive to
initialization** — run 10+ random seeds and keep the best by log-likelihood.

**Model selection — how many states?**
- Fit 2, 3, 4, 5 states; compare on a **held-out** segment via `score(X_holdout)` (in-sample
  log-likelihood mechanically increases with more states).
- AIC / BIC are not exposed directly by `hmmlearn`; compute manually:
  - `n_params = K*(K-1) + (K-1) + K*D + K*D*(D+1)/2` for `GaussianHMM(K, 'full')` with `D` features.
  - `aic = -2 * loglik + 2 * n_params`, `bic = -2 * loglik + log(n_obs) * n_params`.
- Diminishing returns are usually at 2-4 states for daily returns. 5+ states overfit unless you
  have years of data.

**State durations.** Expected duration in state `i` = `1 / (1 - transmat_[i, i])`. Bull/bear
states typically have self-transition probability `> 0.95` (long persistence). If a fitted state
has `transmat_[i, i] < 0.5`, it's barely a regime — likely overfit noise.

**Label switching.** HMM states have **no inherent ordering**: two fits with different
`random_state` may swap state 0 and state 1. **Always relabel** by a deterministic rule (e.g.
sort by `means_.ravel()`) before downstream analysis or you'll get nonsense backtests.

**Smoothed vs filtered probabilities.** `predict_proba` returns **smoothed** posteriors
`P(state_t | data_{1:T})` — uses future data, so not realistic for live trading. For real-time
regime detection, you need the **filtered** posterior `P(state_t | data_{1:t})` — implement via
the forward pass on each rolling window (not directly exposed; use `score_samples` on expanding
windows, or roll your own forward algorithm).

# Common Pitfalls

1. **Random-init sensitivity.** Run 10–20 different `random_state` values, keep the one with the
   highest `score(X)`. A single fit can land in a local optimum that misses obvious regimes. This
   is **the** most common failure mode.
2. **Label switching across fits.** Two HMMs with the same architecture may identify the same
   regimes but number them differently. Hard-relabel by `means_` (or some other deterministic
   statistic) before comparing or aggregating across fits.
3. **Treating decoded states as ground truth.** `predict` returns the most likely state sequence —
   it does not quantify uncertainty. Adjacent low-confidence days can flip between regimes. Use
   `predict_proba` and apply a probability threshold (e.g. only act when `P(bull) > 0.7`).
4. **Look-ahead bias from `predict_proba`.** Smoothed posteriors use the entire data history
   including future observations. Backtesting a strategy that uses `state_probs[t]` to decide
   trades **leaks future information** and inflates returns. Use a true online / filtered estimate.
5. **Not converged but still using the model.** If `monitor_.converged == False`, parameters are
   wherever EM stopped — usually nonsense. Bump `n_iter` or `tol`. Don't ignore the flag.
6. **CategoricalHMM `n_features` mismatch.** `CategoricalHMM` infers `n_features` from data unless
   you set it explicitly. If your held-out set has a category the train set didn't, predict will
   crash or silently treat the new index as unknown. Set `model.n_features = K` before `fit` for
   safety.
7. **Too many states relative to sample size.** With 252 daily observations and `n_components=5`,
   you have ~50 obs per state — barely enough for a univariate Gaussian, hopeless for a full
   `(D x D)` covariance with `D > 1`. Use `covariance_type='diag'` or fewer states.
