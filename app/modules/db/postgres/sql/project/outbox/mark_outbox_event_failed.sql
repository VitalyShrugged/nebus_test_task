UPDATE outbox
SET attempts = attempts + 1,
    last_error = :last_error
WHERE id = :id
;
