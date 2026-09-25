"""
NovaMart E-Commerce Analytics
------------------------------
End-to-end analysis: data validation, revenue trends, product
performance, RFM customer segmentation and cohort retention.
Reads from the SQLite database built by generate_data.py and
sql/schema.sql, and writes chart images to images/.
"""
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.0)
PALETTE = ["#2563eb", "#f97316", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]
plt.rcParams["figure.dpi"] = 150
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.titlesize"] = 13

DB = "/home/claude/dataanalyst/data/novamart.db"
IMG = "/home/claude/dataanalyst/images"

conn = sqlite3.connect(DB)

# ------------------------------------------------------------------
# Load
# ------------------------------------------------------------------
customers = pd.read_sql("SELECT * FROM customers", conn, parse_dates=["signup_date"])
products  = pd.read_sql("SELECT * FROM products", conn)
orders    = pd.read_sql("SELECT * FROM orders", conn, parse_dates=["order_date"])
items     = pd.read_sql("SELECT * FROM order_items", conn)

# ------------------------------------------------------------------
# 1. Data validation / cleaning checks
# ------------------------------------------------------------------
print("=== Data validation ===")
print("Nulls per table:")
print(" customers:", customers.isna().sum().sum())
print(" products :", products.isna().sum().sum())
print(" orders   :", orders.isna().sum().sum())
print(" items    :", items.isna().sum().sum())
print("Duplicate order_ids:", orders.order_id.duplicated().sum())
print("Order status breakdown:\n", orders.status.value_counts(), sep="")

completed_orders = orders[orders.status == "completed"]
line = items.merge(completed_orders[["order_id", "order_date", "customer_id"]], on="order_id")
line = line.merge(products[["product_id", "product_name", "category", "unit_cost"]], on="product_id")
line["revenue"] = line.quantity * line.unit_price
line["profit"]  = line.quantity * (line.unit_price - line.unit_cost)
print(f"\nClean, revenue-bearing line items: {len(line):,}")
print(f"Total net revenue: ${line.revenue.sum():,.2f}")

# ------------------------------------------------------------------
# 2. Monthly revenue trend
# ------------------------------------------------------------------
monthly = line.assign(month=line.order_date.dt.to_period("M").astype(str)) \
              .groupby("month").agg(revenue=("revenue", "sum"),
                                     orders=("order_id", "nunique")).reset_index()

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(monthly.month, monthly.revenue, marker="o", color=PALETTE[0], linewidth=2)
ax.fill_between(range(len(monthly)), monthly.revenue, color=PALETTE[0], alpha=0.08)
for i, m in enumerate(monthly.month):
    if m.endswith(("-11", "-12")):
        ax.axvspan(i - 0.5, i + 0.5, color=PALETTE[1], alpha=0.08)
ax.set_title("Monthly Revenue Trend (2023–2024)\nShaded bands = Nov/Dec holiday season")
ax.set_ylabel("Revenue ($)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:,.0f}K"))
plt.xticks(rotation=60, ha="right", fontsize=8)
plt.tight_layout()
plt.savefig(f"{IMG}/01_monthly_revenue.png")
plt.close()

# ------------------------------------------------------------------
# 3. Top products — Pareto chart
# ------------------------------------------------------------------
prod_rev = line.groupby(["product_name", "category"]).revenue.sum().reset_index() \
               .sort_values("revenue", ascending=False)
top10 = prod_rev.head(10).copy()
top10["cum_pct"] = 100 * top10.revenue.cumsum() / prod_rev.revenue.sum()

fig, ax1 = plt.subplots(figsize=(10, 5))
bars = ax1.barh(top10.product_name[::-1], top10.revenue[::-1], color=PALETTE[0])
ax1.set_xlabel("Revenue ($)")
ax1.set_title("Top 10 Products by Revenue (Pareto View)")
ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:,.0f}K"))
ax2 = ax1.twiny()
ax2.plot(top10.cum_pct[::-1], top10.product_name[::-1], color=PALETTE[1], marker="D", linewidth=2)
ax2.set_xlabel("Cumulative % of Total Revenue")
ax2.set_xlim(0, 100)
plt.tight_layout()
plt.savefig(f"{IMG}/02_top_products_pareto.png")
plt.close()

# ------------------------------------------------------------------
# 4. Category revenue + margin
# ------------------------------------------------------------------
cat = line.groupby("category").agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index()
cat["margin_pct"] = 100 * cat.profit / cat.revenue
cat = cat.sort_values("revenue", ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].bar(cat.category, cat.revenue, color=PALETTE[0])
axes[0].set_title("Revenue by Category")
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:,.0f}K"))
axes[0].tick_params(axis="x", rotation=35)
axes[1].bar(cat.category, cat.margin_pct, color=PALETTE[2])
axes[1].set_title("Gross Margin % by Category")
axes[1].tick_params(axis="x", rotation=35)
for a in axes:
    for label in a.get_xticklabels():
        label.set_ha("right")
