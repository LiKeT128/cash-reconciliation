-- On the statement, not in the ledger.
-- Fees and interest usually land here. They still have to be booked.
SELECT line_date, ref, description, amount_eur
FROM v_bank_open
ORDER BY amount_eur;
