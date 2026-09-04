-- One-time operator recovery grants and purpose-limited browser sessions.

ALTER TABLE session
    ADD COLUMN purpose text NOT NULL DEFAULT 'full'
    CHECK (purpose IN ('full', 'recovery'));

CREATE TABLE session_grant (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    token_hash      bytea NOT NULL UNIQUE,
    created_at      timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    used_at         timestamptz,
    used_ip         inet
);

CREATE INDEX session_grant_open_idx
    ON session_grant (user_id, expires_at)
    WHERE used_at IS NULL;
