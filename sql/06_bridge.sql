-- Books to statement. Unexplained must be zero, or the lists are incomplete.
-- gl - bank = open ledger lines - open bank lines + amount-break difference.

SELECT
  (SELECT COALESCE(SUM(amount_eur), 0) FROM gl_lines) AS gl_balance,
  (SELECT COALESCE(SUM(amount_eur), 0) FROM bank_lines) AS bank_balance,
  (SELECT COALESCE(SUM(amount_eur), 0) FROM v_gl_open WHERE amount_eur < 0) AS outstanding_payments,
  (SELECT COALESCE(SUM(amount_eur), 0) FROM v_gl_open WHERE amount_eur > 0) AS deposits_in_transit,
  (SELECT COALESCE(SUM(amount_eur), 0) FROM v_bank_open WHERE amount_eur < 0) AS bank_charges,
  (SELECT COALESCE(SUM(amount_eur), 0) FROM v_bank_open WHERE amount_eur > 0) AS interest,
  (SELECT COALESCE(SUM(difference_eur), 0) FROM v_amount_break) AS amount_breaks,
  (SELECT COALESCE(SUM(amount_eur), 0) FROM gl_lines)
    - (SELECT COALESCE(SUM(amount_eur), 0) FROM bank_lines)
    - (SELECT COALESCE(SUM(amount_eur), 0) FROM v_gl_open)
    + (SELECT COALESCE(SUM(amount_eur), 0) FROM v_bank_open)
    - (SELECT COALESCE(SUM(difference_eur), 0) FROM v_amount_break) AS unexplained;
