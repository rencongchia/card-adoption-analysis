# Wise Card — Customer Adoption & 12-Month LTV

This analysis answers three main questions:

1. **Q1** — What is the average profit per transaction type? What drives revenue and cost?
2. **Q2** — Forecast the average 12-month LTV per card for the current customer base.
3. **Q3** — How are markets performing? Where's the growth opportunity?

---

## Project structure

```
data/
  raw/dataset.xlsx             Source dataset (gitignored — place here before running)
  processed/*.csv              4 CSVs from validation: card, transaction, cost_structure, rates
  results/*.csv                7 CSVs from analysis: scorecard, CIs, LTV outputs
sql/
  01_clean_transactions.sql    Typed view + amount/billing/IC converted to GBP via rates
  02_cost_lookup.sql           (cost_type × region) → fixed_cost_gbp + variable_rate (includes Interchange line)
  03_profit_per_transaction.sql   Canonical per-row P&L — single source of truth for Q1/Q2/Q3
  04_card_cohort.sql           Per-card attributes + cohort_month for LTV
  05_tenure_stats.sql          Per-tenure observation table — feeds the LTV curve
  06_market_scorecard.sql      Per-market KPIs (volume, mix, profit/card, fail %)
notebooks/                     (run in numerical order)
  01_validate.ipynb            Load xlsx → schema / PK / FK / null audit → persist CSVs
  02_exploration.ipynb         EDA justifying every downstream numerical choice
  03_q1_unit_economics.ipynb   Q1: avg profit per tx type + by cost cell + 3-way IC sensitivity
  04_q2_ltv.ipynb              Q2: cohort/tenure LTV + per-market LTV + sensitivity grid
  05_q3_markets.ipynb          Q3: market scorecard + bootstrap CIs + recommendations
  06_figures_for_deck.ipynb    Export PNGs for the deck
src/
  db.py                        DuckDB helpers (get_conn, register_csv_tables, materialize_sql_file)
  ltv.py                       LTV forecasting (cohort_ltv_curve, decomposed_ltv, assumption_sweep)
  markets.py                   Bootstrap 95% CI helper for per-card profit
figures/*.png                  PNG exports used in the deck (gitignored, regenerated)
```

### Regenerate outputs

```bash
# Place the source dataset at data/raw/dataset.xlsx (gitignored, not redistributed)
uv sync
nbstripout --install
jupyter nbconvert --to notebook --execute notebooks/*.ipynb
```

Runtime: ~30 seconds. Everything is reproducible from a clean clone.

### Tools

- **DuckDB + SQL** for transformations
- **Pandas** for charts in notebooks
- **Altair** for in-notebook charts
- **uv** for env management; **nbstripout** for clean notebook diffs

---

## Data cleaning & findings

The source workbook has 6 sheets. We use 4: `card`, `transaction`, `cost_structure`, `rates`. The two that are not mentioned in the case study brief are ignored: `transaction Numair Playground` and `Sheet8`.

### Dataset shape

| Table | Rows | Note |
|---|---:|---|
| `card` | 2,901 | Production dates 2017-10-03 to 2018-04-30; `is_active = True` for every row |
| `transaction` | 18,596 | Date range 2018-01-01 to 2018-04-30 — a 4-month observation window |
| `cost_structure` | 36 | 2 cost types × 3 regions × 6 fee lines (3 Fixed + 3 Variable) |
| `rates` | 153 | Single-snapshot FX rates to GBP and USD |

### Validation outcomes

- **No PK violations.** `card.card_token` unique. `transaction.id` unique. `(cost_line, fixed_or_variable, transaction_cost_type, cost_region)` unique in `cost_structure`. `rates.code` unique.
- **FK integrity OK.** Every `transaction.card_token` exists in `card`; every `(transaction_cost_type, cost_region)` combination has a matching cost_structure row.
- **3 currencies missing GBP rate**: BYR (Belarusian Ruble), ZMK (old Zambian Kwacha), SSP (South Sudanese Pound). No transactions in our data involve these currentices so they don't affect calculations.

### Activity findings

| Transaction state | Count | % |
|---|---:|---:|
| SUCCESS | 17,388 | 93.5% |
| FAIL | 1,208 | 6.5% |

| Card activity | Count | % |
|---|---:|---:|
| Cards with ≥1 SUCCESS transaction | 1,007 | 35% |
| Cards with FAIL only (no SUCCESS) | 62 | 2% |
| Cards with no transactions at all | **1,832** | **63%** |

