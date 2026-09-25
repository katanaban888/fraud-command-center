-- Business question: What is each customer's prior transaction baseline?
WITH ordered AS (
    SELECT
        sender_customer_id AS customer_id,
        timestamp,
        amount,
        AVG(amount) OVER (PARTITION BY sender_customer_id ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS prior_avg_amount,
        COUNT(*) OVER (PARTITION BY sender_customer_id ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS prior_transaction_count
    FROM transactions
)
SELECT * FROM ordered;
