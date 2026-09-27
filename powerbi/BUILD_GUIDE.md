# Build the .pbix — Power BI Desktop (~10 minutes)

Power BI Desktop is Windows-only, so the `.pbix` can't be generated on Linux —
build it once by hand following these steps, then save it into `powerbi/`.

**Prerequisites**

- Power BI Desktop installed (Windows)
- This repo checked out, with gold tables built:
  `python3 etl/generate_data.py && python3 etl/run_local.py`
  → CSVs land in `data/gold/`

## 1. Load the gold tables (2 min)

1. Open Power BI Desktop → **Get data → Text/CSV**.
2. Load each file from `data/gold/` (click **Load** on each preview):
   - `fact_orders.csv`
   - `dim_customer.csv`
   - `dim_product.csv`
   - `dim_date.csv`
   - `mart_monthly_sales.csv`
   - `quarantine_orders.csv`
3. If `dim_date[date]` or `order_date` loads as text, select the column →
   **Column tools → Data type → Date**.

## 2. Build the star schema (2 min)

1. Open **Model view** (left sidebar, third icon).
2. Drag-and-drop to create these relationships — all **single direction**
   (dimension filters fact):
   - `fact_orders[customer_id]` → `dim_customer[customer_id]`
   - `fact_orders[product_id]` → `dim_product[product_id]`
   - `fact_orders[date_key]` → `dim_date[date_key]`
3. Confirm each shows `1` on the dimension side and `*` on the fact side.

## 3. Add the DAX measures (2 min)

1. **Home → Enter data** → name the table `_measures` → **Load**
   (creates an empty placeholder table).
2. Right-click `_measures` → **New measure**, and paste each measure from
   `powerbi/dashboard_spec.md`:
   `Total Revenue`, `Total Orders`, `AOV`, `Avg Discount`,
   `Revenue MoM %`, `Revenue YoY %`.
3. Select the `Avg Discount` measure → **Measure tools → Format → Percentage**.

## 4. Page 1 — Executive Overview (3 min)

Rename Page 1 to `Executive Overview`, then add:

| Visual | Setup |
|---|---|
| 4 Cards | `_measures[Total Revenue]`, `_measures[Total Orders]`, `_measures[AOV]`, `_measures[Avg Discount]` |
| Line chart | X-axis = `mart_monthly_sales[ym]` · Y-axis = Sum of `mart_monthly_sales[revenue]` |
| Bar chart | Y-axis = `dim_product[category]` · X-axis = `_measures[Total Revenue]` |
| Donut chart | Legend = `dim_customer[segment]` · Values = `_measures[Total Orders]` |
| Slicers (3) | `dim_date[year]`, `dim_product[category]`, `dim_customer[country]` |

## 5. Page 2 — Customer & Product Deep-Dive (2 min)

New page → rename to `Deep-Dive`, then add:

| Visual | Setup |
|---|---|
| Table | `dim_product[product_name]`, Sum of `fact_orders[quantity]`, `_measures[Total Revenue]`, `_measures[Avg Discount]` → sort by Total Revenue ↓, **Filters → Top N = 10** |
| Bar chart | X-axis = `_measures[Total Revenue]` · Y-axis = new calculated column `Cohort Year = YEAR(dim_customer[signup_date])` (Modeling → New column on `dim_customer`) |
| Map | Location = `dim_customer[country]` · Bubble size = `_measures[Total Revenue]` |
| Card | `Count of quarantine_orders[order_id]` → title it "Quarantined orders (DQ transparency)" |

## 6. Save

**File → Save as** → `powerbi/RetailSalesAnalytics.pbix` (inside this repo).

Done — the `.pbix` now matches `powerbi/dashboard_spec.md`, and the dashboard
renders the same numbers as the evidence images in `docs/images/`.
