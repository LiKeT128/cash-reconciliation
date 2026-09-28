-- Agreed lines. Same reference, same amount, both books.
SELECT ref, gl_date, bank_date, description, amount_eur
FROM v_exact
ORDER BY gl_date, ref;
