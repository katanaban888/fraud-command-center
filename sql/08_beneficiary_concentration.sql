-- Business question: Which beneficiaries receive funds from many distinct customers?
SELECT beneficiary_id,
       COUNT(DISTINCT sender_customer_id) AS sender_count,
       COUNT(*) AS transaction_count,
       SUM(amount) AS total_amount
FROM transactions
GROUP BY beneficiary_id
HAVING COUNT(DISTINCT sender_customer_id) >= 8
ORDER BY sender_count DESC, total_amount DESC;
