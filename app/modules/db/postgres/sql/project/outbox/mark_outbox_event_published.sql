UPDATE outbox
SET status = 'published',
    processed_at = now()
WHERE id = :id
;
