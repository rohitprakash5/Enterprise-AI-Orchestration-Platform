"""Show full EIO database summary."""
import sys; sys.path.insert(0, ".")
from eio.connectors.databases.sqlite_connector import SQLiteConnector

db = SQLiteConnector("eio/data/demo/financial.db")
db.connect()

print("=== ANNUAL REVENUE BY COMPANY ===")
r = db.execute_query("""
    SELECT c.name, qr.year,
           ROUND(SUM(qr.total_revenue),2)  AS annual_rev_M,
           ROUND(SUM(qr.total_expenses),2) AS annual_exp_M,
           ROUND(SUM(qr.gross_profit),2)   AS annual_gp_M,
           ROUND(AVG(qr.yoy_growth_pct),1) AS avg_yoy_pct
    FROM quarterly_results qr
    JOIN companies c ON c.id = qr.company_id
    GROUP BY c.name, qr.year
    ORDER BY c.name, qr.year
""")
for row in r.rows:
    print(row)

print()
print("=== NOVA FINANCIAL quarterly_results ===")
r2 = db.execute_query("""
    SELECT qr.year, qr.quarter, qr.total_revenue, qr.total_expenses,
           qr.gross_profit, qr.gross_margin, qr.ebitda, qr.yoy_growth_pct
    FROM quarterly_results qr
    JOIN companies c ON c.id = qr.company_id
    WHERE c.name = 'Nova Financial Systems'
    ORDER BY qr.year, qr.quarter
""")
for row in r2.rows:
    print(row)

print()
print("=== DISTINCT PRODUCT LINES (revenue table) ===")
r3 = db.execute_query("""
    SELECT c.name, rv.product_line
    FROM revenue rv
    JOIN companies c ON c.id = rv.company_id
    GROUP BY c.name, rv.product_line
    ORDER BY c.name, rv.product_line
""")
for row in r3.rows:
    print(row)

print()
print("=== DISTINCT EXPENSE CATEGORIES ===")
r4 = db.execute_query("SELECT DISTINCT category FROM expenses ORDER BY category")
for row in r4.rows:
    print(" ", row)

print()
print("=== TABLE ROW COUNTS ===")
for t in ["companies", "quarterly_results", "revenue", "expenses"]:
    rc = db.execute_query(f"SELECT COUNT(*) AS cnt FROM {t}")
    print(f"  {t:<22} {rc.rows[0]['cnt']:>4} rows")
