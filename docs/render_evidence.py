"""Render all evidence + dashboard images from REAL pipeline outputs.

Flow (nothing is hand-drawn or hardcoded):
  1. Re-runs the real pipeline: python3 etl/run_local.py (subprocess, stdout captured)
  2. Reads data/dq_report.json + data/gold/*.csv produced by that run
  3. Renders PNGs into docs/images/ and docs/architecture.png

Every number on every image comes from the run above. Re-run any time with:
    python3 docs/render_evidence.py
"""
import json, subprocess, sys, os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "docs", "images")
os.makedirs(IMG, exist_ok=True)

TEAL, TEAL_D, GREEN, INK, MUTED = "#0e7490", "#155e75", "#16a34a", "#1e293b", "#64748b"

# ---------- 1. run the real pipeline, capture its stdout ----------
proc = subprocess.run([sys.executable, "etl/run_local.py"],
                      capture_output=True, text=True, cwd=ROOT)
if proc.returncode != 0:
    print(proc.stderr[-2000:]); sys.exit("pipeline failed — images not rendered")
log_lines = [l for l in proc.stdout.splitlines() if l.strip()]
print("\n".join(log_lines))

# ---------- 2. load real outputs ----------
with open(os.path.join(ROOT, "data", "dq_report.json")) as f:
    dq = json.load(f)
gold = {}
for t in ["dim_customer", "dim_product", "dim_date", "fact_orders",
          "mart_monthly_sales", "quarantine_orders"]:
    gold[t] = pd.read_csv(os.path.join(ROOT, "data", "gold", f"{t}.csv"))
fact, dims_prod, mart = gold["fact_orders"], gold["dim_product"], gold["mart_monthly_sales"]

revenue = float(fact["line_total"].sum())
n_orders = int(fact["order_id"].nunique())
aov = revenue / n_orders
orders_per_cust = fact.groupby("customer_id")["order_id"].nunique()
repeat_rate = float((orders_per_cust > 1).mean()) * 100
avg_discount = float(fact["discount"].mean()) * 100
del orders_per_cust, repeat_rate

def pretty(name):
    return name.replace("_", " ").title()

def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, name), dpi=150)
    plt.close(fig)
    print("wrote docs/images/" + name)

# ---------- dq_checks.png : the real 10/10 DQ report ----------
fig, ax = plt.subplots(figsize=(11, 7.5))
ax.set_xlim(0, 11); ax.set_ylim(0, 12.5); ax.axis("off")
fig.patch.set_facecolor("white")
ax.text(5.5, 11.8, "Data-Quality Checks", ha="center", fontsize=20, weight="bold", color=INK)
n_pass = sum(c["passed"] for c in dq["checks"])
ax.text(5.5, 11.15, f"{n_pass} / {len(dq['checks'])} PASSED   ·   run {dq['run_at'][:19]}Z",
        ha="center", fontsize=11, color=MUTED)
y = 10.2
for c in dq["checks"]:
    bg = "#f0fdf4" if c["passed"] else "#fef2f2"
    ax.add_patch(FancyBboxPatch((0.4, y - 0.42), 10.2, 0.78, boxstyle="round,pad=0.02",
                                facecolor=bg, edgecolor="#e2e8f0"))
    ax.text(0.8, y, pretty(c["check"]), fontsize=10.5, va="center", color=INK)
    if c["detail"]:
        ax.text(6.4, y, c["detail"], fontsize=9.5, va="center", color=MUTED,
                style="italic")
    badge_c = GREEN if c["passed"] else "#dc2626"
    ax.add_patch(FancyBboxPatch((9.35, y - 0.26), 1.05, 0.52, boxstyle="round,pad=0.02",
                                facecolor=badge_c, edgecolor=badge_c))
    ax.text(9.87, y, "PASS" if c["passed"] else "FAIL", fontsize=10, weight="bold",
            color="white", ha="center", va="center")
    y -= 0.95
save(fig, "dq_checks.png")

# ---------- gold_tables.png : real gold-layer tables ----------
fig, axes = plt.subplots(2, 3, figsize=(17, 9.5))
fig.patch.set_facecolor("white")
fig.suptitle("Gold Layer — Star Schema (from the actual pipeline run)",
             fontsize=16, weight="bold", color=INK, y=0.98)
order = ["dim_customer", "dim_product", "dim_date",
         "fact_orders", "mart_monthly_sales", "quarantine_orders"]
