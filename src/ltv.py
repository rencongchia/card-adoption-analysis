"""12-month LTV forecasting.

Given an observed `tenure_stats` table (the output of `sql/05_tenure_stats.sql`), extrapolate
expected profit per card across months 0..11 under an assumed transactor attrition rate.

- `cohort_ltv_curve`: use observed transactor_share × profit_per_transactor up to the last
  reliable tenure month, then extrapolate using an attrition rate on the transactor curve and
  hold per-transactor profit at the mean over T=1..anchor.
- `assumption_sweep`: sweep cohort_ltv_curve across a grid of attrition rates.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class LtvScenario:
    attrition_rate: float = 0.10   # monthly transactor decay after the reliable horizon
    anchor_tenure: int = 3         # last tenure month with a sample large enough to anchor on.
                                    # Under calendar-month bucketing T=3 has 284 eligible cards;
                                    # T=4 drops to 27. See 02_exploration.ipynb §3.
    horizon_months: int = 12


def cohort_ltv_curve(observed: pd.DataFrame,
                     scenario: LtvScenario = LtvScenario()) -> tuple[float, pd.DataFrame]:
    """Curve method: observed up to `anchor_tenure`, then transactor share decays at
    `attrition_rate` per month and per-transactor profit holds at the mean over T=1..anchor
    (T=0 excluded — partial-month deflation makes it anomalously low).

    Returns (12-month LTV in GBP, per-tenure forecast DataFrame).
    """
    obs = observed.set_index("month_since_issuance")
    baseline_share = float(obs.loc[scenario.anchor_tenure, "transactor_share"])
    tail_profit = float(
        observed.loc[observed["month_since_issuance"].between(1, scenario.anchor_tenure),
                     "profit_per_transactor_gbp"].mean()
    )

    rows: list[dict] = []
    cum = 0.0
    for t in range(scenario.horizon_months):
        if t <= scenario.anchor_tenure and t in obs.index:
            share = float(obs.loc[t, "transactor_share"])
            profit_if_transacting = float(obs.loc[t, "profit_per_transactor_gbp"])
            source = "observed"
        else:
            steps_past = t - scenario.anchor_tenure
            share = baseline_share * ((1 - scenario.attrition_rate) ** steps_past)
            profit_if_transacting = tail_profit
            source = "extrapolated"
        expected = share * profit_if_transacting
        cum += expected
        rows.append({
            "month_since_issuance":      t,
            "source":                    source,
            "transactor_share":          share,
            "profit_per_transactor_gbp": profit_if_transacting,
            "expected_profit_gbp":       expected,
            "cumulative_ltv_gbp":        cum,
        })
    forecast = pd.DataFrame(rows)
    return cum, forecast


def assumption_sweep(observed: pd.DataFrame,
                     attrition_rates: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20),
                     anchor_tenure: int = 3,
                     horizon_months: int = 12) -> pd.DataFrame:
    """Sweep cohort_ltv_curve across attrition rates.
    Powers the deck's 'central estimate, range' headline."""
    rows = []
    for rate in attrition_rates:
        ltv, _ = cohort_ltv_curve(observed, LtvScenario(
            attrition_rate=rate,
            anchor_tenure=anchor_tenure,
            horizon_months=horizon_months,
        ))
        rows.append({"attrition_rate": rate, "ltv_gbp": ltv})
    return pd.DataFrame(rows)
