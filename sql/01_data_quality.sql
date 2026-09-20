-- Business question: Are the core transaction fields complete and valid?
SELECT
    COUNT(*) AS row_count,
    SUM(CASE WHEN transaction_id IS NULL THEN 1 ELSE 0 END) AS missing_transaction_ids,
    SUM(CASE WHEN amount <= 0 THEN 1 ELSE 0 END) AS invalid_amounts,
    SUM(CASE WHEN balance_before < 0 OR balance_after < 0 THEN 1 ELSE 0 END) AS negative_balances,
    COUNT(DISTINCT transaction_id) AS distinct_transaction_ids
FROM transactions;
