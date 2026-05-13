-- profit_per_transaction: canonical per-transaction P&L. The single source of truth that
-- Q1 (unit economics), Q2 (LTV), and Q3 (markets) all build on.

SELECT
    t.id,
    t.card_token,
    t.transaction_date,
    t.transaction_time,
    t.transaction_type,
    t.transaction_cost_type,
    t.cost_region,
    t.merchant_address_country,
    t.amount_currency,
    t.amount_value,
    t.billing_amount_currency,
    t.billing_amount_value,
    t.amount_in_gbp,
    t.billing_in_gbp,
    t.is_cross_currency,
    t.interchange_in_gbp AS interchange_revenue_gbp,
    CASE WHEN t.is_cross_currency
         THEN t.billing_in_gbp - t.amount_in_gbp
         ELSE 0 END AS conversion_revenue_gbp,
    c.fixed_cost_gbp,
    t.amount_in_gbp * c.variable_rate AS variable_cost_gbp,
    (
        t.interchange_in_gbp
        + CASE WHEN t.is_cross_currency
               THEN t.billing_in_gbp - t.amount_in_gbp
               ELSE 0 END
        - c.fixed_cost_gbp
        - (t.amount_in_gbp * c.variable_rate)
    ) AS profit_gbp
FROM clean_transactions t
LEFT JOIN cost_lookup c USING (transaction_cost_type, cost_region)
WHERE t.state = 'SUCCESS'
