# Retail Sales Analytics — End-to-End Data Pipeline

A complete, runnable analytics project: messy raw e-commerce data → cleansed
lakehouse → star-schema gold layer → KPI queries → Power BI dashboard spec.
Built to be talked through in interviews, not just listed on a resume.

## Architecture

```
data/raw/*.csv ──▶ BRONZE (as-is + _ingested_at, _source_file)
                        │ dedupe · fix dates · drop bad qtys · conform keys
                        ▼
                   SILVER (clean, typed, conformed)
                        │ quarantine bad-customer orders (not silent drops)
                        ▼
                   GOLD star schema ──▶ Power BI dashboards
                        ├── dim_customer / dim_product / dim_date
                        ├── fact_orders (56,420 rows, $80.96M)
                        ├── mart_monthly_sales (pre-aggregated KPIs)
                        └── quarantine_orders (2,113 rows, auditable)
```

## What's inside

| Folder | Contents |
|---|---|
| `etl/generate_data.py` | Builds the raw dataset (5,000 customers, 17 products, 60,600 orders) with realistic quality issues |
| `etl/run_local.py` | Full medallion pipeline, runnable with plain Python + pandas; **10/10 DQ checks pass** |
| `notebooks/databricks_etl.py` | Same pipeline in PySpark for Databricks Runtime (Delta Lake, Unity Catalog) |
| `sql/gold_models.sql` | Star-schema DDL |
| `sql/kpi_queries.sql` | 6 interview-ready KPI queries (MoM growth, repeat rate, cohorts…) |
| `powerbi/dashboard_spec.md` | 2-page dashboard layout + DAX measures |
| `docs/interview_talk_track.md` | How to explain this project in 2 minutes + likely Q&A |

## Run it

```bash
cd retail-sales-analytics
python3 etl/generate_data.py   # create raw data
python3 etl/run_local.py       # bronze → silver → gold, DQ report to data/dq_report.json
```

The Databricks notebook runs the identical logic on a real cluster — point the
`landing` volume at the raw CSVs and Run All.

## Key design decisions (say these in interviews)

1. **Quarantine, don't silently drop.** Orders referencing customers removed
   during cleansing go to `quarantine_orders` with a reason — auditable, recoverable.
2. **Pre-aggregated marts.** `mart_monthly_sales` feeds the executive dashboard
   so Page 1 stays instant at 100M+ row scale.
3. **DQ as a gate, not a report.** The Databricks job *fails* if any check
   breaks (null keys, broken referential integrity, negative revenue) — bad data
   never reaches the dashboard silently.
4. **Lineage on every bronze row** (`_ingested_at`, `_source_file`) — you can
   always trace a gold number back to its source file.