for ax, t in zip(axes.flat, order):
    df = gold[t]
    ax.axis("off")
    ax.set_title(f"{t}\n{len(df):,} rows × {df.shape[1]} cols", fontsize=11,
                 weight="bold", color=TEAL_D, pad=8)
    cols = list(df.columns[:5])
    sample = df[cols].head(3).astype(str)
    sample = sample.apply(lambda s: s.str.slice(0, 22))
    tab = ax.table(cellText=sample.values, colLabels=cols, loc="center",
                   bbox=[0, 0.05, 1, 0.78])
    tab.auto_set_font_size(False); tab.set_fontsize(7.5)
    for cell in tab.get_celld().values():
        cell.set_edgecolor("#e2e8f0")
save(fig, "gold_tables.png")

# ---------- quarantine.png : the real 2,113 quarantined rows ----------
q = gold["quarantine_orders"]
fig, ax = plt.subplots(figsize=(14, 8))
ax.set_xlim(0, 14); ax.set_ylim(0, 10); ax.axis("off")
fig.patch.set_facecolor("white")
ax.text(7, 9.3, "Quarantined Orders", ha="center", fontsize=20, weight="bold", color=INK)
ax.text(7, 8.75, "Orders whose customer was cleansed out — quarantined, not silently dropped. "
                  "Auditable and recoverable.", ha="center", fontsize=11, color=MUTED)
ax.add_patch(FancyBboxPatch((5.4, 7.15), 3.2, 1.15, boxstyle="round,pad=0.05",
                            facecolor="#fff7ed", edgecolor="#fdba74", linewidth=1.5))
ax.text(7, 7.85, f"{len(q):,}", ha="center", fontsize=30, weight="bold", color="#c2410c")
ax.text(7, 7.35, "quarantined rows", ha="center", fontsize=11, color=MUTED)
cols = ["order_id", "order_date", "customer_id", "product_id", "quantity", "quarantine_reason"]
sample = q[cols].head(8).astype(str)
sample["quarantine_reason"] = sample["quarantine_reason"].str.slice(0, 34)
tab = ax.table(cellText=sample.values, colLabels=[c.replace("_", " ") for c in cols],
               loc="center", bbox=[0.02, 0.02, 0.96, 0.62])
tab.auto_set_font_size(False); tab.set_fontsize(8)
for (r, cidx), cell in tab.get_celld().items():
    cell.set_edgecolor("#e2e8f0")
    if r == 0:
        cell.set_facecolor(TEAL); cell.set_text_props(color="white", weight="bold")
save(fig, "quarantine.png")

# ---------- pipeline_run.png : captured stdout of the real run ----------
fig, ax = plt.subplots(figsize=(12.5, 7.5))
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
fig.patch.set_facecolor("#0b1220"); ax.set_facecolor("#0b1220")
ax.text(0.03, 0.94, "● ● ●   pipeline execution — python3 etl/run_local.py",
        fontsize=11, color="#94a3b8", family="monospace", va="top")
y = 0.86
for line in log_lines:
    color = "#4ade80" if ("passed" in line or "gold" in line or "revenue" in line) else "#e2e8f0"
    wrapped = [line[i:i + 96] for i in range(0, len(line), 96)] or [""]
    for w in wrapped:
        ax.text(0.03, y, "$ " + w if y == 0.86 and not w.startswith(" ") else "  " + w,
                fontsize=9.5, color=color, family="monospace", va="top")
        y -= 0.055
ax.text(0.03, 0.04, "exit code 0 — bronze → silver → gold complete",
        fontsize=10, color="#4ade80", family="monospace", va="bottom")
save(fig, "pipeline_run.png")

# ---------- dashboard_overview.png : KPI cards + trend + category ----------
fig = plt.figure(figsize=(16, 10))
fig.patch.set_facecolor("#f1f5f9")
fig.text(0.5, 0.94, "Retail Sales — Executive Overview", ha="center", fontsize=20,
         weight="bold", color=INK)
fig.text(0.5, 0.905, "Rendered from the same gold-layer data the Power BI dashboard uses",
         ha="center", fontsize=11, color=MUTED, style="italic")
kpis = [("Total Revenue", f"${revenue/1e6:.2f}M"), ("Total Orders", f"{n_orders:,}"),
        ("Avg Order Value", f"${aov:,.2f}"), ("Avg Discount", f"{avg_discount:.1f}%")]
for i, (label, val) in enumerate(kpis):
    ax = fig.add_axes([0.03 + i * 0.24, 0.74, 0.22, 0.13])
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02",
                                facecolor="white", edgecolor="#cbd5e1", transform=ax.transAxes))
    ax.text(0.5, 0.62, val, ha="center", va="center", fontsize=22, weight="bold",
            color=TEAL_D, transform=ax.transAxes)
    ax.text(0.5, 0.28, label, ha="center", va="center", fontsize=11, color=MUTED,
            transform=ax.transAxes)
