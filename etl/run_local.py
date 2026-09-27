"""Medallion pipeline: raw CSVs -> bronze -> silver -> gold (star schema).

This is the locally-runnable version (pandas). notebooks/databricks_etl.py holds
the identical logic in PySpark for Databricks Runtime — same layers, same rules.
Run:  python3 etl/run_local.py
"""
import pandas as pd, numpy as np, os, json
from datetime import datetime

RAW, GOLD = "data/raw", "data/gold"
os.makedirs(GOLD, exist_ok=True)
dq = {"run_at": datetime.utcnow().isoformat()+"Z", "layers": {}, "checks": []}

def check(name, passed, detail=""):
    dq["checks"].append({"check": name, "passed": bool(passed), "detail": str(detail)})

# ---------------- BRONZE: ingest as-is + lineage ----------------
bronze = {}
for t in ["customers","products","orders"]:
    df = pd.read_csv(f"{RAW}/{t}.csv", dtype=str)
    df["_ingested_at"] = datetime.utcnow().isoformat()
    df["_source_file"] = f"{t}.csv"
    bronze[t] = df
    dq["layers"][f"bronze_{t}"] = len(df)
print("bronze:", {k: len(v) for k,v in bronze.items()})

# ---------------- SILVER: cleanse & conform ----------------
# customers: drop null emails, normalize country casing
cust = bronze["customers"].copy()
n0 = len(cust)
cust = cust[cust["email"].notna() & (cust["email"] != "")]
cust["country"] = cust["country"].str.strip().str.title().replace({"Usa":"USA"})
cust["signup_date"] = pd.to_datetime(cust["signup_date"], errors="coerce")
cust = cust.dropna(subset=["signup_date"]).drop_duplicates("customer_id")
check("customers_null_email_removed", True, f"removed={n0-len(cust)}")

# products: nothing dirty by design, just type it
prod = bronze["products"].copy()
prod["unit_price"] = pd.to_numeric(prod["unit_price"], errors="coerce")
prod = prod.dropna(subset=["unit_price"]).drop_duplicates("product_id")

# orders: dedupe, fix dates, drop bad quantities, enforce product FK
ord_ = bronze["orders"].copy()
n0 = len(ord_)
ord_ = ord_.drop_duplicates(subset=["order_id"], keep="first")
check("orders_duplicates_removed", True, f"removed={n0-len(ord_)}")
ord_["order_date"] = pd.to_datetime(ord_["order_date"], dayfirst=False, errors="coerce")
n1 = len(ord_)
ord_ = ord_.dropna(subset=["order_date"])
check("orders_bad_dates_removed", True, f"removed={n1-len(ord_)}")
ord_["quantity"] = pd.to_numeric(ord_["quantity"], errors="coerce")
ord_["unit_price"] = pd.to_numeric(ord_["unit_price"], errors="coerce")
ord_["discount"] = pd.to_numeric(ord_["discount"], errors="coerce").fillna(0)
n2 = len(ord_)
ord_ = ord_[ord_["quantity"] > 0]
check("orders_bad_quantity_removed", True, f"removed={n2-len(ord_)}")
n3 = len(ord_)
ord_ = ord_[ord_["product_id"].isin(set(prod["product_id"]))]
check("orders_orphan_fk_removed", True, f"removed={n3-len(ord_)}")
# quarantine: orders whose customer was cleansed out (null email) are NOT
# silently dropped — they land in a quarantine table for review
n4 = len(ord_)
valid_cust = set(cust["customer_id"])
quarantine = ord_[~ord_["customer_id"].isin(valid_cust)].copy()
quarantine["quarantine_reason"] = "customer cleansed out (null email)"
ord_ = ord_[ord_["customer_id"].isin(valid_cust)]
check("orders_quarantined_bad_customer", True, f"quarantined={n4-len(ord_)}")
quarantine.to_csv(f"{GOLD}/quarantine_orders.csv", index=False)
dq["layers"]["gold_quarantine_orders"] = len(quarantine)
ord_["line_total"] = (ord_["quantity"]*ord_["unit_price"]*(1-ord_["discount"])).round(2)

dq["layers"].update({f"silver_{k}": len(v) for k,v in
                     [("customers",cust),("products",prod),("orders",ord_)]})
print("silver:", {k: len(v) for k,v in [("customers",cust),("products",prod),("orders",ord_)]})
check("silver_no_null_keys", cust["customer_id"].notna().all() and ord_["order_id"].notna().all())

# ---------------- GOLD: star schema ----------------
dim_customer = cust[["customer_id","customer_name","email","segment","country","city","signup_date"]].copy()
dim_product  = prod[["product_id","product_name","category","unit_price"]].copy()
dates = pd.DataFrame({"date": pd.date_range(ord_["order_date"].min(), ord_["order_date"].max())})
dim_date = pd.DataFrame({
    "date_key": dates["date"].dt.strftime("%Y%m%d").astype(int),
    "date": dates["date"].dt.date.astype(str),
    "year": dates["date"].dt.year, "month": dates["date"].dt.month,
    "month_name": dates["date"].dt.strftime("%b"), "quarter": dates["date"].dt.quarter,
    "day_of_week": dates["date"].dt.day_name(),
})
fact_orders = ord_[["order_id","order_date","customer_id","product_id","quantity",
                    "unit_price","discount","line_total"]].copy()
fact_orders["date_key"] = pd.to_datetime(fact_orders["order_date"]).dt.strftime("%Y%m%d").astype(int)

# referential integrity: every fact key exists in its dimension
check("ri_customer", set(fact_orders["customer_id"]) <= set(dim_customer["customer_id"]))
check("ri_product",  set(fact_orders["product_id"])  <= set(dim_product["product_id"]))
check("ri_date",     set(fact_orders["date_key"])    <= set(dim_date["date_key"]))

for name, df in [("dim_customer",dim_customer),("dim_product",dim_product),
                 ("dim_date",dim_date),("fact_orders",fact_orders)]:
    df.to_csv(f"{GOLD}/{name}.csv", index=False)
    dq["layers"][f"gold_{name}"] = len(df)

# monthly KPI mart (feeds the dashboard directly)
m = fact_orders.copy()
m["ym"] = pd.to_datetime(m["order_date"]).dt.to_period("M").astype(str)
monthly = m.groupby("ym").agg(revenue=("line_total","sum"), orders=("order_id","nunique"),
                              units=("quantity","sum"),
                              customers=("customer_id","nunique")).reset_index()
monthly["aov"] = (monthly["revenue"]/monthly["orders"]).round(2)
monthly["revenue"] = monthly["revenue"].round(2)
monthly.to_csv(f"{GOLD}/mart_monthly_sales.csv", index=False)
dq["layers"]["gold_mart_monthly_sales"] = len(monthly)

with open("data/dq_report.json","w") as f: json.dump(dq, f, indent=2)
print("gold:", {k:v for k,v in dq["layers"].items() if k.startswith("gold")})
print("DQ checks:", sum(c["passed"] for c in dq["checks"]), "/", len(dq["checks"]), "passed")
print("total revenue: $", round(fact_orders["line_total"].sum(), 2))
