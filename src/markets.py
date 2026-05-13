"""Per-market helpers — bootstrap CIs for per-card profit comparisons."""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def bootstrap_mean_ci(values: Iterable[float],
                      n_resamples: int = 1000,
                      confidence: float = 0.95,
                      seed: int = 42) -> tuple[float, float, float]:
    """Percentile-bootstrap (mean, lower, upper) for the mean of `values`."""
    arr = np.asarray(list(values), dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    if n == 0:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = rng.choice(arr, size=(n_resamples, n), replace=True).mean(axis=1)
    alpha = (1 - confidence) / 2
    return float(arr.mean()), float(np.quantile(means, alpha)), float(np.quantile(means, 1 - alpha))


def per_card_profit_with_ci(card_profit: pd.DataFrame,
                            group_col: str = "market",
                            value_col: str = "profit_gbp",
                            min_n: int = 10) -> pd.DataFrame:
    """`card_profit` has one row per card, with columns [group_col, value_col].
    Returns mean and 95% CI per group, filtered to groups with at least `min_n` cards.
    """
    rows = []
    for g, sub in card_profit.groupby(group_col):
        if len(sub) < min_n:
            continue
        mean, lo, hi = bootstrap_mean_ci(sub[value_col].values)
        rows.append({group_col: g, "n_cards": len(sub),
                     "mean_profit_per_card": mean, "ci_lo": lo, "ci_hi": hi})
    return (pd.DataFrame(rows)
            .sort_values("mean_profit_per_card", ascending=False)
            .reset_index(drop=True))
