-- Final E2E active-work checks from test_protocol.md.

SELECT task_type, status, COUNT(*) AS count
FROM agent_tasks
WHERE status IN ('queued', 'running')
GROUP BY task_type, status;

SELECT status, COUNT(*) AS count
FROM contact_attempts
WHERE status IN ('queued', 'running')
GROUP BY status;