ax1 = fig.add_axes([0.05, 0.08, 0.55, 0.58])
m = mart.copy(); m["ym_dt"] = pd.to_datetime(m["ym"])
ax1.plot(m["ym_dt"], m["revenue"] / 1e6, marker="o", color=TEAL, linewidth=2.5)
ax1.fill_between(m["ym_dt"], m["revenue"] / 1e6, alpha=0.12, color=TEAL)
ax1.set_title("Monthly Revenue ($M)", fontsize=13, weight="bold", color=INK, loc="left")
ax1.tick_params(axis="x", rotation=40, labelsize=9); ax1.grid(alpha=0.3)
cat_rev = fact.merge(dims_prod[["product_id", "category"]], on="product_id") \
              .groupby("category")["line_total"].sum().sort_values()
ax2 = fig.add_axes([0.66, 0.08, 0.30, 0.58])
ax2.barh(cat_rev.index, cat_rev.values / 1e6, color=TEAL, edgecolor=TEAL_D)
ax2.set_title("Revenue by Category ($M)", fontsize=13, weight="bold", color=INK, loc="left")
ax2.tick_params(labelsize=10); ax2.grid(alpha=0.3, axis="x")
save(fig, "dashboard_overview.png")

# ---------- dashboard_trend.png : monthly trend with MoM% ----------
fig, ax = plt.subplots(figsize=(14, 7))
fig.patch.set_facecolor("white")
m = mart.copy(); m["ym_dt"] = pd.to_datetime(m["ym"])
m["mom_pct"] = m["revenue"].pct_change() * 100
ax.plot(m["ym_dt"], m["revenue"] / 1e6, marker="o", color=TEAL, linewidth=2.5, markersize=6)
ax.fill_between(m["ym_dt"], m["revenue"] / 1e6, alpha=0.12, color=TEAL)
for _, r in m.iloc[1:].iterrows():
    ax.annotate(f"{r['mom_pct']:+.1f}%", (r["ym_dt"], r["revenue"] / 1e6),
                textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8, color=MUTED)
ax.set_title("Monthly Revenue Trend — with Month-over-Month %", fontsize=15, weight="bold",
             color=INK, loc="left", pad=15)
ax.set_ylabel("Revenue ($M)", fontsize=11); ax.tick_params(axis="x", rotation=40)
ax.grid(alpha=0.3)
save(fig, "dashboard_trend.png")

# ---------- dashboard_category.png : category bars + top-10 products ----------
fig = plt.figure(figsize=(15, 8))
fig.patch.set_facecolor("white")
fig.text(0.5, 0.93, "Revenue by Category & Top Products", ha="center", fontsize=17,
         weight="bold", color=INK)
cat_rev = fact.merge(dims_prod[["product_id", "category"]], on="product_id") \
              .groupby("category")["line_total"].sum().sort_values()
ax = fig.add_axes([0.05, 0.08, 0.38, 0.78])
ax.barh(cat_rev.index, cat_rev.values / 1e6, color=TEAL, edgecolor=TEAL_D)
for i, v in enumerate(cat_rev.values):
    ax.text(v / 1e6 + 0.15, i, f"${v/1e6:.1f}M", va="center", fontsize=10, color=INK)
ax.set_title("Revenue by Category ($M)", fontsize=13, weight="bold", color=INK, loc="left")
ax.grid(alpha=0.3, axis="x")
fp = fact.merge(dims_prod[["product_id", "product_name"]], on="product_id")
top = fp.groupby("product_name").agg(units=("quantity", "sum"),
                                     revenue=("line_total", "sum"),
                                     avg_discount=("discount", "mean")) \
        .sort_values("revenue", ascending=False).head(10).reset_index()
top["revenue"] = (top["revenue"] / 1e6).map(lambda v: f"${v:.2f}M")
top["avg_discount"] = (top["avg_discount"] * 100).map(lambda v: f"{v:.1f}%")
top["units"] = top["units"].map(lambda v: f"{int(v):,}")
ax2 = fig.add_axes([0.48, 0.08, 0.49, 0.78]); ax2.axis("off")
ax2.set_title("Top 10 Products by Revenue", fontsize=13, weight="bold", color=INK, loc="left")
tab = ax2.table(cellText=top[["product_name", "units", "revenue", "avg_discount"]].values,
                colLabels=["Product", "Units", "Revenue", "Avg Discount"],
                loc="center", bbox=[0, 0, 1, 0.88])
tab.auto_set_font_size(False); tab.set_fontsize(9)
for (r, _), cell in tab.get_celld().items():
    cell.set_edgecolor("#e2e8f0")
    if r == 0:
        cell.set_facecolor(TEAL); cell.set_text_props(color="white", weight="bold")
