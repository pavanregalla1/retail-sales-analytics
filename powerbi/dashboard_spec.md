# Power BI Dashboard Spec — Retail Sales Analytics

Connect Power BI Desktop to the gold CSVs (or the Delta tables via the
Databricks/Snowflake connector). Star schema, single-direction relationships:
`fact_orders` → `dim_customer`, `dim_product`, `dim_date`.

## Page 1 — Executive Overview
| Visual | Fields |
|---|---|
| KPI cards | Total Revenue, Total Orders, Avg Order Value, Repeat Purchase Rate |
| Line chart | Revenue by Month (`ym` from `mart_monthly_sales`), with MoM % |
| Bar chart | Revenue by Category |
| Donut | Orders by Customer Segment |
| Slicers | Year, Category, Country |

## Page 2 — Customer & Product Deep-Dive
| Visual | Fields |
|---|---|
| Table | Top 10 products: units, revenue, avg discount |
| Bar chart | Revenue per customer by signup cohort year |
| Map | Revenue by Country |
| Card | Quarantined orders (data-quality transparency) |

## DAX measures (paste into a `_measures` table)
```dax
Total Revenue = SUM ( fact_orders[line_total] )

Total Orders = DISTINCTCOUNT ( fact_orders[order_id] )

AOV = DIVIDE ( [Total Revenue], [Total Orders] )

Repeat Purchase Rate =
VAR MultiBuyers =
    COUNTROWS ( FILTER ( VALUES ( dim_customer[customer_id] ),
        CALCULATE ( [Total Orders] ) > 1 ) )
RETURN DIVIDE ( MultiBuyers, DISTINCTCOUNT ( dim_customer[customer_id] ) )

Revenue MoM % =
VAR PrevM = CALCULATE ( [Total Revenue], PREVIOUSMONTH ( dim_date[date] ) )
RETURN DIVIDE ( [Total Revenue] - PrevM, PrevM )

Revenue YoY % =
VAR PrevY = CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( dim_date[date] ) )
RETURN DIVIDE ( [Total Revenue] - PrevY, PrevY )
```

## Refresh plan
Bronze → Silver → Gold runs on a schedule (Databricks Workflow / Airflow);
Power BI uses scheduled refresh against the gold tables. `mart_monthly_sales`
is pre-aggregated so Page 1 loads instantly even at 100M+ row scale.
