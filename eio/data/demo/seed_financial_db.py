"""
Financial Demo Database Seeder
================================
Creates and seeds the SQLite demo database with realistic
multi-year financial data for three fictional companies.

Tables:
  companies       — company master data
  revenue         — quarterly revenue by product line
  expenses        — quarterly operating expenses by category
  quarterly_results — aggregated P&L per quarter per company

Run directly:  python -m eio.data.demo.seed_financial_db
Or called automatically at API startup.
"""

from __future__ import annotations

import os
import random
import sqlite3
from pathlib import Path

_DB_PATH = os.getenv("EIO_SQLITE_PATH", "eio/data/demo/financial.db")
_SEED = 42  # deterministic data generation


def seed(db_path: str = _DB_PATH, force: bool = False) -> None:
    """
    Create and seed the financial demo database.
    Skips if the database already exists and force=False.
    """
    path = Path(db_path)
    if path.exists() and not force:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(_SEED)

    with sqlite3.connect(db_path) as conn:
        _create_tables(conn)
        _seed_companies(conn)
        _seed_financials(conn, rng)
        conn.commit()
    print(f"[EIO] Demo database seeded at {db_path}")


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    DROP TABLE IF EXISTS quarterly_results;
    DROP TABLE IF EXISTS revenue;
    DROP TABLE IF EXISTS expenses;
    DROP TABLE IF EXISTS companies;

    CREATE TABLE companies (
        id          INTEGER PRIMARY KEY,
        ticker      TEXT NOT NULL UNIQUE,
        name        TEXT NOT NULL,
        sector      TEXT NOT NULL,
        founded     INTEGER,
        hq_city     TEXT
    );

    CREATE TABLE revenue (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id  INTEGER NOT NULL REFERENCES companies(id),
        year        INTEGER NOT NULL,
        quarter     INTEGER NOT NULL CHECK(quarter BETWEEN 1 AND 4),
        product_line TEXT NOT NULL,
        amount      REAL NOT NULL,
        currency    TEXT DEFAULT 'USD'
    );

    CREATE TABLE expenses (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id  INTEGER NOT NULL REFERENCES companies(id),
        year        INTEGER NOT NULL,
        quarter     INTEGER NOT NULL CHECK(quarter BETWEEN 1 AND 4),
        category    TEXT NOT NULL,
        amount      REAL NOT NULL,
        currency    TEXT DEFAULT 'USD'
    );

    CREATE TABLE quarterly_results (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id      INTEGER NOT NULL REFERENCES companies(id),
        year            INTEGER NOT NULL,
        quarter         INTEGER NOT NULL CHECK(quarter BETWEEN 1 AND 4),
        total_revenue   REAL NOT NULL,
        total_expenses  REAL NOT NULL,
        gross_profit    REAL GENERATED ALWAYS AS (total_revenue - total_expenses) VIRTUAL,
        gross_margin    REAL GENERATED ALWAYS AS (
                            CASE WHEN total_revenue > 0
                            THEN ROUND((total_revenue - total_expenses) / total_revenue * 100, 2)
                            ELSE 0 END
                        ) VIRTUAL,
        yoy_growth_pct  REAL,
        ebitda          REAL
    );
    """)


def _seed_companies(conn: sqlite3.Connection) -> None:
    companies = [
        (1, "APEX", "Apex Analytics Corp", "Technology", 2010, "San Francisco"),
        (2, "NOVA", "Nova Financial Systems", "Financial Services", 2005, "New York"),
        (3, "CREST", "Crest Manufacturing Ltd", "Industrials", 1998, "Chicago"),
    ]
    conn.executemany(
        "INSERT INTO companies VALUES (?, ?, ?, ?, ?, ?)", companies
    )


def _seed_financials(conn: sqlite3.Connection, rng: random.Random) -> None:
    product_lines = {
        1: ["Cloud Platform", "Analytics Suite", "Professional Services", "Licensing"],
        2: ["Investment Banking", "Asset Management", "Retail Banking", "Insurance"],
        3: ["Equipment Sales", "Maintenance Contracts", "Parts & Components", "Installation"],
    }
    expense_categories = ["R&D", "Sales & Marketing", "G&A", "COGS", "Operations"]

    revenue_rows = []
    expense_rows = []
    result_rows = []

    # Base revenues (millions USD) and annual growth rates per company
    base_rev = {1: 120.0, 2: 350.0, 3: 180.0}
    growth = {1: 0.22, 2: 0.08, 3: 0.05}          # annual YoY growth
    seasonality = {1: 0.9, 2: 1.15, 3: 1.0, 4: 1.3}  # Q4 strong

    for company_id in [1, 2, 3]:
        for year_offset, year in enumerate([2021, 2022, 2023]):
            for q in [1, 2, 3, 4]:
                # Total revenue for this quarter
                annual_rev = base_rev[company_id] * ((1 + growth[company_id]) ** year_offset)
                quarterly_rev = (annual_rev / 4) * seasonality[q]
                # Add slight noise
                quarterly_rev *= rng.uniform(0.94, 1.06)

                # Split across product lines
                lines = product_lines[company_id]
                weights = [rng.uniform(0.1, 0.5) for _ in lines]
                total_w = sum(weights)
                for i, line in enumerate(lines):
                    amount = round(quarterly_rev * (weights[i] / total_w), 2)
                    revenue_rows.append((company_id, year, q, line, amount, "USD"))

                # Total expenses (60-70% of revenue)
                expense_ratio = rng.uniform(0.60, 0.70)
                total_expenses = round(quarterly_rev * expense_ratio, 2)

                # Split across expense categories
                exp_weights = [rng.uniform(0.05, 0.40) for _ in expense_categories]
                total_ew = sum(exp_weights)
                for i, cat in enumerate(expense_categories):
                    amount = round(total_expenses * (exp_weights[i] / total_ew), 2)
                    expense_rows.append((company_id, year, q, cat, amount, "USD"))

                # Quarterly results
                total_rev = round(quarterly_rev, 2)
                ebitda = round(total_rev - total_expenses * 0.75, 2)  # EBITDA excludes D&A

                # YoY growth (only for 2022+)
                yoy = None
                if year_offset > 0:
                    prior_rev = base_rev[company_id] * ((1 + growth[company_id]) ** (year_offset - 1))
                    prior_quarterly = (prior_rev / 4) * seasonality[q]
                    yoy = round((total_rev - prior_quarterly) / prior_quarterly * 100, 2)

                result_rows.append((company_id, year, q, total_rev, total_expenses, yoy, ebitda))

    conn.executemany(
        "INSERT INTO revenue (company_id, year, quarter, product_line, amount, currency) VALUES (?,?,?,?,?,?)",
        revenue_rows,
    )
    conn.executemany(
        "INSERT INTO expenses (company_id, year, quarter, category, amount, currency) VALUES (?,?,?,?,?,?)",
        expense_rows,
    )
    conn.executemany(
        "INSERT INTO quarterly_results (company_id, year, quarter, total_revenue, total_expenses, yoy_growth_pct, ebitda) "
        "VALUES (?,?,?,?,?,?,?)",
        result_rows,
    )


if __name__ == "__main__":
    seed(force=True)
