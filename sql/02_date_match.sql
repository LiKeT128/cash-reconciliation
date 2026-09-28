-- Same amount, dates within two days, reference missing or different.
-- Used only for lines the exact match did not already take.
SELECT gl_date, bank_date, gl_ref, bank_ref, description, amount_eur
FROM v_date_match
ORDER BY gl_date;
