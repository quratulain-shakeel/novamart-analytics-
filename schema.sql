-- ============================================================
-- NovaMart E-Commerce Analytics — Database Schema
-- ============================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id         INTEGER PRIMARY KEY,
    customer_name        TEXT NOT NULL,
    city                 TEXT NOT NULL,
    acquisition_channel  TEXT NOT NULL,
    signup_date          DATE NOT NULL
);

CREATE TABLE products (
    product_id     INTEGER PRIMARY KEY,
    product_name   TEXT NOT NULL,
    category       TEXT NOT NULL,
    unit_price     NUMERIC NOT NULL,
    unit_cost      NUMERIC NOT NULL
);

CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date    DATE NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('completed', 'cancelled', 'refunded'))
);

CREATE TABLE order_items (
    order_item_id  INTEGER PRIMARY KEY,
    order_id       INTEGER NOT NULL REFERENCES orders(order_id),
    product_id     INTEGER NOT NULL REFERENCES products(product_id),
    quantity       INTEGER NOT NULL,
    unit_price     NUMERIC NOT NULL
);

CREATE INDEX idx_orders_customer   ON orders(customer_id);
CREATE INDEX idx_orders_date       ON orders(order_date);
CREATE INDEX idx_items_order       ON order_items(order_id);
CREATE INDEX idx_items_product     ON order_items(product_id);
