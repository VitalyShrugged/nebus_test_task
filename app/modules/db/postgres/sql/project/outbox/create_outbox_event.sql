INSERT INTO outbox (
    aggregate_type,
    aggregate_id,
    event_type,
    payload
)
VALUES (
    :aggregate_type,
    :aggregate_id,
    :event_type,
    :payload
)
RETURNING
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
;
