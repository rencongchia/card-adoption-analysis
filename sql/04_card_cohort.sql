-- card_cohort: per-card attributes used by the LTV pipeline.
-- cohort_date is the calendar date the card was produced (the user's "day zero").

SELECT
    c.card_token,
    c.card_owner_id,
    c.card_produced_time,
    CAST(c.card_produced_time AS DATE)        AS cohort_date,
    DATE_TRUNC('month', c.card_produced_time) AS cohort_month,
    c.profile_address_country,
    c.age_years,
    c.email_domain,
    c.is_active
FROM card c
