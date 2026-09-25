-- Business question: How many analyst minutes are required by day and priority?
SELECT DATE(created_at) AS event_date,
       alert_priority,
       COUNT(*) AS alerts,
       COUNT(*) * 8 AS estimated_analyst_minutes
FROM alerts
GROUP BY DATE(created_at), alert_priority
ORDER BY event_date, alert_priority;
