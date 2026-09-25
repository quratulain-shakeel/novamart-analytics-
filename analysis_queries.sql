-- ============================================================
-- NovaMart E-Commerce Analytics — Business Queries
-- Dialect: SQLite. All revenue figures exclude cancelled/refunded orders.
-- ============================================================

-- ------------------------------------------------------------
-- 1. Monthly revenue trend
-- ------------------------------------------------------------
SELECT
    strftime('%Y-%m', o.order_date)                    AS month,
    ROUND(SUM(oi.quantity * oi.unit_price), 2)          AS revenue,
    COUNT(DISTINCT o.order_id)                          AS orders
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.status = 'completed'
GROUP BY month
ORDER BY month;


-- ------------------------------------------------------------
-- 2. Top 10 products by revenue, with running (cumulative) share
--    of total revenue — window functions for a Pareto/80-20 view
-- ------------------------------------------------------------
WITH product_revenue AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        SUM(oi.quantity * oi.unit_price) AS revenue
    FROM order_items oi
    JOIN orders o    ON o.order_id = oi.order_id
    JOIN products p  ON p.product_id = oi.product_id
    WHERE o.status = 'completed'
    GROUP BY p.product_id
)
SELECT
    product_name,
    category,
    ROUND(revenue, 2) AS revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)                                       AS pct_of_total,
    ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER (), 2)      AS cumulative_pct
FROM product_revenue
ORDER BY revenue DESC
LIMIT 10;


-- ------------------------------------------------------------
-- 3. Category contribution to total revenue
-- ------------------------------------------------------------
SELECT
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
    ROUND(100.0 * SUM(oi.quantity * oi.unit_price) / SUM(SUM(oi.quantity * oi.unit_price)) OVER (), 2) AS pct_of_total
FROM order_items oi
JOIN orders o   ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY revenue DESC;


-- ------------------------------------------------------------
-- 4. RFM base table — Recency, Frequency, Monetary per customer,
--    scored into quartiles (1 = lowest, 4 = highest) and mapped
--    to a plain-English segment
-- ------------------------------------------------------------
WITH order_summary AS (
    SELECT
        o.customer_id,
        MAX(o.order_date)                              AS last_order_date,
        COUNT(DISTINCT o.order_id)                      AS frequency,
        SUM(oi.quantity * oi.unit_price)                AS monetary
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.status = 'completed'
    GROUP BY o.customer_id
),
rfm_scored AS (
    SELECT
        customer_id,
        CAST(julianday('2024-12-31') - julianday(last_order_date) AS INTEGER) AS recency_days,
        frequency,
        ROUND(monetary, 2) AS monetary,
        NTILE(4) OVER (ORDER BY julianday(last_order_date) DESC) AS r_score,  -- more recent = higher
        NTILE(4) OVER (ORDER BY frequency ASC)                   AS f_score,
        NTILE(4) OVER (ORDER BY monetary ASC)                    AS m_score
    FROM order_summary
)
SELECT
    customer_id, recency_days, frequency, monetary, r_score, f_score, m_score,
    CASE
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
        WHEN r_score >= 3 AND f_score <= 2                  THEN 'New / Promising'
        WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk (high value)'
        WHEN r_score <= 2 AND f_score <= 2                  THEN 'Lost / Dormant'
        ELSE 'Regular'
    END AS segment
FROM rfm_scored
ORDER BY monetary DESC;


-- ------------------------------------------------------------
-- 5. Monthly cohort retention — % of each signup cohort still
--    ordering N months after their first purchase
-- ------------------------------------------------------------
WITH first_order AS (
    SELECT
        o.customer_id,
        MIN(strftime('%Y-%m', o.order_date)) AS cohort_month
    FROM orders o
    WHERE o.status = 'completed'
    GROUP BY o.customer_id
),
activity AS (
    SELECT DISTINCT
        o.customer_id,
        strftime('%Y-%m', o.order_date) AS order_month
    FROM orders o
    WHERE o.status = 'completed'
),
cohort_activity AS (
    -- NOTE: cohort_month / order_month are 'YYYY-MM' strings, not full
    -- dates, so strftime() can't parse them directly — pull the year
    -- and month out with substr() instead.
    SELECT
        f.cohort_month,
        (CAST(substr(a.order_month, 1, 4) AS INTEGER) - CAST(substr(f.cohort_month, 1, 4) AS INTEGER)) * 12
          + (CAST(substr(a.order_month, 6, 2) AS INTEGER) - CAST(substr(f.cohort_month, 6, 2) AS INTEGER)) AS month_number,
        f.customer_id
    FROM first_order f
    JOIN activity a ON a.customer_id = f.customer_id
)
SELECT
    cohort_month,
    month_number,
    COUNT(DISTINCT customer_id) AS active_customers
FROM cohort_activity
GROUP BY cohort_month, month_number
ORDER BY cohort_month, month_number;


-- ------------------------------------------------------------
-- 6. Average order value (AOV) and orders-per-customer by
--    acquisition channel
-- ------------------------------------------------------------
SELECT
    c.acquisition_channel,
    COUNT(DISTINCT o.order_id)                                      AS total_orders,
    COUNT(DISTINCT o.customer_id)                                   AS customers,
    ROUND(SUM(oi.quantity * oi.unit_price), 2)                      AS revenue,
    ROUND(SUM(oi.quantity * oi.unit_price) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value,
    ROUND(1.0 * COUNT(DISTINCT o.order_id) / COUNT(DISTINCT o.customer_id), 2) AS orders_per_customer
FROM customers c
JOIN orders o        ON o.customer_id = c.customer_id
JOIN order_items oi  ON oi.order_id = o.order_id
WHERE o.status = 'completed'
GROUP BY c.acquisition_channel
ORDER BY revenue DESC;


-- ------------------------------------------------------------
-- 7. Gross margin by category (needs product cost data)
-- ------------------------------------------------------------
SELECT
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price), 2)                    AS revenue,
    ROUND(SUM(oi.quantity * p.unit_cost), 2)                      AS cost,
    ROUND(SUM(oi.quantity * (oi.unit_price - p.unit_cost)), 2)    AS gross_profit,
    ROUND(100.0 * SUM(oi.quantity * (oi.unit_price - p.unit_cost)) / SUM(oi.quantity * oi.unit_price), 2) AS margin_pct
FROM order_items oi
JOIN orders o   ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY gross_profit DESC;


-- ------------------------------------------------------------
-- 8. Order cancellation / refund rate (data-quality / ops check)
-- ------------------------------------------------------------
SELECT
    status,
    COUNT(*) AS orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_orders
FROM orders
GROUP BY status;
