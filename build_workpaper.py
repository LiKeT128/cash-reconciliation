"""Build a June 2026 cash reconciliation and a one-page workpaper.

The books are fictional. The tie-out is not optional: unexplained must be 0.
"""

from __future__ import annotations

import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "cash.db"
REPORT_PATH = ROOT / "workpaper" / "index.html"
SCHEMA = (ROOT / "schema.sql").read_text(encoding="utf-8")


def euro(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}€{abs(amount):,}"


def build() -> sqlite3.Connection:
    rng = random.Random(19)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    gl: list[tuple] = []
    bank: list[tuple] = []
    reserved = {7770, 2460, 10000, 1000, 4200, 1800, 960, 5100, 2300, 35, 11}

    def add(side: list[tuple], date: str, ref: str | None, description: str, amount: int) -> None:
        side.append((date, ref, description, amount))

    for index in range(1, 33):
        amount = rng.randint(90, 3800)
        while amount in reserved:
            amount = rng.randint(90, 3800)
        reserved.add(amount)
        if rng.random() < 0.6:
            amount = -amount
        day = rng.randint(1, 24)
        ref = f"M-{index:03d}"
        description = "Supplier payment" if amount < 0 else "Customer receipt"
        add(gl, f"2026-06-{day:02d}", ref, description, amount)
        add(bank, f"2026-06-{day:02d}", ref, description, amount)

    # Reference missing on the statement. Amount and date still agree.
    add(gl, "2026-06-28", "DEP-441", "Customer receipt", 7770)
    add(bank, "2026-06-30", None, "Incoming payment", 7770)
    add(gl, "2026-06-29", "DEP-442", "Customer receipt", 2460)
    add(bank, "2026-06-30", None, "Incoming payment", 2460)

    # Sent or received in the books, not on the 30 June statement.
    add(gl, "2026-06-30", "PAY-901", "Supplier payment, sent 30 Jun", -4200)
    add(gl, "2026-06-29", "PAY-902", "Supplier payment, sent 29 Jun", -1800)
    add(gl, "2026-06-30", "PAY-903", "Supplier payment, sent 30 Jun", -960)
    add(gl, "2026-06-30", "DEP-901", "Customer receipt, lodged 30 Jun", 5100)
    add(gl, "2026-06-30", "DEP-902", "Customer receipt, lodged 30 Jun", 2300)

    # On the statement, not yet in the ledger.
    add(bank, "2026-06-30", "FEE-06", "Account maintenance", -35)
    add(bank, "2026-06-30", "INT-06", "Credit interest", 11)

    # Same reference, a zero dropped on the statement side.
    add(gl, "2026-06-14", "REC-77", "Card settlement", 10000)
    add(bank, "2026-06-14", "REC-77", "Card settlement", 1000)

    conn.executemany(
        "INSERT INTO gl_lines (line_date, ref, description, amount_eur) VALUES (?, ?, ?, ?)",
        gl,
    )
    conn.executemany(
        "INSERT INTO bank_lines (line_date, ref, description, amount_eur) VALUES (?, ?, ?, ?)",
        bank,
    )
    conn.commit()
    return conn


def rows(conn: sqlite3.Connection, name: str) -> list[sqlite3.Row]:
    sql = (ROOT / "sql" / name).read_text(encoding="utf-8")
    return list(conn.execute(sql))


