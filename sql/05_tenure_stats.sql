-- tenure_stats: per-tenure-month observation table.
--
-- Tenure is bucketed by CALENDAR MONTH. Tenure T = `cohort_month + T` calendar months.
--
-- A card is "at risk" at tenure T iff `cohort_month + T` falls inside the
-- transaction observation period (Jan-Apr 2018). Cards produced outside that
-- observable range for tenure T are excluded from both numerator and denominator
-- at that T.
--
-- A card is "transacting" at tenure T iff it had >=1 SUCCESS transaction in the
-- calendar month `cohort_month + T`.

WITH window_bounds AS (
    SELECT DATE_TRUNC('month', min(transaction_date)) AS tx_min_month,
           DATE_TRUNC('month', max(transaction_date)) AS tx_max_month
    FROM clean_transactions
),
tenure_grid AS (
    SELECT unnest([0,1,2,3,4,5,6]) AS month_since_issuance
),
at_risk AS (
    SELECT
        cc.card_token,
        cc.profile_address_country,
        cc.cohort_month,
        tg.month_since_issuance
    FROM card_cohort cc
    CROSS JOIN tenure_grid tg
    CROSS JOIN window_bounds wb
    WHERE DATEDIFF('month', cc.cohort_month, wb.tx_min_month) <= tg.month_since_issuance
      AND DATEDIFF('month', cc.cohort_month, wb.tx_max_month) >= tg.month_since_issuance
),
card_monthly_profit AS (
    SELECT
        ppt.card_token,
        DATEDIFF('month',
                 cc.cohort_month,
                 DATE_TRUNC('month', ppt.transaction_date))  AS month_since_issuance,
        SUM(ppt.profit_gbp) AS monthly_profit_gbp,
        COUNT(*) AS tx_count
    FROM profit_per_transaction ppt
    JOIN card_cohort cc USING (card_token)
    GROUP BY ppt.card_token,
             DATEDIFF('month',
                      cc.cohort_month,
                      DATE_TRUNC('month', ppt.transaction_date))
)
SELECT
    ar.month_since_issuance,
    COUNT(DISTINCT ar.card_token) AS cohort_at_risk,
    COUNT(DISTINCT cmp.card_token) AS transacting_cards,
    1.0 * COUNT(DISTINCT cmp.card_token) / COUNT(DISTINCT ar.card_token) AS transactor_share,
    AVG(cmp.monthly_profit_gbp) AS profit_per_transactor_gbp,
    AVG(cmp.tx_count) AS tx_per_transactor
FROM at_risk ar
LEFT JOIN card_monthly_profit cmp
  ON ar.card_token = cmp.card_token
 AND ar.month_since_issuance = cmp.month_since_issuance
GROUP BY ar.month_since_issuance
ORDER BY ar.month_since_issuance
