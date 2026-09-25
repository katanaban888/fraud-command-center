-- Business question: Which transactions go to a beneficiary not previously used by the customer?
SELECT t.*
FROM transactions t
WHERE NOT EXISTS (
    SELECT 1 FROM transactions prior
    WHERE prior.sender_customer_id = t.sender_customer_id
      AND prior.beneficiary_id = t.beneficiary_id
      AND prior.timestamp < t.timestamp
);
