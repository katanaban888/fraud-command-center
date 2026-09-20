-- Business question: How does labelled fraud rate change by month?
SELECT strftime('%Y-%m', timestamp) AS month,
       COUNT(*) AS transaction_count,
       SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) AS fraud_count,
       1.0 * SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) / COUNT(*) AS fraud_rate
FROM transactions
GROUP BY strftime('%Y-%m', timestamp)
ORDER BY month;
