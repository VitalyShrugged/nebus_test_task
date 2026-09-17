UPDATE payments
SET status = :status,
    processed_at = now()
WHERE payment_id = :payment_id
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
