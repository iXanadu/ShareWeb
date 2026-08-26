-- Share initial schema — spec Part 3 (with D-08 upload_session.version_id nullable, no cascade)

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TYPE artifact_kind AS ENUM ('bundle', 'page', 'document', 'image', 'video', 'file');
CREATE TYPE upload_state AS ENUM ('open', 'committing', 'committed', 'expired', 'aborted');

CREATE TABLE app_user (
    id              text PRIMARY KEY,
    email           citext NOT NULL UNIQUE,
    display_name    text,
    handle          citext UNIQUE,
    is_root         boolean NOT NULL DEFAULT false,
    quota_bytes     bigint NOT NULL DEFAULT 536870912000,
    storage_bytes   bigint NOT NULL DEFAULT 0,
    artifact_count  integer NOT NULL DEFAULT 0,
    settings        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_seen_at    timestamptz,
    disabled_at     timestamptz,
    CONSTRAINT handle_format CHECK (
        handle IS NULL OR handle ~ '^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$')
);
CREATE UNIQUE INDEX one_root_user ON app_user ((true)) WHERE is_root;

CREATE TABLE passkey_credential (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    credential_id   bytea NOT NULL UNIQUE,
    public_key      bytea NOT NULL,
    sign_count      bigint NOT NULL DEFAULT 0,
    transports      text[] NOT NULL DEFAULT '{}',
    aaguid          uuid,
    backup_eligible boolean NOT NULL DEFAULT false,
    backup_state    boolean NOT NULL DEFAULT false,
    name            text NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_used_at    timestamptz,
    revoked_at      timestamptz
);
CREATE INDEX passkey_credential_user_id_idx ON passkey_credential (user_id) WHERE revoked_at IS NULL;

CREATE TABLE recovery_code (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    code_hash       bytea NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    used_at         timestamptz,
    used_ip         inet
);
CREATE INDEX recovery_code_user_id_idx ON recovery_code (user_id) WHERE used_at IS NULL;

