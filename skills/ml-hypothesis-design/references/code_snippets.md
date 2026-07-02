# Code Snippets

Reference implementations for the methodology in `SKILL.md`. These mirror the
`mlfinlab` `BacktestStatistics` API; prefer that library in production and use
these for clarity / when `mlfinlab` is unavailable.

## Deflated Sharpe Ratio

The Deflated Sharpe Ratio (DSR) computes the probability that the *observed*
Sharpe ratio exceeds the maximum Sharpe expected under the null, given
`N_trials` candidates and the higher moments of returns.

```python
import numpy as np
from scipy.stats import norm
from scipy.special import erfinv


def expected_max_sharpe(n_trials: int, sharpe_std: float = 1.0) -> float:
    """Expected maximum Sharpe across n_trials i.i.d. candidates with std sharpe_std.

    Uses the Gumbel/extreme-value approximation from Bailey & Lopez de Prado (2014).
    sharpe_std is the cross-trial std of Sharpe ratios under the null.
    """
    if n_trials < 2:
        return 0.0
    euler_mascheroni = 0.5772156649
    # E[max] ≈ sqrt(2 * ln(N)) - (gamma + ln(ln(N))) / (2 * sqrt(2 * ln(N)))
    # Bailey's form is:
    z = (1 - euler_mascheroni) * norm.ppf(1 - 1.0 / n_trials) \
        + euler_mascheroni * norm.ppf(1 - 1.0 / (n_trials * np.e))
    return sharpe_std * z


def deflated_sharpe_ratio(
    observed_sr: float,
    n_obs: int,
    skewness: float,
    kurtosis: float,
    n_trials: int,
    sharpe_std: float = 1.0,
) -> float:
    """Deflated Sharpe Ratio: probability the strategy's true Sharpe > 0
    given n_trials candidates and non-normal returns.

    Returns a probability in [0, 1]. A DSR > 0.95 is the conventional ship threshold.

    Reference: Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio",
    Journal of Portfolio Management 40(5), 94-107.
    """
    # Expected max Sharpe under the null with n_trials candidates
    sr_null = expected_max_sharpe(n_trials, sharpe_std)

    # Variance of the Sharpe estimator (Mertens 2002; accounts for skew/kurt)
    sr_var = (1 - skewness * observed_sr + ((kurtosis - 1) / 4) * observed_sr ** 2) / (n_obs - 1)
    sr_se = np.sqrt(sr_var)

    # DSR is the probability the observed exceeds the null max
    return float(norm.cdf((observed_sr - sr_null) / sr_se))


# Example
dsr = deflated_sharpe_ratio(
    observed_sr=1.2,       # Annualized Sharpe from your best backtest
    n_obs=252 * 5,         # 5 years of daily returns
    skewness=-0.3,         # Sample skewness of returns
    kurtosis=4.0,          # Sample kurtosis (NOT excess)
    n_trials=100,          # How many strategies you tried
    sharpe_std=0.5,        # Cross-trial Sharpe std (estimate from your sweep)
)
print(f"Deflated Sharpe (probability true SR > 0): {dsr:.3f}")
```

## Minimum Backtest Length

```python
def minimum_backtest_length(sharpe_target: float, n_trials: int, freq: int = 252) -> float:
    """Years of backtest needed so the best-of-N strategy's Sharpe is credible.

    Reference: Bailey, Borwein, Lopez de Prado, Zhu (2014/2017), "The Probability
    of Backtest Overfitting". Approximation: MinBTL ≈ (E[max SR under H0] / SR_target)^2.
    """
    sr_max_null = expected_max_sharpe(n_trials, sharpe_std=1.0)
    years = (sr_max_null / sharpe_target) ** 2
    return years


print(f"Minimum backtest length for SR=1.0 with 50 trials: "
      f"{minimum_backtest_length(1.0, 50):.1f} years")
# ~5.3 years — if you only have 3 years of data, the best of 50 trials is not credible.
```

## Bonferroni for a strategy sweep

```python
from scipy.stats import norm


def sharpe_pvalue(sr: float, n_obs: int) -> float:
    """One-sided p-value for H0: Sharpe = 0 (normal returns approximation, Lo 2002)."""
    se = np.sqrt((1 + 0.5 * sr ** 2) / n_obs)
    z = sr / se
    return 1 - norm.cdf(z)


def bonferroni_survivors(sharpes: list[float], n_obs: int, alpha: float = 0.05) -> list[int]:
    """Return indices of strategies that survive Bonferroni at family-wise alpha."""
    threshold = alpha / len(sharpes)
    return [i for i, sr in enumerate(sharpes) if sharpe_pvalue(sr, n_obs) < threshold]
```