**Most cards never transact.** 63% of the cards in the provided data have zero observable activity over Jan–Apr 2018. This shows that onboarded cards aren't converting to active users, which is the reason why we use **per-total-card** (not per-active-card) as the denominator for Q3 (inactive cards still count to customer acquisition efforts).

### Card cohort distribution

| Production cohort (month produced) | Approx cards |
|---|---:|
| Pre-2018 (Oct–Dec 2017) | ~27 |
| Jan 2018 | ~1,055 |
| Feb 2018 | ~775 |
| Mar 2018 | ~610 |
| Apr 2018 | ~434 |

(Exact distribution in [`notebooks/02_exploration.ipynb`](notebooks/02_exploration.ipynb) §2.)

The skew matters for LTV: with most cards produced late in the window, only a small handful are observable at higher tenures (T=3 has 284 at-risk cards globally; T=4 cliffs to 27). This drives the LTV anchor choice.

---

## Analysis

### Q1 — Average profit per transaction type

The card book is loss-making at the unit level — net 4-month P&L is **−£1,490**. (**purchases earn ~£900; cash withdrawals cost ~£2,400.**)

#### By transaction type

| Transaction type | n | Avg profit/tx | 4-month total |
|---|---:|---:|---:|
| ECOM_PURCHASE | 2,790 | **+£0.21** | +£575 |
| POS_PURCHASE | 13,029 | **+£0.03** | +£322 |
| CASH_WITHDRAWAL | 1,569 | **−£1.52** | −£2,386 |
| **Total** | **17,388** | **−£0.09** | **−£1,490** |

#### By (cost type × cost region) — avg profit/tx in GBP

| | Domestic | Intra | Inter |
|---|---:|---:|---:|
| **POS/ECOM** (n = 15,819) | +£0.06 (n=3,884) | +£0.15 (n=3,072) | +£0.02 (n=8,863) |
| **ATM** (n = 1,569) | −£0.34 (n=216) | **−£2.31** (n=260) | −£1.57 (n=1,093) |

The structural picture:

- **POS/ECOM cells are all positive.** Purchases earn money, expected.
- **ATM cells are all negative.** ATM Intra is the worst per-tx (−£2.31); ATM Inter has the largest impact due to volume of transactions (~−£1,710).
- **POS/ECOM Inter** (the biggest single cell at 8,863 transactions) is only just positive (+£0.02/tx). The 1.17% scheme variable rate eats most of the per-row interchange + conversion margin.

#### What drives revenue vs cost

| Component | Sign | Magnitude | Source |
|---|---|---|---|
| Per-row interchange | + for POS/ECOM, − for ATM | scales with transaction size | `transaction.inter_change_fee` |
| Conversion revenue | usually + in real data | ~2% of cross-currency billing | derived `billing_in_gbp − amount_in_gbp` |
| Fixed cost | − | ~£0.06/tx (Scheme + Issuer + Processing) | `cost_structure` Fixed lines |
| Variable rate | depends on cell | Inter ATM +1.37%, POS/ECOM Inter −0.03% | `cost_structure` Variable lines |

#### Methodology choices

- **Variable cost basis = `amount_in_gbp`**, per the brief's explicit statement.
- **Interchange:** Per-row IC in the transactions sheet and the cost_structure Interchange line treated as **two distinct flows**.
- **Conversion revenue** is derived, but mildly *negative* on aggregate in this dataset. This might be because the rates table is a single snapshot and doesn't match the rate Wise actually quoted at each transaction time, or that the assumed conversion revenue formula is inaccurate. Flagged on the Q1 slide.

---

### Q2 — 12-month LTV per card

Central estimate **−£5 per card per year**. Sensitivity band: **−£4 to −£11**.

#### Method

For each tenure month T from 0 to 11:

```
expected_profit_per_card(T) = transactor_share(T) × profit_per_transactor(T)
LTV = sum over T = 0..11
```

- **T = 0..3**: use observed values directly (≥284 at-risk cards at T=3).
- **T = 4..11**: extrapolate. Transactor share decays at 10%/month from T=3; profit-per-transactor held at the mean of T=1..T=3.

#### Sensitivity grid

| attrition | mean post-M0 |
|---|---:|
| 0% | −£6.98 | 
| 5% | −£5.96 | 
| **10%** (default) | **−£5.16** | 
| 15% | −£4.53 | 
| 20% | −£4.03 |

#### Caveats (Q2)

