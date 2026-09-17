SELECT
    id,
    aggregate_type,
    aggregate_id,
    event_type,
    payload,
    status,
    attempts,
    last_error,
    created_at,
    processed_at
FROM outbox
WHERE status = 'pending'
ORDER BY id
LIMIT :limit
FOR UPDATE SKIP LOCKED
;
