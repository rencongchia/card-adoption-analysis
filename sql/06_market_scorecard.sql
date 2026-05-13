-- market_scorecard: one row per profile_address_country with the KPIs needed for Q3.
--
-- Metrics:
--   n_cards                   total cards in the market
--   pct_active                share of cards with ≥1 SUCCESS tx
--   tx_per_active_card        avg # of SUCCESS tx per active card (over the 4-month window)
--   avg_billing_gbp           avg per-tx billing in GBP
--   observed_profit_per_card  total SUCCESS-tx profit / n_cards (over the 4-month window)
--   pct_{domestic,intra,inter}    region mix of SUCCESS tx
--   pct_{pos,ecom,atm}            channel mix of SUCCESS tx
--   fail_pct                  decline rate over all tx (SUCCESS + FAIL)

WITH market_cards AS (
    SELECT cc.profile_address_country AS market,
           COUNT(*) AS n_cards
    FROM card_cohort cc
    GROUP BY cc.profile_address_country
),
market_success AS (
    SELECT cc.profile_address_country AS market,
           COUNT(*) AS n_success_tx,
           COUNT(DISTINCT ppt.card_token) AS n_active_cards,
           AVG(ppt.billing_in_gbp) AS avg_billing_gbp,
           SUM(ppt.profit_gbp) AS total_profit_gbp,
           AVG(ppt.profit_gbp) AS avg_profit_per_tx_gbp,
           AVG(CASE WHEN ppt.cost_region = 'Inter' THEN 1.0 ELSE 0 END) AS pct_inter,
           AVG(CASE WHEN ppt.cost_region = 'Domestic' THEN 1.0 ELSE 0 END) AS pct_domestic,
           AVG(CASE WHEN ppt.cost_region = 'Intra' THEN 1.0 ELSE 0 END) AS pct_intra,
           AVG(CASE WHEN ppt.transaction_type = 'CASH_WITHDRAWAL' THEN 1.0 ELSE 0 END) AS pct_atm,
           AVG(CASE WHEN ppt.transaction_type = 'POS_PURCHASE' THEN 1.0 ELSE 0 END) AS pct_pos,
           AVG(CASE WHEN ppt.transaction_type = 'ECOM_PURCHASE' THEN 1.0 ELSE 0 END) AS pct_ecom
    FROM profit_per_transaction ppt
    JOIN card_cohort cc USING (card_token)
    GROUP BY cc.profile_address_country
),
market_fail AS (
    SELECT cc.profile_address_country AS market,
           SUM(CASE WHEN ct.state = 'FAIL' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS fail_pct,
           COUNT(*) AS n_total_tx
    FROM clean_transactions ct
    JOIN card_cohort cc USING (card_token)
    GROUP BY cc.profile_address_country
)
SELECT
    mc.market,
    mc.n_cards,
    COALESCE(ms.n_active_cards, 0) AS n_active_cards,
    COALESCE(1.0 * ms.n_active_cards / mc.n_cards, 0) AS pct_active,
    COALESCE(ms.n_success_tx, 0) AS n_success_tx,
    COALESCE(ms.n_success_tx * 1.0 / NULLIF(ms.n_active_cards, 0), 0) AS tx_per_active_card,
    ms.avg_billing_gbp,
    ms.avg_profit_per_tx_gbp,
    COALESCE(ms.total_profit_gbp, 0) / mc.n_cards AS observed_profit_per_card_gbp,
    ms.pct_inter,
    ms.pct_domestic,
    ms.pct_intra,
    ms.pct_atm,
    ms.pct_pos,
    ms.pct_ecom,
    mf.fail_pct,
    mf.n_total_tx
FROM market_cards mc
LEFT JOIN market_success ms USING (market)
LEFT JOIN market_fail mf USING (market)
ORDER BY mc.n_cards DESC
