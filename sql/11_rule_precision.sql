-- Business question: Which triggered rules have the best synthetic precision?
WITH rule_labels AS (
    SELECT rr.rule_id, rr.rule_name, rr.transaction_id, t.is_fraud
    FROM rule_results rr
    JOIN transactions t ON t.transaction_id = rr.transaction_id
    WHERE rr.triggered = 1
)
SELECT rule_id,
       rule_name,
       COUNT(*) AS triggered_count,
       SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) AS labelled_fraud,
       1.0 * SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) / COUNT(*) AS precision
FROM rule_labels
GROUP BY rule_id, rule_name
ORDER BY precision DESC;
