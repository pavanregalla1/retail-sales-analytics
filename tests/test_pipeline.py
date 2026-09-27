"""Real tests over actual pipeline outputs (data/gold/*.csv + data/dq_report.json).

Run after the pipeline (CI runs these steps in order):
    python3 etl/generate_data.py
    python3 etl/run_local.py
    python3 -m pytest tests/ -v
"""
import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(ROOT, "data", "gold")


def load(table):
    path = os.path.join(GOLD, f"{table}.csv")
    assert os.path.exists(path), f"missing gold table: {path}"
    return pd.read_csv(path)


def dq_report():
    path = os.path.join(ROOT, "data", "dq_report.json")
    assert os.path.exists(path), "missing data/dq_report.json — run etl/run_local.py first"
    with open(path) as f:
        return json.load(f)


def test_gold_tables_exist_and_nonempty():
    for t in ["dim_customer", "dim_product", "dim_date", "fact_orders",
              "mart_monthly_sales", "quarantine_orders"]:
        assert len(load(t)) > 0, f"{t} is empty"


def test_fact_orders_row_count():
    assert len(load("fact_orders")) == 56420


def test_total_revenue():
    rev = load("fact_orders")["line_total"].sum()
    assert abs(rev - 80961565.34) < 1.0, f"unexpected revenue {rev}"


def test_quarantine_count_matches_report():
    q = load("quarantine_orders")
    assert len(q) == 2113
    assert dq_report()["layers"]["gold_quarantine_orders"] == 2113
    assert "quarantine_reason" in q.columns


def test_dq_checks_all_pass():
    dq = dq_report()
    assert len(dq["checks"]) == 10
    failed = [c["check"] for c in dq["checks"] if not c["passed"]]
    assert not failed, f"DQ checks failed: {failed}"


def test_gold_schemas():
    expected = {
        "dim_customer": {"customer_id", "customer_name", "email", "segment",
                         "country", "city", "signup_date"},
        "dim_product": {"product_id", "product_name", "category", "unit_price"},
        "dim_date": {"date_key", "date", "year", "month", "month_name",
                     "quarter", "day_of_week"},
        "fact_orders": {"order_id", "order_date", "customer_id", "product_id",
                        "quantity", "unit_price", "discount", "line_total", "date_key"},
        "mart_monthly_sales": {"ym", "revenue", "orders", "units", "customers", "aov"},
    }
    for table, cols in expected.items():
        actual = set(load(table).columns)
        assert cols <= actual, f"{table} missing columns: {cols - actual}"


def test_referential_integrity():
    f = load("fact_orders")
    assert set(f["customer_id"]) <= set(load("dim_customer")["customer_id"])
    assert set(f["product_id"]) <= set(load("dim_product")["product_id"])
    assert set(f["date_key"]) <= set(load("dim_date")["date_key"])


def test_no_negative_revenue_or_quantity():
    f = load("fact_orders")
    assert (f["line_total"] >= 0).all()
    assert (f["quantity"] > 0).all()


def test_sample_data():
    s = pd.read_csv(os.path.join(ROOT, "sample_data", "orders_sample.csv"))
    assert len(s) == 500
    assert {"order_id", "order_date", "customer_id", "product_id",
            "quantity", "unit_price", "discount"} <= set(s.columns)
