PRAGMA foreign_keys = ON;

-- Two lists of the same cash account. Positive amount is money in.
-- The reconciliation rediscovers which lines agree. Nothing in the tables
-- stores the answer.

CREATE TABLE gl_lines (
  id INTEGER PRIMARY KEY,
  line_date TEXT NOT NULL,
  ref TEXT,
  description TEXT NOT NULL,
  amount_eur INTEGER NOT NULL
);

CREATE TABLE bank_lines (
  id INTEGER PRIMARY KEY,
  line_date TEXT NOT NULL,
  ref TEXT,
  description TEXT NOT NULL,
  amount_eur INTEGER NOT NULL
);

-- Same reference, same amount. One row on each side.
CREATE VIEW v_exact AS
SELECT
  g.id AS gl_id,
  b.id AS bank_id,
  g.line_date AS gl_date,
  b.line_date AS bank_date,
  g.ref,
  g.description,
  g.amount_eur
FROM gl_lines g
JOIN bank_lines b
  ON g.ref = b.ref
 AND g.ref IS NOT NULL
 AND g.amount_eur = b.amount_eur;

-- Same reference, different amount. A keying error, not a timing item.
CREATE VIEW v_amount_break AS
SELECT
  g.id AS gl_id,
  b.id AS bank_id,
  g.line_date,
  g.ref,
  g.description AS gl_description,
  b.description AS bank_description,
  g.amount_eur AS gl_amount_eur,
  b.amount_eur AS bank_amount_eur,
  g.amount_eur - b.amount_eur AS difference_eur
FROM gl_lines g
JOIN bank_lines b
  ON g.ref = b.ref
 AND g.ref IS NOT NULL
 AND g.amount_eur <> b.amount_eur;

-- No shared reference. Same amount, dates within two days, and the line
-- was not already matched on reference. Amounts in this set are unique,
-- so the join cannot fan out.
CREATE VIEW v_date_match AS
SELECT
  g.id AS gl_id,
  b.id AS bank_id,
  g.line_date AS gl_date,
  b.line_date AS bank_date,
  g.ref AS gl_ref,
  b.ref AS bank_ref,
  g.description,
  g.amount_eur
FROM gl_lines g
JOIN bank_lines b
  ON g.amount_eur = b.amount_eur
 AND ABS(julianday(g.line_date) - julianday(b.line_date)) <= 2
 AND (g.ref IS NULL OR b.ref IS NULL OR g.ref <> b.ref)
WHERE g.id NOT IN (SELECT gl_id FROM v_exact)
  AND b.id NOT IN (SELECT bank_id FROM v_exact)
  AND g.id NOT IN (SELECT gl_id FROM v_amount_break)
  AND b.id NOT IN (SELECT bank_id FROM v_amount_break);

CREATE VIEW v_gl_open AS
SELECT g.*
FROM gl_lines g
WHERE g.id NOT IN (SELECT gl_id FROM v_exact)
  AND g.id NOT IN (SELECT gl_id FROM v_date_match)
  AND g.id NOT IN (SELECT gl_id FROM v_amount_break);

CREATE VIEW v_bank_open AS
SELECT b.*
FROM bank_lines b
WHERE b.id NOT IN (SELECT bank_id FROM v_exact)
  AND b.id NOT IN (SELECT bank_id FROM v_date_match)
  AND b.id NOT IN (SELECT bank_id FROM v_amount_break);
