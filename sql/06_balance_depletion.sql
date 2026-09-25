-- Business question: Which transactions consume at least 90% of available balance?
SELECT transaction_id, sender_customer_id, amount, balance_before,
       amount / NULLIF(balance_before, 0) AS depletion_ratio
FROM transactions
WHERE amount / NULLIF(balance_before, 0) >= 0.90
ORDER BY depletion_ratio DESC;
