-- Same reference, two amounts. Do not drop these into "timing".
SELECT line_date, ref, gl_description, gl_amount_eur, bank_amount_eur, difference_eur
FROM v_amount_break
ORDER BY ABS(difference_eur) DESC;
