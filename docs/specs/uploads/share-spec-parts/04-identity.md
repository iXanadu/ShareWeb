# Part 4 — Identity: Passkeys, Sessions, Tokens, and Recovery

## 4.1 Three credentials, no passwords

| Credential | Held by | Used for | Form |
| --- | --- | --- | --- |
| **Passkey** | People | Signing in to the dashboard | WebAuthn, in 1Password or a platform authenticator |
| **API token** | Agents | Everything on the HTTP API and MCP endpoint | `shr_` + 43 chars base64url |
| **Recipient session** | Someone with a share link | Viewing one artifact | Cookie, scoped to that link's path |

**There is no user password anywhere in the system.** No storage, no strength rules, no
rotation, no reset-by-email flow. That last one is the point: a password reset is a path that
bypasses the password entirely, and it is where most real account takeovers happen. Deleting
the password deletes the reset flow with it.

Share-link passwords (§7.4) are a different thing — a shared secret protecting one link, not an
identity — and they are the only argon2 hashes in the system apart from recovery codes.

## 4.2 Passkey registration

WebAuthn, with `SHARE_HOST` as the Relying Party ID. Implementation uses a maintained library
(`webauthn` for Python); nothing here reimplements the cryptography.

```
POST /auth/passkey/register/begin      (session, or a valid invite/bootstrap token)
 ← 200 { publicKey: { challenge, rp, user, pubKeyCredParams,
                      authenticatorSelection: { residentKey: "preferred",
                                                userVerification: "preferred" },
                      excludeCredentials: [ …already-registered IDs… ],
                      attestation: "none", timeout: 120000 } }

POST /auth/passkey/register/finish     { credential: <attestation response>, name: "1Password" }
 ← 201 { id: "pky_…", name: "1Password", createdAt: "…" }
```

Decisions and why:

- **`attestation: "none"`.** Share does not care which authenticator model was used, and
  requesting attestation adds a verification burden and a privacy signal for no benefit on a
  single-operator instance.
- **`residentKey: "preferred"`.** Discoverable credentials give the usernameless sign-in flow —
  land on the sign-in screen, tap, done, no email typed. 1Password supports them.
- **`userVerification: "preferred"`, not `"required"`.** Required breaks security keys without
  a PIN and adds friction for a threat model where the device is already the operator's.
- **`excludeCredentials`** prevents registering the same authenticator twice, which otherwise
  produces confusing duplicate entries.
- Every credential gets a **name**, defaulted from the AAGUID against a known-authenticator list
  and editable. "Which of these three is my laptop" needs an answer before revoking one.

**Registering a second passkey is part of setup, not an optional extra.** The first-run
checklist (§12.3) does not complete until at least two are registered or the operator
explicitly dismisses it. Recovery is easy with two keys and unpleasant with one.

## 4.3 Sign-in

```
POST /auth/passkey/login/begin         { }            ← no email needed
 ← 200 { publicKey: { challenge, rpId, userVerification: "preferred",
                      allowCredentials: [] , timeout: 120000 } }

POST /auth/passkey/login/finish        { credential: <assertion response> }
 ← 200 { user: { id, email, handle, displayName, isRoot } }
   Set-Cookie: share_s=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=2592000
```

`allowCredentials` is empty, so the browser offers whichever discoverable credential matches —
this is the one-tap path. Verification:

1. Look up `passkey_credential` by the returned credential ID. Unknown → `401 invalid_credential`.
2. Verify the signature against the stored COSE key, the challenge from Redis (single-use, then
   deleted), the origin, and the RP ID.
3. **Signature counter check.** If the stored `sign_count` is non-zero and the asserted count is
   not greater, treat it as a possible cloned authenticator: reject with
   `401 credential_counter_regressed`, revoke nothing automatically, write an audit event, and
   email the owner. Many authenticators (1Password included) always report zero, so the check
   only applies when the stored count is already non-zero.
4. Update `sign_count`, `last_used_at`.
5. Create the session.

Rate limits: 20 login-begin per IP per 10 minutes, 10 finish attempts per IP per 10 minutes.
Brute force is not a meaningful threat against a public-key signature, so these exist to stop
noise rather than to hold a line.

