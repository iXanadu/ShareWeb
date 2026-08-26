# Part 7 — Sharing: Links, Passwords, Expiry, and Grants

## 7.1 Three levels, and the decision behind them

Every artifact sits at exactly one of three levels at any moment. The owner chooses, per
artifact, and can change it at any time.

| Level | Who gets in | How |
| --- | --- | --- |
| **Private** | The owner, and anyone they granted | Signed in. The default, and where most things stay |
| **Link** | Anyone holding the link | A 128-bit token in the URL. No sign-in |
| **Link + password** | Anyone holding the link *and* the password | The token plus a shared secret, given separately |

The interface never merges these into a toggle. Sharing is an object you create, name, list,
and revoke — the same way you'd think about handing out a key rather than flipping a switch.

**Every share link expires.** There is no permanent option, no configuration flag to enable
one, and no override in the API. This is guarantee P4 and it exists because of how links
actually leak: not by being guessed, but by being forwarded, saved into a folder, screenshotted,
and archived. A link that stopped working in February is a non-event in an archive discovered
three years later.

## 7.2 Links address the artifact, not the name

A share link points at `artifact_id`. Renaming an artifact, changing its title, or reposting new
content does not affect any live link — the recipient's URL keeps working and now shows the new
version. That is deliberate: a client given a link to a report should keep seeing the current
report, and the owner should be free to reorganise their own namespace without breaking
promises they made to other people.

The corollary is that a share link **follows content updates**. If an agent reposts an artifact
with something that should not have gone out, live links show it immediately. The mitigation is
that the artifact screen (§11.7) always shows live links prominently, so an owner reposting can
see who is currently watching.

## 7.3 Creating a link

```
POST /api/v1/artifacts/{name}/links
Authorization: Bearer shr_…            (requires scope share:create)
```

```json
{
  "ttl": "14d",
  "password": null,
  "label": "Fairfield listing team",
  "maxViews": null
}
```

| Field | Required | Default | Notes |
| --- | --- | --- | --- |
| `ttl` | no | `SHARE_DEFAULT_SHARE_TTL` (14d) | `30m`, `24h`, `14d`, `180d`. Capped at `SHARE_MAX_SHARE_TTL` |
| `password` | no | none | `true` to have one generated and returned once; a string to set your own (≥8 chars) |
| `label` | no | — | The owner's note about who this is for. Shown only to the owner |
| `maxViews` | no | none | Burn after N distinct viewer-days. Optional and rarely wanted |

**Response `201`:**

```json
{
  "id": "lnk_01JAV…",
  "url": "https://share.c52.com/s/9fq2n4kwPz3mXr7bTvQ8dL",
  "expiresAt": "2026-09-07T18:04:00Z",
  "hasPassword": true,
  "password": "civil-marmot-71",
  "label": "Fairfield listing team",
  "artifact": { "name": "postcal", "title": "Q4 posting calendar" },
  "warnings": []
}
```

The password is returned **once**, at creation, and never again by any endpoint. Losing it
means creating a new link.

**So is the URL.** Only the token's SHA-256 and an 8-character display prefix are stored, so
Share cannot show a link's full address after the response that created it. The dashboard keeps
it in memory for the current session and says plainly that it cannot be recovered later; the
remedy for a lost URL is a new link and a revoked old one. This is the same property that makes
a stolen database dump useless for reaching anyone's artifacts.

Server behaviour: require `share:create`; generate a 128-bit token from a CSPRNG and store only
its SHA-256; hash the password with argon2id (`m=64MiB, t=3, p=1`); write the audit event
`link.create` with actor, token ID, IP, artifact, expiry, and whether a password was set (P3);
email the owner if `settings.notifyOnShare` is true, which is the **default**.

That notification matters more than it looks. It means the owner learns, by email, every time
anything of theirs becomes reachable without a sign-in — including when an agent does it.

### 7.3.1 Token entropy

128 bits, base58-encoded to 22 characters, from `secrets.token_bytes`. Base58 rather than
base64url so the token survives being read aloud, double-clicked, or wrapped in an email
without ambiguous characters. At that size, guessing is not a threat model — the threat is
forwarding, which expiry handles.

## 7.4 Passwords on links

- argon2id, never retrievable, write-only through the API.
- Generated passwords are `{adjective}-{noun}-{2 digits}` from curated word lists — readable
  over the phone, roughly 24 bits, which is adequate because attempts are rate-limited to 10
  per IP per hour and 50 per link per hour and the owner can revoke instantly.
- Owner-supplied passwords need 8 characters and nothing else. No composition rules.
- The gate is served at `401` on the link's own path and posts to `/s/{token}/unlock`,
  accepting form-encoded or JSON, so it works with JavaScript disabled.
- Changing or removing a link's password revokes every recipient session on that link (P9).

```
PATCH  /api/v1/links/{id}     { "password": "new-secret", "ttl": "7d", "label": "…" }
DELETE /api/v1/links/{id}                                        → revoke, immediate
GET    /api/v1/artifacts/{name}/links                            → list, owner only
```

Extending adds to the current expiry rather than starting from now, so an extension can never
silently shorten. **The cap applies to total lifetime** — `expires_at − created_at` may never
exceed `SHARE_MAX_SHARE_TTL` — so repeated extensions cannot walk a link past the ceiling. Revocation deletes recipient sessions and purges the Redis cache in the same
call — the next request from anyone holding that link is a `410`.

