-- KPI queries against the gold layer. Run these in the interview or paste into a SQL screen-share.

-- 1. Monthly revenue trend with month-over-month growth
SELECT ym, revenue, orders, aov,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY ym)) / LAG(revenue) OVER (ORDER BY ym), 1) AS mom_growth_pct
FROM mart_monthly_sales ORDER BY ym;

-- 2. Revenue by category and segment (who buys what)
SELECT p.category, c.segment,
       COUNT(*) AS orders, ROUND(SUM(f.line_total),2) AS revenue,
       ROUND(AVG(f.line_total),2) AS avg_order_value
FROM fact_orders f
JOIN dim_product p ON f.product_id = p.product_id
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY p.category, c.segment
ORDER BY revenue DESC;

-- 3. Repeat purchase rate (customers with >1 order)
WITH order_counts AS (
  SELECT customer_id, COUNT(*) AS n_orders FROM fact_orders GROUP BY customer_id
)
SELECT ROUND(100.0 * SUM(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS repeat_rate_pct,
       COUNT(*) AS total_customers
FROM order_counts;

-- 4. Top 10 products by revenue, with units and discount impact
SELECT p.product_name, p.category,
       SUM(f.quantity) AS units_sold,
       ROUND(SUM(f.line_total),2) AS revenue,
       ROUND(AVG(f.discount)*100,1) AS avg_discount_pct
FROM fact_orders f JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_name, p.category
ORDER BY revenue DESC LIMIT 10;

-- 5. Customer cohorts: revenue by signup year (are newer cohorts spending more?)
SELECT YEAR(c.signup_date) AS cohort_year,
       COUNT(DISTINCT c.customer_id) AS customers,
       ROUND(SUM(f.line_total),2) AS revenue,
       ROUND(SUM(f.line_total)/COUNT(DISTINCT c.customer_id),2) AS revenue_per_customer
FROM dim_customer c JOIN fact_orders f ON c.customer_id = f.customer_id
GROUP BY YEAR(c.signup_date) ORDER BY cohort_year;

-- 6. Data-quality audit: quarantined orders by reason (what the pipeline caught)
-- quarantine_orders holds orders cleansed out; join back to raw to classify the reason
SELECT CASE WHEN o.quantity <= 0 THEN 'bad_quantity'
            WHEN o.order_date IS NULL THEN 'bad_date'
            ELSE 'bad_customer_reference' END AS reason,
       COUNT(*) AS orders
FROM quarantine_orders q JOIN raw_orders_view o ON q.order_id = o.order_id
GROUP BY 1;
