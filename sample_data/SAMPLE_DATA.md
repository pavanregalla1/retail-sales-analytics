# Sample Data

`orders_sample.csv` — 500 raw order rows, taken from the start of the output of
`etl/generate_data.py` (same seeded generator that builds `data/raw/orders.csv`).
No customer PII is included (orders carry only IDs). Safe to share, inspect, or
load into Power BI for a quick smoke test.

## Columns

| Column | Type | Description |
|---|---|---|
| `order_id` | string | Unique order key, e.g. `O000001` |
| `order_date` | string | Order date (`YYYY-MM-DD`; ~1% of rows use `DD/MM/YYYY` on purpose — the pipeline's date-fixing step handles these) |
| `customer_id` | string | Customer key, e.g. `C01234` (join to `dim_customer`) |
| `product_id` | string | Product key, e.g. `P0007` (join to `dim_product`; a few rows use `P9999`, an orphan FK the pipeline removes) |
| `quantity` | integer | Units ordered (~1% of rows are negative on purpose — the pipeline drops them) |
| `unit_price` | decimal | Price per unit at order time |
| `discount` | decimal | Discount fraction applied (0, 0.05, 0.10, 0.15, 0.20) |

To regenerate the full raw dataset: `python3 etl/generate_data.py`.
