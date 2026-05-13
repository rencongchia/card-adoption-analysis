-- cost_lookup: collapse cost_structure to one row per (transaction_cost_type, cost_region).

SELECT
    transaction_cost_type,
    cost_region,
    SUM(CASE WHEN fixed_or_variable = 'Fixed'
             THEN cost_in_gbp END) AS fixed_cost_gbp,
    SUM(CASE WHEN fixed_or_variable = 'Variable'
             THEN variable_fee END) AS variable_rate
FROM cost_structure
GROUP BY transaction_cost_type, cost_region
