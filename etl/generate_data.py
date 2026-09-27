"""Generate realistic raw e-commerce source data (with intentional quality issues).

Produces data/raw/: customers.csv, products.csv, orders.csv
Quality issues injected on purpose so the pipeline has real cleansing to do:
  - duplicate order rows, null emails, malformed dates, negative quantities,
    orders referencing missing products, inconsistent country casing.
"""
import csv, random
from datetime import datetime, timedelta

random.seed(42)
OUT = "data/raw"

FIRST = ["Aarav","Diya","Arjun","Ishaan","Ananya","Rohan","Priya","Karan","Neha",
         "Vikram","Sneha","Aditya","Pooja","Rahul","Kavya","Manish","Divya","Suresh"]
LAST = ["Sharma","Patel","Reddy","Gupta","Mehta","Iyer","Khan","Nair","Das",
        "Kulkarni","Joshi","Chopra","Bose","Rao","Menon","Pillai"]
COUNTRIES = ["USA","usa","Usa","INDIA","India","UK","UAE","Canada"]
CITIES = {"USA":["New York","Jersey City","Austin","Seattle"],
          "INDIA":["Hyderabad","Mumbai","Bengaluru","Chennai"],
          "UK":["London","Manchester"],"UAE":["Dubai"],"Canada":["Toronto"]}
SEGMENTS = ["Consumer","Corporate","Home Office"]
CATEGORIES = {"Electronics":["Laptop","Headphones","Smartphone","Tablet","Monitor"],
              "Furniture":["Office Chair","Desk","Bookshelf","Lamp"],
              "Clothing":["T-Shirt","Jeans","Jacket","Sneakers"],
              "Grocery":["Coffee Beans","Olive Oil","Protein Bar","Honey"]}

# ---------- customers ----------
customers = []
for i in range(1, 5001):
    country_raw = random.choice(COUNTRIES)
    country = country_raw.strip().title()
    if country == "Usa": country = "USA"
    city = random.choice(CITIES.get(country, ["New York"]))
    email = None if random.random() < 0.03 else \
        f"{FIRST[i%len(FIRST)].lower()}.{LAST[i%len(LAST)].lower()}{i}@example.com"
    customers.append({
        "customer_id": f"C{i:05d}",
        "customer_name": f"{random.choice(FIRST)} {random.choice(LAST)}",
        "email": email,                       # 3% nulls on purpose
        "segment": random.choice(SEGMENTS),
        "country": country_raw,               # messy casing on purpose
        "city": city,
        "signup_date": (datetime(2022,1,1)+timedelta(days=random.randint(0,900))).strftime("%Y-%m-%d"),
    })

# ---------- products ----------
products, pid = [], 1
for cat, items in CATEGORIES.items():
    for name in items:
        products.append({
            "product_id": f"P{pid:04d}",
            "product_name": f"{name} {random.choice(['Pro','Max','Lite','Plus','']) }".strip(),
            "category": cat,
            "unit_price": round(random.uniform(9.99, 1299.99), 2),
        })
        pid += 1

# ---------- orders ----------
start = datetime(2024,1,1)
orders, oid = [], 1
for _ in range(60000):
    cust = random.choice(customers)
    prod = random.choice(products)
    qty = random.randint(1,5)
    if random.random() < 0.01: qty = -qty          # bad quantity on purpose
    if random.random() < 0.005: prod = {"product_id":"P9999","unit_price":10.0}  # orphan FK
    d = start + timedelta(days=random.randint(0, 630))
    date_str = d.strftime("%Y-%m-%d")
    if random.random() < 0.01: date_str = d.strftime("%d/%m/%Y")  # malformed date
    discount = round(random.choice([0,0,0,0.05,0.1,0.15,0.2]), 2)
    orders.append({
        "order_id": f"O{oid:06d}",
        "order_date": date_str,
        "customer_id": cust["customer_id"],
        "product_id": prod["product_id"],
        "quantity": qty,
        "unit_price": prod["unit_price"],
        "discount": discount,
    })
    oid += 1

# duplicate ~1% of orders on purpose
orders += random.sample(orders, 600)

def write(name, rows):
    with open(f"{OUT}/{name}.csv","w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

write("customers", customers); write("products", products); write("orders", orders)
print(f"customers={len(customers)} products={len(products)} orders={len(orders)}")