1. **No-churn measurement.** All 2,901 cards have `is_active = True`. The LTV *assumes* attrition (10% default) rather than measures it.
2. **4-month observation forces extrapolation.** Tenures T=4..T=11 are projected, not observed; the sensitivity band brackets the plausible range.
3. **Calendar-month M0 deflation.** First-month transactor share (16%) is artificially low because cards produced late in their calendar month have few observable days. Bounded to M0.
4. **Cohort composition at T=3.** The anchor is ~90% Jan 2018 cards.

---

### Q3 — Market performance and growth

**No market has demonstrated profitability with statistical confidence.** 5 markets show positive 4-month profit/card on point estimate (DK, ES, CH, IT, HU) but bootstrap CIs span zero for all of them. 6 markets are statistically loss-making (CI entirely below zero): **BE, GB, PT, FR, NL, EE**.

#### Full market scorecard (all 33 markets, sorted by `n_cards`)

| Market | n_cards | n_active | %active | tx/active | avg_bill £ | profit/card £ | %Inter | %ATM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GB | 1,507 | 462 | 31% | 17.6 | 33.3 | **−0.47** | 47% | 11% |
| DE | 237 | 78 | 33% | 9.7 | 37.2 | −0.62 | 60% | 13% |
| FR | 138 | 58 | 42% | 11.3 | 56.9 | **−1.40** | 62% | 12% |
| CH | 124 | 53 | 43% | 14.3 | 47.9 | +0.40 | 49% | 6% |
| ES | 122 | 51 | 42% | 12.3 | 48.6 | +0.42 | 65% | 11% |
| HU | 93 | 36 | 39% | 20.0 | 18.2 | +0.15 | 71% | 6% |
| NL | 81 | 32 | 40% | 7.4 | 40.6 | **−1.41** | 44% | 15% |
| EE | 66 | 37 | 56% | 54.2 | 15.1 | **−3.09** | 73% | 3% |
| IT | 64 | 19 | 30% | 18.2 | 43.3 | +0.37 | 89% | 5% |
| IE | 59 | 23 | 39% | 22.8 | 22.4 | −0.42 | 57% | 5% |
| PT | 54 | 18 | 33% | 8.0 | 37.3 | **−0.97** | 92% | 22% |
| CZ | 54 | 23 | 43% | 13.3 | 33.7 | −0.40 | 75% | 14% |
| SE | 43 | 20 | 47% | 23.9 | 22.2 | −0.89 | 73% | 6% |
| RO | 37 | 15 | 41% | 17.5 | 30.7 | −1.59 | 51% | 11% |
| DK | 32 | 12 | 38% | 27.3 | 25.5 | +0.51 | 42% | 2% |
| BE | 31 | 5 | 16% | 5.6 | 29.5 | **−0.42** | 82% | 14% |
| PL | 27 | 15 | 56% | 19.5 | 24.3 | −1.03 | 93% | 4% |
| NO | 23 | 10 | 43% | 13.1 | 27.8 | −0.90 | 82% | 10% |
| AT | 23 | 5 | 22% | 22.8 | 16.8 | +0.10 | 75% | 3% |
| SK | 17 | 5 | 29% | 21.0 | 12.6 | +0.37 | 82% | 3% |
| MT | 16 | 8 | 50% | 7.4 | 51.6 | −0.34 | 92% | 17% |
| FI | 15 | 9 | 60% | 19.0 | 14.9 | +2.68 | 47% | 6% |
| CY | 10 | 1 | 10% | 2.0 | 101.2 | −0.17 | 0% | 0% |
| HR | 6 | 4 | 67% | 4.0 | 13.1 | −0.12 | 75% | 13% |
| LV | 5 | 2 | 40% | 9.5 | 12.4 | −0.17 | 53% | 5% |
| SI | 3 | 1 | 33% | 57.0 | 12.7 | −2.02 | 100% | 16% |
| LT | 3 | 2 | 67% | 13.5 | 18.7 | −0.22 | 22% | 4% |
| GR | 3 | 1 | 33% | 4.0 | 8.4 | +0.28 | 75% | 0% |
| BG | 3 | 0 | 0% | — | — | 0.00 | — | — |
| SG | 2 | 0 | 0% | — | — | 0.00 | — | — |
| PA | 1 | 1 | 100% | 29.0 | 563.2 | **−55.03** | 55% | 55% |
| US | 1 | 1 | 100% | 32.0 | 23.8 | +2.69 | 53% | 3% |
| GI | 1 | 0 | 0% | — | — | 0.00 | — | — |

