-- clean_transactions: typed view over the raw transaction table with GBP
-- conversions joined in. FAIL rows are kept and filtered in the notebooks

SELECT
    t.id,
    t.transaction_time,
    CAST(t.transaction_time AS DATE) AS transaction_date,
    t.card_token,
    t.merchant_address_country,
    t.cost_region,
    t.transaction_type,
    t.transaction_cost_type,
    t.state,
    t.decline_reason,
    t.amount_currency,
    t.amount_value,
    t.billing_amount_currency,
    t.billing_amount_value,
    t.interchange_currency,
    t.inter_change_fee,
    t.merchant_name,
    t.category,
    t.amount_value * r_amt.rate_compared_to_gbp AS amount_in_gbp,
    t.billing_amount_value * r_bill.rate_compared_to_gbp AS billing_in_gbp,
    t.inter_change_fee * r_ic.rate_compared_to_gbp AS interchange_in_gbp,
    (t.amount_currency <> t.billing_amount_currency) AS is_cross_currency
FROM transaction t
LEFT JOIN rates r_amt ON t.amount_currency = r_amt.code
LEFT JOIN rates r_bill ON t.billing_amount_currency = r_bill.code
LEFT JOIN rates r_ic ON t.interchange_currency = r_ic.code