## 4.4 Sessions

| Property | Value |
| --- | --- |
| Cookie | `share_s`, `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, host-only |
| Lifetime | 30 days sliding, 90 days absolute |
| Extension | `expires_at` extends on any request more than an hour since the last extension |
| CSRF | Double-submit: readable `share_csrf` cookie plus `X-Share-CSRF` header on every unsafe method; mismatch is `403 csrf_failed` |
| Listing | `GET /api/v1/auth/sessions` — created, last seen, IP, coarse user agent, which passkey, current flag |
| Revocation | `DELETE /api/v1/auth/sessions/{id}`, or sign out everywhere (§11.19) |

Revoking a passkey revokes every session created with it. Disabling a user revokes all of
theirs.

## 4.5 Recovery

The one place passkeys are genuinely harder than passwords, handled in three layers.

**Layer 1 — more than one passkey.** 1Password syncs across the operator's devices; a second
platform passkey on another machine covers the vault being unavailable. This is the layer that
handles almost every real case, which is why §4.2 pushes it during setup.

**Layer 2 — a recovery code.** Generated at bootstrap and regenerable at any time. Twenty-four
characters, Crockford base32, shown once, hashed with argon2id.

```
POST /auth/recovery/use      { "email": "you@c52.com", "code": "…" }
 ← 200  a session, plus a forced prompt to register a new passkey before anything else
```

Rules: single use; using one invalidates all others and issues a fresh one; the session it
creates is limited to 30 minutes and can do exactly two things — register a passkey and list
existing ones; using a code emails the owner and writes an audit event; 5 attempts per email
per hour, 20 per IP per day.

**Layer 3 — the server.** It is the operator's machine, which no hosted service can offer:

```
sharectl grant-session --email you@c52.com --minutes 30
  → prints a one-time URL that establishes a session on first use
```

Requires root on the box. Audited as `auth.session_granted` with `actor_type='system'`. This is
the true backstop and it means the operator can never be permanently locked out of their own
files while they still have SSH.

**What deliberately does not exist:** email-link recovery. Adding it would reintroduce exactly
the bypass path that removing passwords eliminated.

## 4.6 API tokens

```
Authorization: Bearer shr_7Fq2mR8v…
```

Resolution, constant-time at every step: parse, `SELECT … WHERE token_hash = sha256(token)`,
reject unknown / revoked / expired / disabled-owner with an identical `401 invalid_token` and
identical timing — never distinguish "revoked" from "wrong". `last_used_at` and `last_used_ip`
are buffered in Redis and flushed every 60 seconds rather than written on the request path.

Because tokens are 256-bit random values, plain SHA-256 is the correct storage function;
argon2 exists to slow guessing of low-entropy secrets and would only add latency.

Resolved tokens cache at `sh:tok:{sha256hex}` for 30 seconds. **Revocation bypasses the cache**
with an immediate `DEL`.

### 4.6.1 Scopes

| Scope | Grants |
| --- | --- |
| `artifacts:read` | List, read metadata, download files, read versions, search |
| `artifacts:write` | Create, overwrite, rename, tag, set TTL, trash, restore |
| `artifacts:delete` | Purge from trash — permanent deletion, separate from `write` |
| `share:create` | Create, extend, and revoke share links; grant to other users |
| `account:read` | Read own profile, quota, tokens, sessions |
| `account:admin` | Create tokens, invite users, change settings |

Defaults:

- **Agent-issued tokens** (§4.6.2) get `artifacts:read`, `artifacts:write`. Nothing else.
- `share:create` is never granted automatically. An agent that can post cannot put anything on
  the public internet, which is what makes P3 meaningful.
- `artifacts:delete` is separate from `write` so that a looping agent's worst case is a full
  trash rather than an empty account.

Enforcement is a FastAPI dependency, `require(scope)`. A missing scope returns
`403 insufficient_scope` **naming the scope in the body**, so an agent can tell its human
exactly what to add rather than retrying.

### 4.6.2 How an agent gets a token

Two paths, both requiring a human at some point.

**Dashboard** (§11.18). The owner creates a named token, ticks scopes, copies it once. The
`share:create` checkbox carries its own warning line (§12.6).

**Device-code flow**, for an agent that wants to bootstrap itself:

```
POST /api/v1/auth/device/start   { "name": "claude-code@hosta" }
 ← 200 { deviceCode, userCode: "QRTZ-8H4M", verifyUrl: "https://share.c52.com/~/authorize",
         expiresIn: 600, interval: 5 }

  (the agent prints: "Open https://share.c52.com/~/authorize and enter QRTZ-8H4M")

