# Configuration, Guardrails, Efficient Frontier & Carry-Forward

Relocated from `SKILL.md` to keep the router lean. This file holds the full,
runnable implementations for the principled configuration object, the
data-driven thresholds, the four guardrails, the Pareto frontier selector, and
the per-fold carry-forward state machine.

All parameters are derived from the search space or data characteristics — no
magic numbers.

---

## Core Formula: Walk-Forward Efficiency

```python
def compute_wfe(
    is_sharpe: float,
    oos_sharpe: float,
    n_samples: int | None = None,
) -> float | None:
    """Walk-Forward Efficiency - measures performance transfer.

    WFE = OOS_Sharpe / IS_Sharpe

    Interpretation (guidelines, not hard thresholds):
    - WFE ≥ 0.70: Excellent transfer (low overfitting)
    - WFE 0.50-0.70: Good transfer
    - WFE 0.30-0.50: Moderate transfer (investigate)
    - WFE < 0.30: Severe overfitting (likely reject)

    The IS_Sharpe minimum is derived from signal-to-noise ratio,
    not a fixed magic number. See compute_is_sharpe_threshold().

    Reference: Pardo (2008) "The Evaluation and Optimization of Trading Strategies"
    """
    # Data-driven threshold: IS_Sharpe must exceed 2σ noise floor
    min_is_sharpe = compute_is_sharpe_threshold(n_samples) if n_samples else 0.1

    if abs(is_sharpe) < min_is_sharpe:
        return None
    return oos_sharpe / is_sharpe
```

---

## AWFESConfig: Unified Configuration

