-- Business question: Which events occur during a high-velocity customer window?
SELECT current_tx.transaction_id, current_tx.sender_customer_id, current_tx.timestamp,
       COUNT(prior_tx.transaction_id) AS transactions_in_prior_hour
FROM transactions current_tx
LEFT JOIN transactions prior_tx
  ON prior_tx.sender_customer_id = current_tx.sender_customer_id
 AND prior_tx.timestamp < current_tx.timestamp
 AND prior_tx.timestamp >= datetime(current_tx.timestamp, '-1 hour')
GROUP BY current_tx.transaction_id, current_tx.sender_customer_id, current_tx.timestamp
HAVING COUNT(prior_tx.transaction_id) >= 6;
