CREATE MATERIALIZED VIEW IF NOT EXISTS mv_olap_monthly_sales AS
SELECT
    d.year,
    d.quarter,
    d.month,
    d.yearmonth,
    COUNT(DISTINCT f.invoiceno) AS total_orders,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.totalrevenue) AS revenue_gbp
FROM fact_sales f
JOIN dim_date d ON f.datekey = d.datekey
GROUP BY d.year, d.quarter, d.month, d.yearmonth;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_olap_monthly_sales_yearmonth
    ON mv_olap_monthly_sales (yearmonth);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_olap_monthly_country_sales AS
SELECT
    d.year,
    d.quarter,
    d.month,
    d.yearmonth,
    l.country,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.totalrevenue) AS revenue_gbp
FROM fact_sales f
JOIN dim_date d ON f.datekey = d.datekey
JOIN dim_location l ON f.locationkey = l.locationkey
GROUP BY d.year, d.quarter, d.month, d.yearmonth, l.country;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_olap_month_country
    ON mv_olap_monthly_country_sales (yearmonth, country);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_olap_monthly_product_sales AS
SELECT
    d.year,
    d.quarter,
    d.month,
    d.yearmonth,
    p.stockcode,
    p.description,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.totalrevenue) AS revenue_gbp
FROM fact_sales f
JOIN dim_date d ON f.datekey = d.datekey
JOIN dim_product p ON f.productkey = p.productkey
GROUP BY d.year, d.quarter, d.month, d.yearmonth, p.stockcode, p.description;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_olap_month_product
    ON mv_olap_monthly_product_sales (yearmonth, stockcode);