```python
from dataclasses import dataclass, field
from typing import Literal
import numpy as np

@dataclass
class AWFESConfig:
    """AWFES configuration with principled parameter derivation.

    No magic numbers - all values derived from search space or data.
    """
    # Search space bounds (user-specified)
    min_epoch: int
    max_epoch: int
    granularity: int  # Number of frontier points

    # Derived automatically
    epoch_configs: list[int] = field(init=False)
    prior_variance: float = field(init=False)
    observation_variance: float = field(init=False)

    # Market context for annualization
    # crypto_session_filtered: Use when data is filtered to London-NY weekday hours
    market_type: Literal["crypto_24_7", "crypto_session_filtered", "equity", "forex"] = "crypto_24_7"
    time_unit: Literal["bar", "daily", "weekly"] = "weekly"

    def __post_init__(self):
        # Generate epoch configs with log spacing (optimal for frontier discovery)
        self.epoch_configs = self._generate_epoch_configs()

        # Derive Bayesian variances from search space
        self.prior_variance, self.observation_variance = self._derive_variances()

    def _generate_epoch_configs(self) -> list[int]:
        """Generate epoch candidates with log spacing.

        Log spacing is optimal for efficient frontier because:
        1. Early epochs: small changes matter more (underfit → fit transition)
        2. Late epochs: diminishing returns (already near convergence)
        3. Uniform coverage of the WFE vs cost trade-off space

        Formula: epoch_i = min × (max/min)^(i/(n-1))
        """
        if self.granularity < 2:
            return [self.min_epoch]

        log_min = np.log(self.min_epoch)
        log_max = np.log(self.max_epoch)
        log_epochs = np.linspace(log_min, log_max, self.granularity)

        return sorted(set(int(round(np.exp(e))) for e in log_epochs))

    def _derive_variances(self) -> tuple[float, float]:
        """Derive Bayesian variances from search space.

        Principle: Prior should span the search space with ~95% coverage.

        For Normal distribution: 95% CI = mean ± 1.96σ
        If we want 95% of prior mass in [min_epoch, max_epoch]:
            range = max - min = 2 × 1.96 × σ = 3.92σ
            σ = range / 3.92
            σ² = (range / 3.92)²

        Observation variance: Set to achieve reasonable learning rate.
        Rule: observation_variance ≈ prior_variance / 4
        This means each observation updates the posterior meaningfully
        but doesn't dominate the prior immediately.
        """
        epoch_range = self.max_epoch - self.min_epoch
        prior_std = epoch_range / 3.92  # 95% CI spans search space
        prior_variance = prior_std ** 2

        # Observation variance: 1/4 of prior for balanced learning
        # This gives ~0.2 weight to each new observation initially
        observation_variance = prior_variance / 4

        return prior_variance, observation_variance

    @classmethod
    def from_search_space(
        cls,
        min_epoch: int,
        max_epoch: int,
        granularity: int = 5,
        market_type: str = "crypto_24_7",
    ) -> "AWFESConfig":
        """Create config from search space bounds."""
        return cls(
            min_epoch=min_epoch,
            max_epoch=max_epoch,
            granularity=granularity,
            market_type=market_type,
        )

    def compute_wfe(
        self,
        is_sharpe: float,
        oos_sharpe: float,
        n_samples: int | None = None,
    ) -> float | None:
        """Compute WFE with data-driven IS_Sharpe threshold."""
        min_is = compute_is_sharpe_threshold(n_samples) if n_samples else 0.1
        if abs(is_sharpe) < min_is:
            return None
        return oos_sharpe / is_sharpe

    def get_annualization_factor(self) -> float:
        """Get annualization factor to scale Sharpe from time_unit to ANNUAL.

        IMPORTANT: This returns sqrt(periods_per_year) for scaling to ANNUAL Sharpe.
        For daily-to-weekly scaling, use get_daily_to_weekly_factor() instead.

        Principled derivation:
        - Sharpe scales with √(periods per year)
        - Crypto 24/7: 365 days/year, 52.14 weeks/year
        - Crypto session-filtered: 252 days/year (like equity)
        - Equity: 252 trading days/year, ~52 weeks/year
        - Forex: ~252 days/year (varies by pair)
        """
        PERIODS_PER_YEAR = {
            ("crypto_24_7", "daily"): 365,
            ("crypto_24_7", "weekly"): 52.14,
            ("crypto_24_7", "bar"): None,  # Cannot annualize bars directly
            ("crypto_session_filtered", "daily"): 252,  # London-NY weekdays only
            ("crypto_session_filtered", "weekly"): 52,
            ("equity", "daily"): 252,
            ("equity", "weekly"): 52,
            ("forex", "daily"): 252,
        }

        key = (self.market_type, self.time_unit)
        periods = PERIODS_PER_YEAR.get(key)

        if periods is None:
            raise ValueError(
                f"Cannot annualize {self.time_unit} for {self.market_type}. "
                "Use daily or weekly aggregation first."
            )

        return np.sqrt(periods)

    def get_daily_to_weekly_factor(self) -> float:
        """Get factor to scale DAILY Sharpe to WEEKLY Sharpe.

        This is different from get_annualization_factor()!
        - Daily → Weekly: sqrt(days_per_week)
        - Daily → Annual: sqrt(days_per_year)  (use get_annualization_factor)

        Market-specific:
        - Crypto 24/7: sqrt(7) = 2.65 (7 trading days/week)
        - Crypto session-filtered: sqrt(5) = 2.24 (weekdays only)
        - Equity: sqrt(5) = 2.24 (5 trading days/week)
        """
        DAYS_PER_WEEK = {
            "crypto_24_7": 7,
            "crypto_session_filtered": 5,  # London-NY weekdays only
            "equity": 5,
            "forex": 5,
        }

        days = DAYS_PER_WEEK.get(self.market_type)
        if days is None:
            raise ValueError(f"Unknown market type: {self.market_type}")

        return np.sqrt(days)
```

---

## IS_Sharpe Threshold: Signal-to-Noise Derivation

