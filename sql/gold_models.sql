-- Gold-layer star schema DDL (Snowflake / Databricks SQL / Postgres compatible)
-- Grain: one row per order line in fact_orders.

CREATE TABLE dim_customer (
    customer_id  VARCHAR(10)  PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    email        VARCHAR(150),
    segment      VARCHAR(20),          -- Consumer | Corporate | Home Office
    country      VARCHAR(30),
    city         VARCHAR(50),
    signup_date  DATE
);

CREATE TABLE dim_product (
    product_id   VARCHAR(10)  PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category     VARCHAR(30),          -- Electronics | Furniture | Clothing | Grocery
    unit_price   DECIMAL(10,2) NOT NULL
);

CREATE TABLE dim_date (
    date_key     INT PRIMARY KEY,      -- YYYYMMDD
    date         DATE NOT NULL,
    year         INT, month INT, month_name VARCHAR(3),
    quarter      INT, day_of_week VARCHAR(10)
);

CREATE TABLE fact_orders (
    order_id     VARCHAR(10)  PRIMARY KEY,
    order_date   DATE NOT NULL,
    date_key     INT NOT NULL REFERENCES dim_date(date_key),
    customer_id  VARCHAR(10) NOT NULL REFERENCES dim_customer(customer_id),
    product_id   VARCHAR(10) NOT NULL REFERENCES dim_product(product_id),
    quantity     INT CHECK (quantity > 0),
    unit_price   DECIMAL(10,2) NOT NULL,
    discount     DECIMAL(4,2) DEFAULT 0,
    line_total   DECIMAL(12,2) NOT NULL  -- quantity * unit_price * (1 - discount)
);

-- Monthly KPI mart: pre-aggregated, feeds the executive dashboard page directly
CREATE TABLE mart_monthly_sales (
    ym        VARCHAR(7) PRIMARY KEY,  -- YYYY-MM
    revenue   DECIMAL(14,2),
    orders    INT,
    units     INT,
    customers INT,
    aov       DECIMAL(10,2)           -- average order value
);