CREATE TABLE session (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    token_hash      bytea NOT NULL UNIQUE,
    passkey_id      text REFERENCES passkey_credential(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_seen_at    timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    ip              inet,
    user_agent      text,
    revoked_at      timestamptz
);
CREATE INDEX session_user_id_idx ON session (user_id) WHERE revoked_at IS NULL;

CREATE TABLE api_token (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    name            text NOT NULL,
    display_prefix  text NOT NULL,
    token_hash      bytea NOT NULL UNIQUE,
    scopes          text[] NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_used_at    timestamptz,
    last_used_ip    inet,
    expires_at      timestamptz,
    revoked_at      timestamptz
);
CREATE INDEX api_token_user_id_idx ON api_token (user_id) WHERE revoked_at IS NULL;

CREATE TABLE invite (
    id              text PRIMARY KEY,
    email           citext NOT NULL,
    handle          citext NOT NULL,
    token_hash      bytea NOT NULL,
    invited_by      text NOT NULL REFERENCES app_user(id),
    expires_at      timestamptz NOT NULL,
    accepted_at     timestamptz,
    revoked_at      timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX invite_email_open_idx ON invite (email) WHERE accepted_at IS NULL AND revoked_at IS NULL;

CREATE TABLE file (
    sha256          bytea PRIMARY KEY,
    size            bigint NOT NULL,
    ref_count       integer NOT NULL DEFAULT 0,
    has_brotli      boolean NOT NULL DEFAULT false,
    has_gzip        boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_ref_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX file_unref_idx ON file (last_ref_at) WHERE ref_count = 0;

CREATE TABLE artifact (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    name            text NOT NULL,
    title           text,
    description     text,
    kind            artifact_kind NOT NULL,
    live_version_id text,
    entry_path      text,
    ttl_expires_at  timestamptz,
    pinned          boolean NOT NULL DEFAULT false,
    view_count      integer NOT NULL DEFAULT 0,
    last_viewed_at  timestamptz,
    created_by_token text REFERENCES api_token(id),
    copied_from     text REFERENCES artifact(id),
    allow_framing   boolean NOT NULL DEFAULT false,
    csp             text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    trashed_at      timestamptz,
    deleted_at      timestamptz,
    CONSTRAINT name_format CHECK (
        name ~ '^[a-z0-9][a-z0-9._-]*(/[a-z0-9][a-z0-9._-]*)*$' AND length(name) <= 200)
);
CREATE UNIQUE INDEX artifact_user_name_idx ON artifact (user_id, name) WHERE deleted_at IS NULL;
CREATE INDEX artifact_user_updated_idx ON artifact (user_id, updated_at DESC)
    WHERE trashed_at IS NULL AND deleted_at IS NULL;
CREATE INDEX artifact_trashed_idx ON artifact (trashed_at) WHERE trashed_at IS NOT NULL;
CREATE INDEX artifact_ttl_idx ON artifact (ttl_expires_at)
    WHERE ttl_expires_at IS NOT NULL AND trashed_at IS NULL;
CREATE INDEX artifact_name_trgm ON artifact USING gin (name gin_trgm_ops);
CREATE INDEX artifact_title_trgm ON artifact USING gin (title gin_trgm_ops);

CREATE TABLE artifact_version (
    id              text PRIMARY KEY,
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    seq             integer NOT NULL,
    file_count      integer NOT NULL,
    total_bytes     bigint NOT NULL,
    entry_path      text,
    note            text,
    created_by_token text REFERENCES api_token(id),
    created_by_user  text REFERENCES app_user(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    deleted_at      timestamptz,
    UNIQUE (artifact_id, seq)
);
CREATE INDEX artifact_version_artifact_seq_idx ON artifact_version (artifact_id, seq DESC)
    WHERE deleted_at IS NULL;

ALTER TABLE artifact
    ADD CONSTRAINT artifact_live_version_fk
    FOREIGN KEY (live_version_id) REFERENCES artifact_version(id);

CREATE TABLE version_file (
    version_id      text NOT NULL REFERENCES artifact_version(id) ON DELETE CASCADE,
    path            text NOT NULL,
    sha256          bytea NOT NULL REFERENCES file(sha256),
    size            bigint NOT NULL,
    content_type    text NOT NULL,
    PRIMARY KEY (version_id, path)
);
CREATE INDEX version_file_sha256_idx ON version_file (sha256);

CREATE TABLE artifact_tag (
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    tag             citext NOT NULL,
    PRIMARY KEY (artifact_id, tag),
    CONSTRAINT tag_format CHECK (tag ~ '^[a-z0-9][a-z0-9 _-]{0,39}$')
);
CREATE INDEX artifact_tag_tag_idx ON artifact_tag (tag);

CREATE TABLE upload_session (
    id              text PRIMARY KEY,
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    version_id      text REFERENCES artifact_version(id),
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    state           upload_state NOT NULL DEFAULT 'open',
    manifest        jsonb NOT NULL,
    pending_count   integer NOT NULL,
    created_by_token text REFERENCES api_token(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    committed_at    timestamptz
);
CREATE INDEX upload_session_open_idx ON upload_session (state, expires_at) WHERE state = 'open';

CREATE TABLE share_link (
    id              text PRIMARY KEY,
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    token_hash      bytea NOT NULL UNIQUE,
    display_prefix  text NOT NULL,
    label           text,
    password_hash   text,
    expires_at      timestamptz NOT NULL,
    max_views       integer,
    view_count      integer NOT NULL DEFAULT 0,
    viewer_days     integer NOT NULL DEFAULT 0,
    last_viewed_at  timestamptz,
    created_by_user text REFERENCES app_user(id),
    created_by_token text REFERENCES api_token(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    revoked_at      timestamptz,
    CONSTRAINT expiry_required CHECK (expires_at IS NOT NULL)
);
CREATE INDEX share_link_artifact_idx ON share_link (artifact_id) WHERE revoked_at IS NULL;
CREATE INDEX share_link_expires_idx ON share_link (expires_at) WHERE revoked_at IS NULL;

CREATE TABLE share_grant (
    id              text PRIMARY KEY,
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    note            text,
    created_by      text NOT NULL REFERENCES app_user(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    revoked_at      timestamptz,
    UNIQUE (artifact_id, user_id)
);
CREATE INDEX share_grant_user_idx ON share_grant (user_id) WHERE revoked_at IS NULL;

CREATE TABLE recipient_session (
    id              text PRIMARY KEY,
    share_link_id   text NOT NULL REFERENCES share_link(id) ON DELETE CASCADE,
    token_hash      bytea NOT NULL UNIQUE,
    ip_hash         bytea,
    created_at      timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    revoked_at      timestamptz
);
CREATE INDEX recipient_session_link_idx ON recipient_session (share_link_id) WHERE revoked_at IS NULL;

CREATE TABLE link_viewer_day (
    share_link_id   text NOT NULL REFERENCES share_link(id) ON DELETE CASCADE,
    day             date NOT NULL,
    viewer_hash     bytea NOT NULL,
    PRIMARY KEY (share_link_id, day, viewer_hash)
);

CREATE TABLE audit_event (
    id              text PRIMARY KEY,
    user_id         text REFERENCES app_user(id) ON DELETE SET NULL,
    actor_type      text NOT NULL,
    actor_token_id  text REFERENCES api_token(id),
    action          text NOT NULL,
    target_type     text,
    target_id       text,
    target_label    text,
    ip              inet,
    user_agent      text,
    metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_event_user_idx ON audit_event (user_id, created_at DESC);
CREATE INDEX audit_event_action_idx ON audit_event (action, created_at DESC);
CREATE INDEX audit_event_target_idx ON audit_event (target_id);

CREATE TABLE view_daily (
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    day             date NOT NULL,
    source          text NOT NULL,
    share_link_id   text REFERENCES share_link(id) ON DELETE SET NULL,
    views           integer NOT NULL DEFAULT 0,
    viewers         integer NOT NULL DEFAULT 0,
    bytes_served    bigint NOT NULL DEFAULT 0,
    PRIMARY KEY (artifact_id, day, source, share_link_id)
);

CREATE TABLE idempotency_record (
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    endpoint        text NOT NULL,
    key             text NOT NULL,
    request_digest  bytea NOT NULL,
    status_code     integer NOT NULL,
    response_body   jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, endpoint, key)
);
CREATE INDEX idempotency_record_created_idx ON idempotency_record (created_at);

CREATE TABLE schema_migration (
    revision        text PRIMARY KEY,
    applied_at      timestamptz NOT NULL DEFAULT now()
);