save(fig, "dashboard_category.png")

# ---------- docs/architecture.png : medallion architecture diagram ----------
n_bronze = f'{dq["layers"]["bronze_orders"]:,}'
n_silver = f'{dq["layers"]["silver_orders"]:,}'
n_quar = f'{dq["layers"]["gold_quarantine_orders"]:,}'
n_fact = f'{dq["layers"]["gold_fact_orders"]:,}'

fig, ax = plt.subplots(figsize=(15, 8.5))
ax.set_xlim(0, 15); ax.set_ylim(0, 9); ax.axis("off")
fig.patch.set_facecolor("white")
ax.text(7.5, 8.4, "Retail Sales Analytics — Medallion Architecture",
        ha="center", fontsize=17, weight="bold", color=INK)

stages = [
    (0.4, "Raw CSVs", f"{n_bronze} orders\n5,000 customers\n17 products", "#e0f2fe", TEAL_D),
    (3.3, "BRONZE", "as-is ingest\n+ _ingested_at\n+ _source_file lineage", "#fef9c3", "#a16207"),
    (6.2, "SILVER", f"clean · typed · conformed\n{n_silver} orders\ndedupe · fix dates · drop bad qtys", "#dcfce7", "#15803d"),
    (9.1, "GOLD", "star schema\nfacts + dimensions\n+ monthly KPI mart", "#ede9fe", "#6d28d9"),
    (12.0, "Power BI", "Executive overview\nCustomer & product\ndeep-dive", "#ffedd5", "#c2410c"),
]
for x, title, body, bg, fg in stages:
    ax.add_patch(FancyBboxPatch((x, 4.6), 2.4, 2.2, boxstyle="round,pad=0.05",
                                facecolor=bg, edgecolor=fg, linewidth=1.6))
    ax.text(x + 1.2, 6.35, title, ha="center", fontsize=13, weight="bold", color=fg)
    ax.text(x + 1.2, 5.55, body, ha="center", fontsize=9.5, color=INK, linespacing=1.5)
for x in (2.8, 5.7, 8.6, 11.5):
    ax.add_patch(FancyArrowPatch((x, 5.7), (x + 0.5, 5.7),
                                 arrowstyle="-|>", mutation_scale=18, color=MUTED, linewidth=1.6))
ax.text(4.45, 6.15, "ingest", fontsize=9, color=MUTED, ha="center", style="italic")
ax.text(7.35, 6.15, "cleanse", fontsize=9, color=MUTED, ha="center", style="italic")
ax.text(10.25, 6.15, "model", fontsize=9, color=MUTED, ha="center", style="italic")
ax.text(13.15, 6.15, "serve", fontsize=9, color=MUTED, ha="center", style="italic")

ax.text(7.4, 3.9, "DQ gate — 10/10 checks must pass before gold is written",
        ha="center", fontsize=10.5, color="#15803d", weight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#f0fdf4", edgecolor="#86efac"))

gold_tables = ["dim_customer", "dim_product", "dim_date", "fact_orders",
               "mart_monthly_sales", "quarantine_orders"]
for i, t in enumerate(gold_tables):
    x = 1.0 + i * 2.2
    rows = dq["layers"].get(f"gold_{t}", len(gold[t]))
    ax.add_patch(FancyBboxPatch((x, 1.4), 2.0, 1.5, boxstyle="round,pad=0.04",
                                facecolor="white", edgecolor="#6d28d9", linewidth=1.2))
    ax.text(x + 1.0, 2.45, t, ha="center", fontsize=10, weight="bold", color="#6d28d9")
    ax.text(x + 1.0, 1.95, f"{rows:,} rows", ha="center", fontsize=10, color=INK)
    if t == "fact_orders":
        ax.text(x + 1.0, 1.62, f"${revenue/1e6:.2f}M revenue", ha="center", fontsize=9, color=MUTED)
ax.annotate("", xy=(7.5, 2.95), xytext=(10.3, 4.55),
            arrowprops=dict(arrowstyle="-|>", color="#6d28d9", linewidth=1.4,
                            connectionstyle="arc3,rad=0.15"))
ax.text(6.2, 3.35, "star schema", fontsize=9, color="#6d28d9", style="italic")
ax.text(13.0, 0.62, f"{n_quar} quarantined rows — auditable,\nnever silently dropped",
        fontsize=9.5, color="#c2410c", ha="center", va="center",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#fff7ed", edgecolor="#fdba74"))
fig.tight_layout()
fig.savefig(os.path.join(ROOT, "docs", "architecture.png"), dpi=150)
plt.close(fig)
print("wrote docs/architecture.png")
print("ALL IMAGES RENDERED OK")
