SELECT
    payment_id,
    amount,
    currency,
    description,
    metadata,
    status,
    idempotency_key,
    webhook_url,
    created_at,
    processed_at
FROM payments
WHERE idempotency_key = :idempotency_key
;