def table(headers: list[str], records: list[list[str]]) -> str:
    head = "".join(f"<th>{header}</th>" for header in headers)
    body = []
    for record in records:
        body.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in record) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def render(conn: sqlite3.Connection) -> None:
    bridge = rows(conn, "06_bridge.sql")[0]
    exact = rows(conn, "01_exact.sql")
    dated = rows(conn, "02_date_match.sql")
    gl_open = rows(conn, "03_gl_open.sql")
    bank_open = rows(conn, "04_bank_open.sql")
    breaks = rows(conn, "05_amount_break.sql")

    if bridge["unexplained"] != 0:
        raise SystemExit(f"unexplained {bridge['unexplained']}")
    if len(dated) != 2 or len(breaks) != 1 or len(gl_open) != 5 or len(bank_open) != 2:
        raise SystemExit(
            f"counts exact={len(exact)} date={len(dated)} gl_open={len(gl_open)} "
            f"bank_open={len(bank_open)} breaks={len(breaks)}"
        )

    gl_balance = bridge["gl_balance"]
    bank_balance = bridge["bank_balance"]
    payments = bridge["outstanding_payments"]
    deposits = bridge["deposits_in_transit"]
    charges = bridge["bank_charges"]
    interest = bridge["interest"]
    amount_breaks = bridge["amount_breaks"]

    # Books to statement:
    # start at GL, remove open GL lines, add open bank lines, remove the break delta.
    check = gl_balance - (payments + deposits) + (charges + interest) - amount_breaks
    if check != bank_balance:
        raise SystemExit(f"bridge {check} != bank {bank_balance}")

    bridge_rows = [
        ["Balance per general ledger, 30 Jun 2026", euro(gl_balance), ""],
        ["Outstanding payments, on the books only", euro(-payments), "a"],
        ["Deposits in transit, on the books only", euro(-deposits), "b"],
        ["Bank charges not booked", euro(charges), "c"],
        ["Interest not booked", euro(interest), "c"],
        ["Card settlement REC-77, books minus statement", euro(-amount_breaks), "d"],
        ["Balance per bank statement, 30 Jun 2026", euro(bank_balance), ""],
        ["Unexplained", euro(0), ""],
    ]

    def money_rows(records: list[sqlite3.Row], columns: list[str]) -> list[list[str]]:
        out = []
        for record in records:
            line = []
            for column in columns:
                value = record[column]
                line.append(euro(value) if column.endswith("eur") or column.endswith("amount") or "amount" in column or column == "difference_eur" else (value or "—"))
            out.append(line)
        return out

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cash reconciliation · 30 June 2026</title>
  <style>
    body {{ margin: 0; background: #f7f7f5; color: #161616; font-family: "Segoe UI", sans-serif; }}
    main {{ width: min(880px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 64px; }}
    header {{ display: flex; justify-content: space-between; gap: 24px; border-bottom: 2px solid #161616; padding-bottom: 12px; }}
    h1 {{ font-size: 22px; margin: 0; font-weight: 650; }}
    h2 {{ font-size: 15px; margin: 28px 0 8px; }}
    p {{ margin: 4px 0; }}
    .meta {{ font-size: 13px; text-align: right; }}
    .nil {{ font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; margin-top: 14px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; font-size: 13px; font-variant-numeric: tabular-nums; }}
    th, td {{ border: 1px solid #d0d0d0; padding: 6px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #efefec; font-size: 11px; letter-spacing: 0.04em; text-transform: uppercase; }}
    td:last-child, .bridge td:nth-child(2) {{ text-align: right; font-family: Consolas, "Courier New", monospace; }}
    .bridge tr:last-child td {{ font-weight: 700; }}
    .bridge tr:nth-last-child(2) td {{ border-top: 2px solid #161616; }}
    footer {{ margin-top: 28px; font-size: 12px; color: #444; }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <p>Atelier Ledger s.r.o. · fictional</p>
      <h1>Cash reconciliation</h1>
      <p>Bank statement to the general ledger · 30 June 2026</p>
    </div>
    <div class="meta">
      <p>Workpaper C-1</p>
      <p>Prepared 2 July 2026</p>
      <p>Currency EUR</p>
    </div>
  </header>
  <p class="nil">Unexplained difference: nil</p>
  <h2>Bridge</h2>
  {table(["Line", "Amount", "Tick"], bridge_rows)}
  <h2>a–b · On the ledger, not on the statement</h2>
  {table(["Date", "Ref", "Description", "Amount"], money_rows(gl_open, ["line_date", "ref", "description", "amount_eur"]))}
  <p>Open ledger lines are listed once. Payments are negative, deposits in transit are positive. Tick b is the positive rows.</p>
  <h2>c · On the statement, not in the books · {euro(charges + interest)}</h2>
  {table(["Date", "Ref", "Description", "Amount"], money_rows(bank_open, ["line_date", "ref", "description", "amount_eur"]))}
  <h2>d · Same reference, different amount</h2>
  {table(["Date", "Ref", "Books", "Statement", "Difference"], money_rows(breaks, ["line_date", "ref", "gl_amount_eur", "bank_amount_eur", "difference_eur"]))}
  <h2>Agreed without a shared reference</h2>
  {table(["Ledger date", "Statement date", "Ledger ref", "Statement ref", "Amount"], money_rows(dated, ["gl_date", "bank_date", "gl_ref", "bank_ref", "amount_eur"]))}
  <p>{len(exact)} further lines agreed on reference and amount. They are in both balances and drop out of the bridge. Query: sql/01_exact.sql.</p>
  <footer>
    Matching rules are views in schema.sql. Exact reference, then amount-and-date within two days, then whatever is left.
    An amount break is not called a timing difference. The population is synthetic. The unexplained line is a check, not a label: if a line is missing from the lists, it stops being zero.
  </footer>
</main>
</body>
</html>
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(page, encoding="utf-8")
    print(
        f"gl={gl_balance} bank={bank_balance} payments={payments} deposits={deposits} "
        f"charges={charges} interest={interest} break={amount_breaks} exact={len(exact)} unexplained=0"
    )
    print(REPORT_PATH)


if __name__ == "__main__":
    connection = build()
    try:
        render(connection)
    finally:
        connection.close()
