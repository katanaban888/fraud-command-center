-- Business question: How much analyst queue volume is created by each risk level?
SELECT risk_level,
       COUNT(*) AS alert_count,
       AVG(risk_score) AS average_risk_score,
       SUM(CASE WHEN alert_status IN ('New', 'In Review', 'Escalated') THEN 1 ELSE 0 END) AS open_alerts
FROM alerts
GROUP BY risk_level
ORDER BY average_risk_score DESC;
