-- Business question: Which rule results create the most false positives?
SELECT rr.rule_id,
       rr.rule_name,
       COUNT(*) AS false_positive_count,
       AVG(rr.rule_score) AS average_rule_score
FROM rule_results rr
JOIN transactions t ON t.transaction_id = rr.transaction_id
WHERE rr.triggered = 1 AND t.is_fraud = 0
GROUP BY rr.rule_id, rr.rule_name
ORDER BY false_positive_count DESC;