**Bold** profit/card values are statistically loss-making at 95% (CI entirely below 0); see CI table below.

#### Bootstrap 95% CIs (markets with ≥30 cards, our reliability threshold)

| Market | n | mean profit/card | 95% CI | Statistical call |
|---|---:|---:|---|---|
| DK | 32 | +0.51 | [−0.42, +1.67] | spans 0 |
| ES | 122 | +0.42 | [−0.90, +1.99] | spans 0 |
| CH | 124 | +0.40 | [−0.27, +1.07] | spans 0 |
| IT | 64 | +0.37 | [−0.64, +1.84] | spans 0 |
| HU | 93 | +0.15 | [−0.72, +0.83] | spans 0 |
| CZ | 54 | −0.40 | [−1.02, +0.09] | spans 0 |
| IE | 59 | −0.42 | [−0.92, +0.02] | spans 0 |
| **BE** | 31 | −0.42 | [−1.10, **−0.01**] | **loss-making** |
| **GB** | 1,507 | −0.47 | [−0.73, **−0.23**] | **loss-making** |
| DE | 237 | −0.62 | [−1.32, +0.05] | spans 0 |
| SE | 43 | −0.89 | [−2.17, +0.28] | spans 0 |
| **PT** | 54 | −0.97 | [−1.92, **−0.30**] | **loss-making** |
| **FR** | 138 | −1.40 | [−2.81, **−0.34**] | **loss-making** |
| **NL** | 81 | −1.41 | [−3.44, **−0.08**] | **loss-making** |
| RO | 37 | −1.59 | [−4.51, +0.27] | spans 0 |
| **EE** | 66 | −3.09 | [−5.60, **−1.02**] | **loss-making** |

#### What drives per-card outcomes

Under the I3 profit model, **Inter-region share is no longer the lever** it appears to be under the per-row-only interpretation (card-weighted Pearson(Inter%, profit/card) ≈ −0.02 in our scorecard). The lever that survives is **transaction frequency × ticket size × ATM share**. EE's deep loss comes from very high frequency (54 tx per active card per 4 months) on slightly loss-making transactions; HU achieves similar frequency at much smaller ticket sizes in slightly positive cells, staying near breakeven.

#### Recommendations (focus: ≥30 cards, statistically defensible)

**1. Fix Great Britain.** GB is statistically loss-making (n=1,507, CI [−0.73, −0.23]) with the narrowest CI in the book. 52% of the issued cards; observed loss −£0.47/card; 12-month LTV around −£4.40. Action: segment GB customers by behaviour, identify the slice driving the loss, push card-on-file with UK merchants. A 100 cards/mo EE-style → GB-style reallocation = ~£262/mo loss reduction.

**2. Validate Hungary's persona.** HU shows +£0.15/card at 71% Inter share — the most mission-aligned market that doesn't lose money on a point estimate. CI [−0.72, +0.83] spans zero, so it's not yet *statistically* profitable. Action: profile the HU customer (MCC, ticket size, cadence), test the persona in CZ / RO / PL where Wise has thin penetration, and add 100+ more HU cards to tighten the CI.

**What we deliberately don't recommend:** exiting markets with thin samples (4-month window too short for a structural call), filtering cash-heavy users (anti-customer-driven), or recommending against Inter-region usage (cross-border IS the product).

#### 2018 → today cross-check

- **Free-ATM monthly cap + per-withdrawal fee beyond it.** Wise shipped this post-2018 (current US: $250/mo free, then $1.95 + 1.95%). Validates the ATM-loss-centre finding; contradicts a purist "no hidden fees" rejection of the fix.
- **Card scaled from 2,901 (2018) → 1.6M (IPO July 2021).** Fixed-cost amortisation at volume changes the structural math.
- **Hungary was a strategic priority** — Wise's first direct EU payment-infrastructure integration was with the Hungarian Central Bank (settlement account, GIRO clearing, Qvik instant payments). External validation that HU is a meaningful market for Wise — for reasons beyond what the 2018 sample shows.

#### Caveats (Q3)

- **Per-card denominator is per-total-card** (not per-active-card). Matches the acquisition question — if you onboard 1,000 GB cards and 690 of them don't transact, the per-card profit reflects that drag.
- **4-month observation window** is too short to call any market "profitable" with statistical confidence.
- **No-churn measurement** — `is_active = True` for every card.
