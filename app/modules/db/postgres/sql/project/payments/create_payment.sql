INSERT INTO payments (
    payment_id,
    amount,
    currency,
    description,
    metadata,
    status,
    idempotency_key,
    webhook_url
)
VALUES (
    :payment_id,
    :amount,
    :currency,
    :description,
    :metadata,
    :status,
    :idempotency_key,
    :webhook_url
)
ON CONFLICT (idempotency_key) DO NOTHING
RETURNING
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
;
