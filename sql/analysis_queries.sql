-- Sales & Customer Analytics — KPI queries
-- SQLite-compatible. Assumes tables: orders, customers, products
-- (load the CSVs with matching table names; order_date is TEXT 'YYYY-MM-DD').

-- 1. Monthly revenue by region
SELECT
    substr(o.order_date, 1, 7)          AS order_month,
    c.region                            AS region,
    COUNT(*)                            AS orders,
    ROUND(SUM(o.line_total), 2)         AS revenue,
    ROUND(AVG(o.line_total), 2)         AS avg_order_value
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY order_month, region
ORDER BY order_month, region;

-- 2. Top 10 products by revenue
SELECT
    p.product_id,
    p.product_name,
    p.category,
    COUNT(*)                            AS orders,
    SUM(o.quantity)                     AS units_sold,
    ROUND(SUM(o.line_total), 2)         AS revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;

-- 3. Repeat vs one-time customer revenue share
WITH customer_orders AS (
    SELECT customer_id,
           COUNT(*)              AS order_count,
           SUM(line_total)       AS revenue
    FROM orders
    GROUP BY customer_id
)
SELECT
    CASE WHEN order_count > 1 THEN 'repeat' ELSE 'one_time' END AS customer_type,
    COUNT(*)                                                     AS customers,
    ROUND(SUM(revenue), 2)                                      AS revenue,
    ROUND(100.0 * SUM(revenue) / (SELECT SUM(line_total) FROM orders), 1)
                                                                AS revenue_share_pct
FROM customer_orders
GROUP BY customer_type;

-- 4. Year-over-year monthly revenue growth (2024 vs 2023)
WITH monthly AS (
    SELECT substr(order_date, 1, 7) AS order_month,
           SUM(line_total)         AS revenue
    FROM orders
    GROUP BY order_month
),
y2023 AS (
    SELECT substr(order_month, 6, 2) AS mth, revenue AS revenue_2023
    FROM monthly WHERE substr(order_month, 1, 4) = '2023'
),
y2024 AS (
    SELECT substr(order_month, 6, 2) AS mth, revenue AS revenue_2024
    FROM monthly WHERE substr(order_month, 1, 4) = '2024'
)
SELECT
    y2023.mth                                   AS month,
    ROUND(y2023.revenue_2023, 2)                AS revenue_2023,
    ROUND(y2024.revenue_2024, 2)                AS revenue_2024,
    ROUND(100.0 * (y2024.revenue_2024 - y2023.revenue_2023)
          / y2023.revenue_2023, 1)              AS yoy_growth_pct
FROM y2023
JOIN y2024 ON y2023.mth = y2024.mth
ORDER BY month;

-- 5. Average order value by category
SELECT
    p.category                          AS category,
    COUNT(*)                            AS orders,
    ROUND(SUM(o.line_total), 2)         AS revenue,
    ROUND(AVG(o.line_total), 2)         AS avg_order_value
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue DESC;

-- 6. (Bonus) Channel performance
SELECT
    channel                             AS channel,
    COUNT(*)                            AS orders,
    ROUND(SUM(line_total), 2)          AS revenue,
    ROUND(AVG(line_total), 2)          AS avg_order_value
FROM orders
GROUP BY channel
ORDER BY revenue DESC;
