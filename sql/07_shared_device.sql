-- Business question: Which devices are shared by multiple customers?
SELECT dcl.device_id,
       COUNT(DISTINCT dcl.customer_id) AS customer_count,
       COUNT(DISTINCT t.sender_account_id) AS account_count
FROM device_customer_links dcl
LEFT JOIN transactions t ON t.device_id = dcl.device_id
GROUP BY dcl.device_id
HAVING COUNT(DISTINCT dcl.customer_id) >= 2
ORDER BY customer_count DESC;
