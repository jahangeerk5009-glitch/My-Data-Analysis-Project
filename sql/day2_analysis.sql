-- Top 10 products by units sold
SELECT
    Description,
    SUM(Quantity) AS units_sold,
    ROUND(SUM(Revenue), 2) AS sales_revenue
FROM sales
GROUP BY Description
ORDER BY units_sold DESC
LIMIT 10;

-- Top 10 customers by spending
SELECT
    CustomerID,
    ROUND(SUM(Revenue), 2) AS total_spending,
    COUNT(DISTINCT InvoiceNo) AS number_of_orders
FROM sales
GROUP BY CustomerID
ORDER BY total_spending DESC
LIMIT 10;