```python
def compute_is_sharpe_threshold(n_samples: int | None = None) -> float:
    """Compute minimum IS_Sharpe threshold from signal-to-noise ratio.

    Principle: IS_Sharpe must be statistically distinguishable from zero.

    Under null hypothesis (no skill), Sharpe ~ N(0, 1/√n).
    To reject null at α=0.05 (one-sided), need Sharpe > 1.645/√n.

    For practical use, we use 2σ threshold (≈97.7% confidence):
        threshold = 2.0 / √n

    This adapts to sample size:
    - n=100: threshold ≈ 0.20
    - n=400: threshold ≈ 0.10
    - n=1600: threshold ≈ 0.05

    Fallback for unknown n: 0.1 (assumes n≈400, typical fold size)

    Rationale for 0.1 fallback:
    - 2/√400 = 0.1, so 0.1 assumes ~400 samples per fold
    - This is conservative: 400 samples is typical for weekly folds
    - If actual n is smaller, threshold is looser (accepts more noise)
    - If actual n is larger, threshold is tighter (fine, we're conservative)
    - The 0.1 value also corresponds to "not statistically distinguishable
      from zero at reasonable sample sizes" - a natural floor for Sharpe SE
    """
    if n_samples is None or n_samples < 10:
        # Conservative fallback: 0.1 assumes ~400 samples (typical fold size)
        # Derivation: 2/√400 = 0.1; see rationale above
        return 0.1

    return 2.0 / np.sqrt(n_samples)
```

---

## Guardrails (Principled Guidelines)

### G1: WFE Thresholds

The traditional thresholds (0.30, 0.50, 0.70) are **guidelines based on practitioner consensus**, not derived from first principles. They represent:

| Threshold | Meaning     | Statistical Basis                                          |
| --------- | ----------- | ---------------------------------------------------------- |
| **0.30**  | Hard reject | Retaining <30% of IS performance is almost certainly noise |
| **0.50**  | Warning     | At 50%, half the signal is lost - investigate              |
| **0.70**  | Target      | Industry standard for "good" transfer                      |

```python
# These are GUIDELINES, not hard rules
# Adjust based on your domain and risk tolerance
WFE_THRESHOLDS = {
    "hard_reject": 0.30,  # Below this: almost certainly overfitting
    "warning": 0.50,      # Below this: significant signal loss
    "target": 0.70,       # Above this: good generalization
}

def classify_wfe(wfe: float | None) -> str:
    """Classify WFE with principled thresholds."""
    if wfe is None:
        return "INVALID"  # IS_Sharpe below noise floor
    if wfe < WFE_THRESHOLDS["hard_reject"]:
        return "REJECT"
    if wfe < WFE_THRESHOLDS["warning"]:
        return "INVESTIGATE"
    if wfe < WFE_THRESHOLDS["target"]:
        return "ACCEPTABLE"
    return "EXCELLENT"
```

### G2: IS_Sharpe Minimum (Data-Driven)

**OLD (magic number):**

```python
# WRONG: Fixed threshold regardless of sample size
if is_sharpe < 1.0:
    wfe = None
```

**NEW (principled):**

```python
# CORRECT: Threshold adapts to sample size
min_is_sharpe = compute_is_sharpe_threshold(n_samples)
if is_sharpe < min_is_sharpe:
    wfe = None  # Below noise floor for this sample size
```

The threshold derives from the standard error of Sharpe ratio: SE(SR) ≈ 1/√n.

**Note on SE(Sharpe) approximation**: The formula `1/√n` is a first-order approximation valid when SR is small (close to 0). The full Lo (2002) formula is:

```
SE(SR) = √((1 + 0.5×SR²) / n)
```

For high-Sharpe strategies (SR > 1.0), the simplified formula underestimates SE by ~25-50%. Use the full formula when evaluating strategies with SR > 1.0.

### G3: Stability Penalty for Epoch Changes (Adaptive)

The stability penalty prevents hyperparameter churn. Instead of fixed thresholds, use **relative improvement** based on WFE variance:

```python
def compute_stability_threshold(wfe_history: list[float]) -> float:
    """Compute stability threshold from observed WFE variance.

    Principle: Require improvement exceeding noise level.

    If WFE has std=0.15 across folds, random fluctuation could be ±0.15.
    To distinguish signal from noise, require improvement > 1σ of WFE.

    Minimum: 5% (prevent switching on negligible improvements)
    Maximum: 20% (don't be overly conservative)
    """
    if len(wfe_history) < 3:
        return 0.10  # Default until enough history

    wfe_std = np.std(wfe_history)
    threshold = max(0.05, min(0.20, wfe_std))
    return threshold


class AdaptiveStabilityPenalty:
    """Stability penalty that adapts to observed WFE variance."""

    def __init__(self):
        self.wfe_history: list[float] = []
        self.epoch_changes: list[int] = []

    def should_change_epoch(
        self,
        current_wfe: float,
        candidate_wfe: float,
        current_epoch: int,
        candidate_epoch: int,
    ) -> bool:
        """Decide whether to change epochs based on adaptive threshold."""
        self.wfe_history.append(current_wfe)

        if current_epoch == candidate_epoch:
            return False  # Same epoch, no change needed

        threshold = compute_stability_threshold(self.wfe_history)
        improvement = (candidate_wfe - current_wfe) / max(abs(current_wfe), 0.01)

        if improvement > threshold:
            self.epoch_changes.append(len(self.wfe_history))
            return True

        return False  # Improvement not significant
```

### G4: DSR Adjustment for Epoch Search (Principled)

```python
def adjusted_dsr_for_epoch_search(
    sharpe: float,
    n_folds: int,
    n_epochs: int,
    sharpe_se: float | None = None,
    n_samples_per_fold: int | None = None,
) -> float:
    """Deflated Sharpe Ratio accounting for epoch selection multiplicity.

    When selecting from K epochs, the expected maximum Sharpe under null
    is inflated. This adjustment corrects for that selection bias.

    Principled SE estimation:
    - If n_samples provided: SE(Sharpe) ≈ 1/√n
    - Otherwise: estimate from typical fold size

    Reference: Bailey & López de Prado (2014), Gumbel distribution
    """
    from math import sqrt, log, pi

    n_trials = n_folds * n_epochs  # Total selection events

    if n_trials < 2:
        return sharpe  # No multiple testing correction needed

    # Expected maximum under null (Gumbel distribution)
    # E[max(Z_1, ..., Z_n)] ≈ √(2·ln(n)) - (γ + ln(π/2)) / √(2·ln(n))
    # where γ ≈ 0.5772 is Euler-Mascheroni constant
    euler_gamma = 0.5772156649
    sqrt_2_log_n = sqrt(2 * log(n_trials))
    e_max_z = sqrt_2_log_n - (euler_gamma + log(pi / 2)) / sqrt_2_log_n

    # Estimate Sharpe SE if not provided
    if sharpe_se is None:
        if n_samples_per_fold is not None:
            sharpe_se = 1.0 / sqrt(n_samples_per_fold)
        else:
            # Conservative default: assume ~300 samples per fold
            sharpe_se = 1.0 / sqrt(300)

    # Expected maximum Sharpe under null
    e_max_sharpe = e_max_z * sharpe_se

    # Deflated Sharpe
    return max(0, sharpe - e_max_sharpe)
```

**Example**: For 5 epochs × 50 folds = 250 trials with 300 samples/fold:

- `sharpe_se ≈ 0.058`
- `e_max_z ≈ 2.88`
- `e_max_sharpe ≈ 0.17`
- A Sharpe of 1.0 deflates to **0.83** after adjustment.

---

## Efficient Frontier Algorithm