plt.tight_layout()
plt.savefig(f"{IMG}/03_category_performance.png")
plt.close()

# ------------------------------------------------------------------
# 5. RFM segmentation (computed in pandas)
# ------------------------------------------------------------------
snapshot = pd.Timestamp("2024-12-31")
rfm = line.groupby("customer_id").agg(
    last_order=("order_date", "max"),
    frequency=("order_id", "nunique"),
    monetary=("revenue", "sum"),
).reset_index()
rfm["recency_days"] = (snapshot - rfm.last_order).dt.days

rfm["r_score"] = pd.qcut(rfm.recency_days.rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
rfm["f_score"] = pd.qcut(rfm.frequency.rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["m_score"] = pd.qcut(rfm.monetary.rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)

def segment(row):
    if row.r_score >= 3 and row.f_score >= 3 and row.m_score >= 3:
        return "Champions"
    if row.r_score >= 3 and row.f_score <= 2:
        return "New / Promising"
    if row.r_score <= 2 and row.f_score >= 3 and row.m_score >= 3:
        return "At Risk (high value)"
    if row.r_score <= 2 and row.f_score <= 2:
        return "Lost / Dormant"
    return "Regular"

rfm["segment"] = rfm.apply(segment, axis=1)
seg_summary = rfm.groupby("segment").agg(customers=("customer_id", "count"),
                                          avg_monetary=("monetary", "mean")).reset_index()
seg_summary = seg_summary.sort_values("avg_monetary", ascending=False)
print("\n=== RFM segment summary ===")
print(seg_summary.to_string(index=False))

fig, ax = plt.subplots(figsize=(9, 4.5))
bars = ax.bar(seg_summary.segment, seg_summary.customers, color=PALETTE[:len(seg_summary)])
ax.set_title("Customer Count by RFM Segment")
ax.set_ylabel("Customers")
for b, v in zip(bars, seg_summary.avg_monetary):
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 3, f"avg ${v:,.0f}",
            ha="center", fontsize=8.5, color="#374151")
plt.xticks(rotation=15, ha="right")
plt.tight_layout()
plt.savefig(f"{IMG}/04_rfm_segments.png")
plt.close()

# ------------------------------------------------------------------
# 6. Cohort retention heatmap
# ------------------------------------------------------------------
first_order = line.groupby("customer_id").order_date.min().dt.to_period("M")
line["cohort"] = line.customer_id.map(first_order)
line["order_month"] = line.order_date.dt.to_period("M")
line["month_number"] = (line.order_month - line.cohort).apply(lambda x: x.n)

cohort_counts = line.groupby(["cohort", "month_number"]).customer_id.nunique().reset_index()
cohort_pivot = cohort_counts.pivot(index="cohort", columns="month_number", values="customer_id")
cohort_size = cohort_pivot[0]
retention = cohort_pivot.divide(cohort_size, axis=0) * 100
retention = retention.iloc[:, :7]  # first 7 months for readability

fig, ax = plt.subplots(figsize=(10, 7))
sns.heatmap(retention, annot=True, fmt=".0f", cmap="Blues", cbar_kws={"label": "% retained"}, ax=ax)
ax.set_title("Monthly Cohort Retention (%)")
ax.set_xlabel("Months since first purchase")
ax.set_ylabel("Signup cohort")
plt.tight_layout()
plt.savefig(f"{IMG}/05_cohort_retention.png")
plt.close()

# ------------------------------------------------------------------
# 7. Acquisition channel performance
# ------------------------------------------------------------------
chan = line.merge(customers[["customer_id", "acquisition_channel"]], on="customer_id")
chan_summary = chan.groupby("acquisition_channel").agg(
    revenue=("revenue", "sum"),
    orders=("order_id", "nunique"),
    customers=("customer_id", "nunique"),
).reset_index()
chan_summary["aov"] = chan_summary.revenue / chan_summary.orders
chan_summary["orders_per_customer"] = chan_summary.orders / chan_summary.customers
chan_summary = chan_summary.sort_values("revenue", ascending=False)
print("\n=== Acquisition channel performance ===")
print(chan_summary.to_string(index=False))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].bar(chan_summary.acquisition_channel, chan_summary.aov, color=PALETTE[3])
axes[0].set_title("Avg Order Value by Channel")
axes[0].tick_params(axis="x", rotation=25)
axes[1].bar(chan_summary.acquisition_channel, chan_summary.orders_per_customer, color=PALETTE[4])
axes[1].set_title("Orders per Customer by Channel")
axes[1].tick_params(axis="x", rotation=25)
for a in axes:
    for label in a.get_xticklabels():
        label.set_ha("right")
plt.tight_layout()
plt.savefig(f"{IMG}/06_channel_performance.png")
plt.close()

print("\nAll charts saved to images/.")
conn.close()
