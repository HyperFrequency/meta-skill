# Worked Examples

## 3-State GaussianHMM on Returns, Decode Regimes

```python
import numpy as np
import pandas as pd
from hmmlearn import hmm

# Synthetic 3-regime return series: bull (drift up, low vol), bear (drift down, high vol),
# sideways (no drift, mid vol). Real data: replace with actual daily returns.
rng = np.random.default_rng(2026)
n_per = 250
bull     = rng.normal(loc= 0.0010, scale=0.008, size=n_per)
sideways = rng.normal(loc= 0.0000, scale=0.012, size=n_per)
bear     = rng.normal(loc=-0.0015, scale=0.022, size=n_per)
returns = np.concatenate([bull, sideways, bear, bull, bear])
X = returns.reshape(-1, 1)  # hmmlearn expects 2D: (n_samples, n_features)

# Fit a 3-state Gaussian HMM. Multiple random seeds because EM is sensitive to init.
best_model, best_score = None, -np.inf
for seed in range(10):
    model = hmm.GaussianHMM(
        n_components=3,
        covariance_type='full',   # also: 'diag', 'spherical', 'tied'
        n_iter=200,
        tol=1e-4,
        random_state=seed,
    )
    model.fit(X)
    if model.monitor_.converged and model.score(X) > best_score:
        best_model, best_score = model, model.score(X)

print(f"Best log-likelihood: {best_score:.2f}")
print(f"State means (annualized ret): {best_model.means_.ravel() * 252}")
print(f"State stds (annualized vol):  {np.sqrt(best_model.covars_.ravel()) * np.sqrt(252)}")
print(f"Transition matrix:\n{best_model.transmat_.round(3)}")

# Viterbi decode: most likely state sequence
states = best_model.predict(X)
# Smoothed posterior probabilities P(state_t | all data)
state_probs = best_model.predict_proba(X)

# Label states by mean return (lowest = bear, highest = bull) for downstream use.
order = np.argsort(best_model.means_.ravel())
label_map = {order[0]: 'bear', order[1]: 'sideways', order[2]: 'bull'}
labels = pd.Series([label_map[s] for s in states])
print(labels.value_counts())
```

## Model Selection via Held-Out Log-Likelihood

```python
import numpy as np
from hmmlearn import hmm

X = ...  # 2D returns array, shape (T, 1)
split = int(0.7 * len(X))
X_train, X_test = X[:split], X[split:]

results = {}
for K in (2, 3, 4, 5):
    best_score = -np.inf
    for seed in range(20):
        m = hmm.GaussianHMM(n_components=K, covariance_type='full',
                            n_iter=300, random_state=seed)
        try:
            m.fit(X_train)
            if m.monitor_.converged:
                s = m.score(X_test)              # out-of-sample log-likelihood
                if s > best_score:
                    best_score = s
        except Exception:
            continue
    results[K] = best_score
print(results)
# Choose K with highest out-of-sample log-likelihood, considering the
# law of diminishing returns. BIC penalizes more aggressively than AIC.
```

## CategoricalHMM for Hand-Built Signal Alphabets

If you've discretized returns into a small alphabet (e.g. trinary `{down, flat, up}` or a
5-bin quantile encoding), `CategoricalHMM` fits a discrete-emission HMM directly:

```python
from hmmlearn import hmm
import numpy as np

# Encode returns into 5 quantile bins.
returns = ...  # 1D array
bins = np.quantile(returns, [0.2, 0.4, 0.6, 0.8])
symbols = np.digitize(returns, bins).reshape(-1, 1)   # in {0,1,2,3,4}

K = 3                       # number of regimes
n_features = 5              # alphabet size — MUST be set explicitly
model = hmm.CategoricalHMM(n_components=K, n_iter=300, random_state=0)
model.n_features = n_features
model.fit(symbols)

states = model.predict(symbols)
print("Emission probability matrix (state x symbol):")
print(model.emissionprob_.round(3))
```

Useful when you want regimes over *categorical* signal data (e.g. a regime classifier over
technical-indicator regimes, sentiment buckets, or hand-engineered features).
