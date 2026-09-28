-- On the ledger, not on the statement, not part of an amount break.
-- Negative: payment sent, bank has not taken it.
-- Positive: receipt booked, bank has not cleared it.
SELECT line_date, ref, description, amount_eur
FROM v_gl_open
ORDER BY amount_eur;