## 7.5 Expiry

The worker sweeps every 5 minutes:

```sql
UPDATE share_link SET revoked_at = now()
WHERE revoked_at IS NULL AND expires_at <= now()
RETURNING id, artifact_id;
```

For each: delete recipient sessions, purge the cache, audit `link.expired` with
`actor_type='system'`, and email the owner (§12.9 `link_ended`).

Because the sweep lags by up to 5 minutes, **`/internal/authorize` also checks `expires_at`
inline on every request** and refuses immediately when it has passed, regardless of what the
row says. The sweep is bookkeeping; the inline check is enforcement. T-EXP-02 verifies a link
is dead the second after expiry even if the sweep has not run.

Twenty-four hours before expiry the owner gets an email with a one-click extend. Links expiring
within 48 hours appear in a dashboard banner (§11.5).

## 7.6 What a recipient can learn

A share link deliberately reveals as little as possible:

- The URL contains no owner handle, no artifact name, and no artifact ID.
- The password gate names nothing — not the artifact, not who sent it, not the file type.
- Assets load under `/s/{token}/…`, so a recipient viewing a bundle never sees the artifact's
  real path.
- A revoked or expired link returns `410 link_expired` **only on the link's own entry page**,
  with a page that says the link is no longer active and nothing else. Everywhere else in the
  system an inaccessible thing is a `404` (P1); this is the one exception, because a recipient
  who was legitimately given a link benefits from knowing it died rather than being told it
  never existed, and the disclosure is limited to "some link that used to work no longer does".

## 7.7 Grants: sharing with another user

Separate from links, and safer, because there is no bearer token to forward.

```
POST   /api/v1/artifacts/{name}/grants     { "handle": "sarah", "note": "the Q4 draft" }
GET    /api/v1/artifacts/{name}/grants
DELETE /api/v1/grants/{id}
```

The artifact appears in Sarah's **Shared with me** (`GET /api/v1/artifacts?shared=true`) and
she reaches it at its canonical URL, `/~robert/postcal`, signed in as herself. She can view,
download, and copy it. She cannot edit, rename, delete, share it onward, or see anything else
in Robert's space.

Revoking a grant takes effect on her next request.

### 7.7.1 Shared is not permanent

The owner can delete the artifact at any moment and the grantee's access goes with it. That is
correct — it is the owner's file — and it means "shared with me" is a view, not a possession.
So the grantee gets a **Save a copy** action (§5.10), which pulls the artifact into their own
space as their own artifact, referencing the same stored bytes and therefore costing nothing.

The dashboard puts that action on every shared item precisely because the failure mode is
silent: a link that will stop working someday looks identical to one that will not.

## 7.7.2 One definition of "live"

A share link is **live** when `revoked_at IS NULL AND expires_at > now()`. A grant is live when
`revoked_at IS NULL`. That single predicate is used everywhere — the authorize path, the expiry
sweep, the derived `visibility` field, the `hasLink` search filter, and every count shown in the
dashboard. There is no second, looser notion of live anywhere in the system.

## 7.8 Visibility as displayed

The `visibility` field on an artifact is derived, never stored:

| Value | Condition | Shown as |
| --- | --- | --- |
| `private` | No live links, no live grants | Private |
| `granted` | Live grants, no live links | Shared with *n* people |
| `shared` | At least one live link | Link active · expires *date* |

When several apply, `shared` wins, because a live link is the widest thing true about the
artifact and the owner should see the widest thing first.

## 7.9 What an agent can and cannot do

By default an agent token holds `artifacts:read` and `artifacts:write` and **not**
`share:create`. It can post, overwrite, tag, and trash its own owner's artifacts. It cannot
create a share link, cannot grant to another user, and cannot extend an existing link.

An agent asked to "share this with my client" therefore fails with `403 insufficient_scope`
naming `share:create`, and the correct response is for it to hand the owner a dashboard link
to do it. That is the intended shape: putting something in front of a person outside the
system is a human decision.

Tokens can be granted `share:create` deliberately, in the dashboard, with a warning attached
(§12.6). Doing so is audited.

**Scopes constrain tokens, not people.** A signed-in user always holds full authority over
their own space, including sharing — there is no scope on a session and no dashboard state in
which the owner is refused an action on their own artifact. Scopes exist to limit what an agent
can do while acting as its owner.

## 7.10 Sharing error codes

| HTTP | Code | Meaning |
| --- | --- | --- |
| 403 | `insufficient_scope` | Token lacks `share:create` |
| 403 | `not_your_artifact` | Sharing something in another space |
| 404 | `link_not_found` | No such link, or already revoked |
| 404 | `grant_not_found` | No such grant |
| 404 | `user_not_found` | No user with that handle to grant to |
| 409 | `grant_exists` | Already shared with that user |
| 409 | `cannot_grant_to_self` | Granting to your own account |
| 410 | `link_expired` | Link past expiry or revoked (entry page only) |
| 422 | `ttl_too_long` | Beyond `SHARE_MAX_SHARE_TTL` |
| 422 | `password_too_short` | Under 8 characters |
| 422 | `artifact_trashed` | Cannot share something in the trash |
| 429 | `rate_limited` | §10.2 |