```python
def compute_efficient_frontier(
    epoch_metrics: list[dict],
    wfe_weight: float = 1.0,
    time_weight: float = 0.1,
) -> tuple[list[int], int]:
    """
    Find Pareto-optimal epochs and select best.

    An epoch is on the frontier if no other epoch dominates it
    (better WFE AND lower training time).

    Args:
        epoch_metrics: List of {epoch, wfe, training_time_sec}
        wfe_weight: Weight for WFE in selection (higher = prefer generalization)
        time_weight: Weight for training time (higher = prefer speed)

    Returns:
        (frontier_epochs, selected_epoch)
    """
    import numpy as np

    # Filter valid metrics
    valid = [(m["epoch"], m["wfe"], m.get("training_time_sec", m["epoch"]))
             for m in epoch_metrics
             if m["wfe"] is not None and np.isfinite(m["wfe"])]

    if not valid:
        # Fallback: return epoch with best OOS Sharpe
        best_oos = max(epoch_metrics, key=lambda m: m.get("oos_sharpe", 0))
        return ([best_oos["epoch"]], best_oos["epoch"])

    # Pareto dominance check
    frontier = []
    for i, (epoch_i, wfe_i, time_i) in enumerate(valid):
        dominated = False
        for j, (epoch_j, wfe_j, time_j) in enumerate(valid):
            if i == j:
                continue
            # j dominates i if: better/equal WFE AND lower/equal time (strict in at least one)
            if (wfe_j >= wfe_i and time_j <= time_i and
                (wfe_j > wfe_i or time_j < time_i)):
                dominated = True
                break
        if not dominated:
            frontier.append((epoch_i, wfe_i, time_i))

    frontier_epochs = [e for e, _, _ in frontier]

    if len(frontier) == 1:
        return (frontier_epochs, frontier[0][0])

    # Weighted score selection
    wfes = np.array([w for _, w, _ in frontier])
    times = np.array([t for _, _, t in frontier])

    wfe_norm = (wfes - wfes.min()) / (wfes.max() - wfes.min() + 1e-10)
    time_norm = (times.max() - times) / (times.max() - times.min() + 1e-10)

    scores = wfe_weight * wfe_norm + time_weight * time_norm
    best_idx = np.argmax(scores)

    return (frontier_epochs, frontier[best_idx][0])
```

---

## Carry-Forward Mechanism

```python
class AdaptiveEpochSelector:
    """Maintains epoch selection state across WFO folds with adaptive stability."""

    def __init__(self, epoch_configs: list[int]):
        self.epoch_configs = epoch_configs
        self.selection_history: list[dict] = []
        self.last_selected: int | None = None
        self.stability = AdaptiveStabilityPenalty()  # Use adaptive, not fixed

    def select_epoch(self, epoch_metrics: list[dict]) -> int:
        """Select epoch with adaptive stability penalty for changes."""
        frontier_epochs, candidate = compute_efficient_frontier(epoch_metrics)

        # Apply adaptive stability penalty if changing epochs
        if self.last_selected is not None and candidate != self.last_selected:
            candidate_wfe = next(
                m["wfe"] for m in epoch_metrics if m["epoch"] == candidate
            )
            last_wfe = next(
                (m["wfe"] for m in epoch_metrics if m["epoch"] == self.last_selected),
                0.0
            )

            # Use adaptive threshold derived from WFE variance
            if not self.stability.should_change_epoch(
                last_wfe, candidate_wfe, self.last_selected, candidate
            ):
                candidate = self.last_selected

        # Record and return
        self.selection_history.append({
            "epoch": candidate,
            "frontier": frontier_epochs,
            "changed": candidate != self.last_selected,
        })
        self.last_selected = candidate
        return candidate
```

---

## Troubleshooting

| Issue                       | Cause                       | Solution                                           |
| --------------------------- | --------------------------- | -------------------------------------------------- |
| WFE is None                 | IS_Sharpe below noise floor | Check if IS_Sharpe > 2/sqrt(n_samples)             |
| All epochs rejected         | Severe overfitting          | Reduce model complexity, add regularization        |
| Bayesian posterior unstable | High WFE variance           | Increase observation_variance or use median WFE    |
| Epoch always at boundary    | Search range too narrow     | Expand min_epoch or max_epoch bounds               |
| Look-ahead bias detected    | Using val_optimal for test  | Use prior_bayesian_epoch for test evaluation       |
| DSR too aggressive          | Too many epoch candidates   | Limit to 3-5 epoch configs (meta-overfitting risk) |
| Cauchy mean issues          | Arithmetic mean of WFE      | Use median or pooled WFE for aggregation           |
| Fold metrics inconsistent   | Variable fold sizes         | Use pooled WFE (precision-weighted)                |
