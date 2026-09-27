# Interview Talk Track — Retail Sales Analytics Pipeline

## The 2-minute version

"I built an end-to-end retail analytics pipeline. Raw order, customer, and
product CSVs land in a bronze layer exactly as-received, with ingestion
timestamps and source-file lineage on every row. The silver layer cleanses —
dedupe, date parsing, type casting, key conforming — and anything that can't
be trusted goes to a quarantine table with a reason, instead of being silently
dropped. Gold is a star schema — fact_orders with customer, product, and date
dimensions — plus a pre-aggregated monthly sales mart that feeds the Power BI
dashboard directly. The whole thing is gated by data-quality checks: null keys,
referential integrity, negative revenue — if any check fails, the job fails
instead of publishing bad numbers. About 60K raw orders in, 56K clean fact
rows out, around $81M in revenue modeled."

## Likely questions

**Why medallion instead of going straight to the warehouse?**
"Bronze preserves the raw truth — if a cleansing rule is wrong, I can replay
from bronze without re-extracting. Silver is the single clean source every
downstream model trusts. Gold is purpose-built for analytics so the BI layer
never does heavy joins."

**Why quarantine instead of dropping bad rows?**
"Silent drops hide data problems and make revenue numbers unexplainable.
Quarantine keeps the pipeline honest — the business can see exactly what was
excluded and why, and we can fix the source and reprocess."

**How would this scale?**
"The logic is written once and runs on Databricks with Delta Lake — same
transforms, distributed. The monthly mart means the dashboard never scans the
fact table directly, so it stays fast at hundreds of millions of rows.
Partition by order date in production."

**How do you handle late-arriving or changing dimensions?**
"Customer and product are Type 1 in this version — latest wins. If the business
needed history, I'd switch to Type 2 with effective dates and a current-row
flag; the fact table grain wouldn't change."

**What would you do differently?**
"Add dbt for the silver→gold models so transformations are tested SQL with
version control, and put the whole thing behind CI — run the DQ suite on every
pull request before it can touch gold."