POST /api/v1/auth/device/poll    { "deviceCode": "…" }
 ← 428 { "error": { "code": "authorization_pending" } }        … then, once approved:
 ← 200 { "token": "shr_…", "tokenId": "shr_01J…", "scopes": ["artifacts:read","artifacts:write"] }
```

The human signs in with their passkey, sees which agent and machine is asking, and approves —
scoped, always, to the agent default set. Elevating a token is a separate deliberate act in the
dashboard.

This replaces the email-code flow of the earlier draft. It is better here because the approval
happens in an authenticated session where the human can see what they are granting, rather than
by typing a code that arrived in an inbox.

## 4.7 Recipient sessions

Someone holding a share link is not a user and never becomes one.

- Cookie `share_r_{first 8 chars of the token}`, `Path=/s/{token}`, `HttpOnly`, `Secure`,
  `SameSite=Lax`. Path-scoped, so a recipient holding three links keeps three independent
  cookies and none is ever sent to another link.
- Value is `{recipientSessionId}.{HMAC-SHA256(secret_key, id)}`. The MAC is checked first
  (cheap, constant-time), then the row, cached 300 s.
- Lifetime: 24 hours, never beyond the share link's own expiry.
- **A recipient session authorises nothing but viewing that one artifact through that one
  link.** It is not accepted by `/api/v1/*`, `/~/*`, or `/mcp`. Tested by T-SEC-07.

## 4.8 Invites

Only the root user, or a user with `account:admin`, may invite.

```
POST /api/v1/invites    { "email": "sarah@…", "handle": "sarah" }
```

The invitee receives a link, opens it, registers a passkey, and lands in their own empty space.
No password is ever created because none exists. Acceptance creates the user and audits
`user.create`. Invite tokens live 7 days.

Handles are claimed at invite time so two pending invites cannot collide, and are subject to
the reserved list in §6.3.

## 4.9 Error taxonomy

| HTTP | Code | When |
| --- | --- | --- |
| 401 | `invalid_token` | Missing, malformed, unknown, revoked, or expired API token |
| 401 | `invalid_credential` | Unknown passkey credential ID |
| 401 | `credential_counter_regressed` | Possible cloned authenticator; owner emailed |
| 401 | `webauthn_verification_failed` | Signature, challenge, origin, or RP ID mismatch |
| 401 | `session_expired` | Dashboard cookie past expiry |
| 401 | `recipient_auth_required` | Share link needs its password |
| 401 | `recipient_auth_failed` | Wrong share-link password |
| 403 | `insufficient_scope` | Valid token, missing scope; body names it |
| 403 | `csrf_failed` | Unsafe dashboard request without a matching CSRF pair |
| 403 | `wrong_credential_class` | Recipient session or share token presented to the API |
| 410 | `invite_expired` | Invite past its TTL |
| 428 | `authorization_pending` | Device-code poll before approval |
| 429 | `rate_limited` | Any bucket in §10.2 |

Every authentication failure writes an audit event with source IP and, where parseable, the
token's `display_prefix`. Repeated failures trip the auth bucket and surface on the security
screen (§11.20).

## 4.10 Secret-handling rules

1. No secret is logged at any level. The logging filter redacts anything matching `shr_`,
   `Bearer `, or a cookie value.
2. Error responses never echo a submitted credential.
3. Tokens and recovery codes are displayed exactly once, at creation. `display_prefix` is
   stored so the UI and audit log can name a token without holding it.
4. `sharectl` refuses to print a full token when stdout is not a TTY unless `--force` is passed.
5. Backups contain hashes and public keys only. There is no secret in the database whose
   disclosure grants access — a stolen dump yields no usable credential, which is a direct
   consequence of having no passwords and no stored API secrets.
