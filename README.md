# NovaMart E-Commerce Sales & Customer Analytics

A SQL + Python analysis of two years of e-commerce transactions for **NovaMart**, a fictional multi-category online retailer — built to answer the questions a real retail analytics team would ask: what's driving revenue, who are our best customers, and where should marketing spend actually go.

> **On the data:** NovaMart is a fictional company. The dataset is synthetically generated (`scripts/generate_data.py`) to reproduce realistic retail patterns — holiday seasonality, repeat-purchase behavior, customer churn, and a small share of cancelled/refunded orders — so the analysis below reflects *real computed output* from that data, not invented numbers.

## Business questions

1. How is revenue trending, and how seasonal is the business?
2. Which products and categories actually drive the business?
3. Who are the best customers, and who is the business losing? (RFM segmentation)
4. How well does the business retain customers after their first purchase? (cohort analysis)
5. Which acquisition channels bring in the highest-value customers?

## Data model

A normalized relational schema — see `sql/schema.sql`.

```
customers (customer_id, customer_name, city, acquisition_channel, signup_date)
products  (product_id, product_name, category, unit_price, unit_cost)
orders    (order_id, customer_id, order_date, status)
order_items (order_item_id, order_id, product_id, quantity, unit_price)
```

`orders.status` is one of `completed / cancelled / refunded` — every query below filters to `completed` only, since ~6% of orders in the raw data are cancellations or refunds.

## What's in this repo

| File | What it does |
|---|---|
| `scripts/generate_data.py` | Generates the synthetic dataset (customers, products, orders, order_items) into CSVs and a SQLite database |
| `sql/schema.sql` | Table definitions, constraints and indexes |
| `sql/analysis_queries.sql` | 8 analysis queries — monthly revenue, Pareto product analysis, RFM segmentation, cohort retention, channel performance, gross margin, all written with CTEs and window functions |
| `scripts/analysis.py` | Standalone Python script version of the full analysis (loads from SQLite, produces all charts) |
| `notebooks/novamart_analysis.ipynb` | The full narrative notebook — business context, methodology, code, charts and takeaways for each question |
| `images/` | Exported chart PNGs |

## Key findings

- **Revenue grew ~4x** from Jan 2023 ($4.6K) to peak Nov 2024 ($236K), with a **consistent Nov/Dec seasonal spike** both years — the business should plan inventory and ad spend around a holiday peak rather than a flat monthly budget.
- **Revenue is concentrated**: the top 10 of 60 SKUs drive ~45% of total revenue, and **Electronics alone is 40%** of category revenue (37% gross margin) — stock-out risk on these specific items is a real business risk.
- **RFM segmentation** surfaces 103 "At Risk (high value)" customers — inactive recently, but averaging ~$4,755 in historical spend — a clearer win-back target than a blanket promotion to all 800 customers.
- **Month-1 is the critical retention window**: cohort retention drops sharply after the first month, then stabilizes around 20–40% — a post-first-purchase engagement flow is the highest-leverage retention lever.
- **Email outperforms its size**: fewer customers acquired than Paid Ads or Organic Search, but a comparable average order value (~$398) and the 2nd-highest orders-per-customer — suggesting it retains better than it acquires.

*(Full numbers, SQL and chart-by-chart breakdown are in the notebook.)*

## Tech stack

`SQL` (SQLite — CTEs, window functions, `NTILE`) · `Python` (`pandas`, `numpy`) · `Data visualization` (`matplotlib`, `seaborn`) · Jupyter Notebook

## Running it yourself

```bash
pip install -r requirements.txt
python scripts/generate_data.py        # builds data/*.csv and data/novamart.db
sqlite3 data/novamart.db < sql/schema.sql   # optional: rebuild schema from scratch
jupyter notebook notebooks/novamart_analysis.ipynb
```

Or run the plain script version instead of the notebook:

```bash
python scripts/analysis.py
```

---

Built by [Quratulain Shakeel](https://github.com/quratulain-shakeel).
