# Databricks notebook source
# Retail Sales Analytics — medallion pipeline (Databricks Runtime 14+, Delta Lake)
# Mirrors etl/run_local.py exactly: same layers, same cleansing rules, same DQ checks.
# Attach to a cluster, set the `catalog`/`schema` widgets, Run All.

# COMMAND ----------
dbutils.widgets.text("catalog", "retail")
dbutils.widgets.text("schema", "sales")
CAT, SCH = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CAT}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CAT}.{SCH}")
spark.sql(f"USE {CAT}.{SCH}")

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.types import *

bronze = {}
for t in ["customers", "products", "orders"]:
    df = (spark.read.option("header", True).csv(f"/Volumes/{CAT}/{SCH}/landing/{t}.csv")
          .withColumn("_ingested_at", F.current_timestamp())
          .withColumn("_source_file", F.lit(f"{t}.csv")))
    df.write.format("delta").mode("overwrite").saveAsTable(f"{CAT}.{SCH}.bronze_{t}")
    bronze[t] = df.count()
print(bronze)

# COMMAND ----------
# SILVER — cleanse & conform
cust = spark.table(f"{CAT}.{SCH}.bronze_customers")
cust = (cust.filter(F.col("email").isNotNull() & (F.col("email") != ""))
            .withColumn("country", F.initcap(F.trim("country")))
            .withColumn("country", F.when(F.col("country") == "Usa", "USA").otherwise(F.col("country")))
            .withColumn("signup_date", F.to_date("signup_date"))
            .dropna(subset=["signup_date"]).dropDuplicates(["customer_id"]))

prod = (spark.table(f"{CAT}.{SCH}.bronze_products")
        .withColumn("unit_price", F.col("unit_price").cast("double"))
        .dropna(subset=["unit_price"]).dropDuplicates(["product_id"]))

ord_ = spark.table(f"{CAT}.{SCH}.bronze_orders")
ord_ = ord_.dropDuplicates(["order_id"])
ord_ = (ord_.withColumn("order_date",
            F.coalesce(F.to_date("order_date", "yyyy-MM-dd"),
                       F.to_date("order_date", "dd/MM/yyyy")))
            .dropna(subset=["order_date"]))
for c in ["quantity", "unit_price", "discount"]:
    ord_ = ord_.withColumn(c, F.col(c).cast("double"))
ord_ = ord_.filter(F.col("quantity") > 0)
ord_ = ord_.join(prod.select("product_id"), "product_id", "inner")  # drop orphan product FKs
ord_ = ord_.withColumn("line_total",
            F.round(F.col("quantity") * F.col("unit_price") * (1 - F.coalesce(F.col("discount"), F.lit(0))), 2))

# quarantine: orders whose customer was cleansed out -> review table, not silent drop
valid_cust = cust.select("customer_id")
quarantine = ord_.join(valid_cust, "customer_id", "left_anti")
quarantine.write.format("delta").mode("overwrite").saveAsTable(f"{CAT}.{SCH}.quarantine_orders")
ord_ = ord_.join(valid_cust, "customer_id", "inner")

for name, df in [("silver_customers", cust), ("silver_products", prod), ("silver_orders", ord_)]:
    df.write.format("delta").mode("overwrite").saveAsTable(f"{CAT}.{SCH}.{name}")

# COMMAND ----------
# GOLD — star schema
dim_customer = cust.select("customer_id","customer_name","email","segment","country","city","signup_date")
dim_product  = prod.select("product_id","product_name","category","unit_price")
dim_date = (ord_.select(F.to_date("order_date").alias("date")).distinct()
            .withColumn("date_key", F.date_format("date","yyyyMMdd").cast("int"))
            .withColumn("year", F.year("date")).withColumn("month", F.month("date"))
            .withColumn("month_name", F.date_format("date","MMM"))
            .withColumn("quarter", F.quarter("date"))
            .withColumn("day_of_week", F.date_format("date","EEEE")))
fact_orders = (ord_.withColumn("date_key", F.date_format(F.to_date("order_date"),"yyyyMMdd").cast("int"))
               .select("order_id","order_date","customer_id","product_id","quantity",
                       "unit_price","discount","line_total","date_key"))
monthly = (fact_orders.withColumn("ym", F.date_format(F.to_date("order_date"),"yyyy-MM"))
           .groupBy("ym").agg(F.round(F.sum("line_total"),2).alias("revenue"),
                              F.countDistinct("order_id").alias("orders"),
                              F.sum("quantity").alias("units"),
                              F.countDistinct("customer_id").alias("customers"))
           .withColumn("aov", F.round(F.col("revenue")/F.col("orders"),2)))

for name, df in [("dim_customer",dim_customer),("dim_product",dim_product),
                 ("dim_date",dim_date),("fact_orders",fact_orders),
                 ("mart_monthly_sales",monthly)]:
    df.write.format("delta").mode("overwrite").saveAsTable(f"{CAT}.{SCH}.{name}")

# COMMAND ----------
# DQ gate — fail the job if any check breaks
checks = {
  "fact_rows>0":          spark.table(f"{CAT}.{SCH}.fact_orders").count() > 0,
  "no_null_order_keys":   spark.table(f"{CAT}.{SCH}.fact_orders").filter("order_id IS NULL").count() == 0,
  "ri_customer":          spark.table(f"{CAT}.{SCH}.fact_orders").join(
                              spark.table(f"{CAT}.{SCH}.dim_customer"), "customer_id", "left_anti").count() == 0,
  "ri_product":           spark.table(f"{CAT}.{SCH}.fact_orders").join(
                              spark.table(f"{CAT}.{SCH}.dim_product"), "product_id", "left_anti").count() == 0,
  "no_negative_revenue":  spark.table(f"{CAT}.{SCH}.fact_orders").filter("line_total < 0").count() == 0,
}
failed = [k for k,v in checks.items() if not v]
assert not failed, f"DQ FAILED: {failed}"
print("DQ passed:", list(checks))
