-- Business question: How do volume and labelled fraud differ by customer segment?
SELECT c.customer_type,
       c.customer_risk_level,
       COUNT(DISTINCT c.customer_id) AS customers,
       COUNT(t.transaction_id) AS transactions,
       SUM(t.amount) AS total_amount,
       SUM(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) AS labelled_fraud,
       1.0 * SUM(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(t.transaction_id), 0) AS fraud_rate
FROM customers c
LEFT JOIN transactions t ON t.sender_customer_id = c.customer_id
GROUP BY c.customer_type, c.customer_risk_level
ORDER BY fraud_rate DESC;
