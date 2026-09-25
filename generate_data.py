"""
Synthetic data generator for the NovaMart e-commerce sales dataset.
Produces customers, products, orders and order_items tables that mimic
real-world retail transaction patterns: seasonality, repeat-purchase
behavior, churn, acquisition channels and a small share of
cancelled/refunded orders (for a realistic data-cleaning step).
"""
import numpy as np
import pandas as pd
import sqlite3
from datetime import date, timedelta

rng = np.random.default_rng(42)

# ---------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------
N_CUSTOMERS = 800
CITIES = ["Lahore", "Karachi", "Islamabad", "Faisalabad", "Multan",
          "Rawalpindi", "Peshawar", "Quetta"]
CHANNELS = ["Organic Search", "Paid Ads", "Referral", "Email", "Social Media"]

signup_start = date(2023, 1, 1)
signup_end = date(2024, 10, 1)
signup_range_days = (signup_end - signup_start).days

customers = pd.DataFrame({
    "customer_id": np.arange(1, N_CUSTOMERS + 1),
    "customer_name": [f"Customer_{i:04d}" for i in range(1, N_CUSTOMERS + 1)],
    "city": rng.choice(CITIES, N_CUSTOMERS, p=[.22, .20, .14, .10, .08, .10, .09, .07]),
    "acquisition_channel": rng.choice(CHANNELS, N_CUSTOMERS, p=[.32, .28, .18, .12, .10]),
    "signup_date": [signup_start + timedelta(days=int(d)) for d in rng.integers(0, signup_range_days, N_CUSTOMERS)],
})
# Each customer's underlying purchase propensity (drives frequency + churn)
customers["purchase_rate"] = rng.lognormal(mean=-1.6, sigma=0.7, size=N_CUSTOMERS).clip(0.02, 1.2)

# ---------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------
CATEGORIES = {
    "Electronics": (25, 350),
    "Home & Kitchen": (10, 150),
    "Apparel": (8, 90),
    "Beauty": (5, 60),
    "Sports & Outdoors": (12, 180),
    "Books": (4, 35),
}
products = []
pid = 1
for cat, (lo, hi) in CATEGORIES.items():
    n_products = 10
    for _ in range(n_products):
        price = round(rng.uniform(lo, hi), 2)
        cost = round(price * rng.uniform(0.45, 0.72), 2)
        products.append((pid, f"{cat} Item {pid:03d}", cat, price, cost))
        pid += 1
products = pd.DataFrame(products, columns=["product_id", "product_name", "category", "unit_price", "unit_cost"])

# ---------------------------------------------------------------------
# Orders + order_items (simulate month-by-month purchase behaviour)
# ---------------------------------------------------------------------
DATASET_END = date(2024, 12, 31)
order_rows = []
item_rows = []
order_id = 1
item_id = 1

def month_range(start, end):
    y, m = start.year, start.month
    out = []
    while date(y, m, 1) <= end:
        out.append(date(y, m, 1))
        m += 1
        if m == 13:
            m = 1
            y += 1
    return out

for _, cust in customers.iterrows():
    months = month_range(cust.signup_date, DATASET_END)
    for m_start in months:
        # Seasonality boost for Nov/Dec (holiday shopping)
        season = 1.6 if m_start.month in (11, 12) else 1.0
        # Slight fatigue the longer since signup (mild churn effect)
        tenure_months = (m_start.year - cust.signup_date.year) * 12 + (m_start.month - cust.signup_date.month)
        fatigue = max(0.55, 1 - tenure_months * 0.012)
        monthly_rate = cust.purchase_rate * season * fatigue
        if rng.random() > min(monthly_rate, 0.95):
            continue
        n_orders_this_month = rng.poisson(1.1) + 1
        for _ in range(n_orders_this_month):
            days_in_month = 28
            order_day = m_start + timedelta(days=int(rng.integers(0, days_in_month)))
            if order_day > DATASET_END:
                continue
            status = rng.choice(["completed", "cancelled", "refunded"], p=[0.94, 0.03, 0.03])
            order_rows.append((order_id, cust.customer_id, order_day.isoformat(), status))

            n_items = rng.integers(1, 5)
            chosen = products.sample(n=n_items, replace=False, random_state=int(rng.integers(0, 1_000_000)))
            for _, prod in chosen.iterrows():
                qty = int(rng.integers(1, 4))
                # occasional small promo discount
                price = prod.unit_price * (0.95 if rng.random() < 0.15 else 1.0)
                item_rows.append((item_id, order_id, prod.product_id, qty, round(price, 2)))
                item_id += 1
            order_id += 1

orders = pd.DataFrame(order_rows, columns=["order_id", "customer_id", "order_date", "status"])
order_items = pd.DataFrame(item_rows, columns=["order_item_id", "order_id", "product_id", "quantity", "unit_price"])

customers = customers.drop(columns=["purchase_rate"])  # internal-only field

# ---------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------
customers.to_csv("/home/claude/dataanalyst/data/customers.csv", index=False)
products.to_csv("/home/claude/dataanalyst/data/products.csv", index=False)
orders.to_csv("/home/claude/dataanalyst/data/orders.csv", index=False)
order_items.to_csv("/home/claude/dataanalyst/data/order_items.csv", index=False)

conn = sqlite3.connect("/home/claude/dataanalyst/data/novamart.db")
customers.to_sql("customers", conn, if_exists="replace", index=False)
products.to_sql("products", conn, if_exists="replace", index=False)
orders.to_sql("orders", conn, if_exists="replace", index=False)
order_items.to_sql("order_items", conn, if_exists="replace", index=False)
conn.close()

print(f"customers: {len(customers)}")
print(f"products: {len(products)}")
print(f"orders: {len(orders)}")
print(f"order_items: {len(item_rows)}")
