-- Business question: What is the suspicious transaction volume by day and channel?
SELECT DATE(t.timestamp) AS event_date,
       t.channel,
       COUNT(*) AS transaction_count,
       SUM(t.amount) AS transaction_amount,
       SUM(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) AS labelled_fraud_count
FROM transactions t
GROUP BY DATE(t.timestamp), t.channel
ORDER BY event_date, transaction_amount DESC;
