# Code Snippets — Reference Implementations

Minimal, dependency-light reference implementations (numpy / pandas / scikit-learn).
`mlfinlab` is the canonical production backbone; these are for understanding and zero-dependency use.

## Purged K-fold CV (López de Prado)

```python
import numpy as np
import pandas as pd
from sklearn.model_selection._split import _BaseKFold


class PurgedKFold(_BaseKFold):
    """K-fold CV that purges training samples whose label end-time falls inside the test fold,
    and optionally embargoes a window after each test fold.

    Reference: López de Prado (2018), Advances in Financial Machine Learning, Ch. 7.
    """

    def __init__(self, n_splits: int, t1: pd.Series, embargo_pct: float = 0.01):
        super().__init__(n_splits=n_splits, shuffle=False, random_state=None)
        if not isinstance(t1, pd.Series):
            raise TypeError("t1 must be a pd.Series indexed by event start time")
        self.t1 = t1
        self.embargo_pct = embargo_pct

    def split(self, X: pd.DataFrame, y=None, groups=None):
        if (X.index != self.t1.index).any():
            raise ValueError("X.index and t1.index must match")

        indices = np.arange(X.shape[0])
        embargo = int(X.shape[0] * self.embargo_pct)

        # Test folds are contiguous blocks of indices
        test_starts = [(i[0], i[-1] + 1) for i in
                       np.array_split(indices, self.n_splits)]

        for start, end in test_starts:
            test_idx = indices[start:end]
            t0 = self.t1.index[start]
            t1_test = self.t1.iloc[end - 1]

            # PURGE: drop training samples whose label end time is inside the test window
            train_idx = self.t1.index[(self.t1 < t0) | (self.t1.index > t1_test)]
            train_pos = X.index.get_indexer(train_idx)
            train_pos = train_pos[train_pos >= 0]

            # EMBARGO: drop the `embargo` indices immediately following the test fold
            if embargo > 0:
                embargo_end = min(end + embargo, len(indices))
                embargo_idx = indices[end:embargo_end]
                train_pos = np.setdiff1d(train_pos, embargo_idx)

            yield train_pos, test_idx
```

## Walk-forward backtest loop

```python
def walk_forward(
    X: pd.DataFrame,
    y: pd.Series,
    model_factory,
    train_size: int,
    test_size: int,
    step: int = None,
    anchored: bool = False,
) -> pd.DataFrame:
    """Walk-forward predictions for a time-ordered dataset.

    Args:
        X, y: feature matrix and target, sorted by time.
        model_factory: callable returning a fresh sklearn-like model each window.
        train_size: number of samples in each training window.
        test_size: number of samples to predict in each step.
        step: stride between windows; defaults to test_size (non-overlapping).
        anchored: if True, training window grows from index 0; else it slides.

    Returns:
        DataFrame with columns ['y_true', 'y_pred', 'fold'] indexed by X.index.
    """
    step = step or test_size
    out = []
    fold = 0
    start = train_size
    while start + test_size <= len(X):
        train_lo = 0 if anchored else start - train_size
        Xtr = X.iloc[train_lo:start]
        ytr = y.iloc[train_lo:start]
        Xte = X.iloc[start:start + test_size]
        yte = y.iloc[start:start + test_size]

        model = model_factory()
        model.fit(Xtr, ytr)
        yhat = model.predict(Xte)

        out.append(pd.DataFrame({
            "y_true": yte.values,
            "y_pred": yhat,
            "fold": fold,
        }, index=Xte.index))
        fold += 1
        start += step

    return pd.concat(out)
```

## Trading metrics from a returns series

```python
def trading_metrics(returns: pd.Series, periods_per_year: int = 252) -> dict:
    """Compute a standard tearsheet bundle from a per-period returns series."""
    r = returns.dropna()
    if len(r) < 2:
        return {}

    ann_factor = np.sqrt(periods_per_year)
    mean_r = r.mean()
    std_r = r.std()
    downside_std = r[r < 0].std()

    sharpe = (mean_r / std_r) * ann_factor if std_r > 0 else np.nan
    sortino = (mean_r / downside_std) * ann_factor if downside_std > 0 else np.nan

    cum = (1 + r).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    max_dd = drawdown.min()

    ann_return = (1 + mean_r) ** periods_per_year - 1
    calmar = ann_return / abs(max_dd) if max_dd != 0 else np.nan

    return {
        "annualized_return": ann_return,
        "annualized_vol": std_r * ann_factor,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": max_dd,
        "win_rate": (r > 0).mean(),
        "profit_factor": r[r > 0].sum() / -r[r < 0].sum() if (r < 0).any() else np.nan,
    }
```

## Probability of Backtest Overfitting (PBO)

```python
from itertools import combinations


def probability_of_backtest_overfitting(
    returns_matrix: pd.DataFrame,
    n_partitions: int = 16,
) -> float:
    """PBO over a matrix of strategy returns.

    Args:
        returns_matrix: T x N DataFrame, T time periods, N strategies, per-period returns.
        n_partitions: number of equal-length non-overlapping submatrices to split T into.
                      Must be even; combinations of n_partitions/2 form the IS sets.

    Returns:
        PBO ∈ [0, 1]: fraction of CPCV splits where the IS-winner ranks below OOS-median.

    Reference: Bailey, Borwein, López de Prado, Zhu (2014/2017),
    "The Probability of Backtest Overfitting", Journal of Computational Finance.
    """
    assert n_partitions % 2 == 0, "n_partitions must be even"

    # Split rows into n_partitions equal blocks
    blocks = np.array_split(returns_matrix.index, n_partitions)
    block_returns = [returns_matrix.loc[b] for b in blocks]

    # Each split: choose n/2 blocks as IS, rest as OOS
    is_block_idx_combos = list(combinations(range(n_partitions), n_partitions // 2))

    fail_count = 0
    for is_idx in is_block_idx_combos:
        oos_idx = [i for i in range(n_partitions) if i not in is_idx]
        is_returns = pd.concat([block_returns[i] for i in is_idx])
        oos_returns = pd.concat([block_returns[i] for i in oos_idx])

        # Use Sharpe as the ranking metric
        is_sharpe  = is_returns.mean() / is_returns.std()
        oos_sharpe = oos_returns.mean() / oos_returns.std()

        is_winner = is_sharpe.idxmax()
        oos_rank_of_winner = oos_sharpe.rank().loc[is_winner]
        oos_median_rank = (len(oos_sharpe) + 1) / 2

        if oos_rank_of_winner < oos_median_rank:
            fail_count += 1

    return fail_count / len(is_block_idx_combos)
```
