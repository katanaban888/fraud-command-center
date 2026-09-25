-- Business question: How many transactions happen in the defined night window?
SELECT DATE(timestamp) AS event_date,
       COUNT(*) AS transactions,
       SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) AS labelled_fraud
FROM transactions
WHERE CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 1 AND 5
GROUP BY DATE(timestamp)
ORDER BY event_date;
