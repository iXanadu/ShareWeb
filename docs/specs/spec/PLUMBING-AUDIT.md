# Plumbing audit — Parts 2 to 10, 14, 15

Read in full, against each other and against `USE-CASES.md`. This is the second pass; the first
re-cut Parts 11 and 13. Findings are ordered by what they cost if a build team hits them cold.

## Verdict first

**The plumbing is sound and the build team can start.** The access model is four lines and has no
fifth case. The privacy guarantees are stated, numbered, and each has a test. The error taxonomy
is coherent across seven documents. The three-phase post, content-addressed store, reference
counting, and the `forward_auth` contract are all internally consistent and thought through past
the happy path.

That is a different quality of work from what happened in Parts 11 and 13, and the reason is
visible: **Part 14 §14.24 already did this audit.** Nineteen ambiguities, A1–A19, each with the
conflicting sections named, a rule applied, and a resolution — and the resolutions were folded
back into Parts 2–10 rather than left as a list. A9 in particular caught an SSRF surface
(`share_post_from_urls`) that flatly contradicted §2.9's "no outbound requests" claim, and Part 9
now has no such tool. Whoever wrote the test plan was the adult in the room.

So this audit is narrower than expected. It has five things that will bite, one structural gap,
seven A-resolutions that were only half-applied, and some housekeeping.

---

> **All five in §1 and all seven in §3 are now fixed in the files in this folder**, and recorded as
> D-07 to D-13 in `DECISIONS.md`. They are kept here with their reasoning, because a developer who
> finds the fix without the reason tends to undo it. §2's gap is the one thing left open, and §5.13
> of Part 5 now states the four parts of it that are not free choices.

## 1 · Five things that will bite

### 1.1 `sh:tok:` means two different things, with two different TTLs

**Sections:** §2.4.2, §3.10, §4.6

§2.4.2 and §3.10 both define `sh:tok:{sha256}` as **share-link** validity, 300 s. §4.6 says
resolved **API tokens** cache at `sh:tok:{sha256hex}` for **30 s**. Same key namespace, two
credential classes, and a 10× TTL disagreement.

Nothing here is exploitable — the values are keyed by the hash of the presented secret, so a
collision requires the hash of a share token to equal the hash of an API token. But two credential
classes sharing a cache namespace is the kind of thing that becomes exploitable three refactors
later, and the TTL contradiction means one of the two numbers is wrong in a document a developer
will read as authoritative.

**Fixed.** `sh:atok:` for API tokens at 30 s, `sh:ltok:` for share links at 300 s, in §2.4.2,
§3.10 and §4.6. Revocation matters more on an API token, hence the shorter of the two.

### 1.2 An expired upload session cannot return `upload_session_expired`

**Sections:** §5.7, §3.4, §5.12

§5.7: the worker "marks `open` sessions past `expires_at` as `expired` **and deletes the draft
version row**". But `upload_session.version_id` is `NOT NULL REFERENCES artifact_version(id) ON
DELETE CASCADE`. Deleting the version deletes the session row with it. So the `expired` state can
never be observed, and §5.7's own next sentence — "committing an expired session returns
`409 upload_session_expired`" — is unreachable: the commit gets a `404`.

An agent whose upload session lapsed therefore receives the wrong error and cannot tell "your
window closed, re-declare" from "that name doesn't exist". §5.7's recovery advice depends on it
telling them the former.

**Fixed.** `upload_session.version_id` is nullable and no longer cascades; the worker clears it,
then deletes the orphaned draft version. §5.7 now says so, and `409 upload_session_expired` is
reachable.

### 1.3 Two `Cache-Control` rules collide on a hashed asset behind a share link

**Section:** §6.6.5

The table gives "any file reached through a share link" → `private, no-store`, and
"immutable-looking asset (content hash in the filename)" → `private, max-age=31536000, immutable`.
A bundle's `app.a1b2c3.js` reached through a share link matches both. The rules are listed without
precedence.

This matters because the `no-store` row has a stated security purpose — "prevents a borrowed
browser or an intermediary from retaining a document after the link dies" — and the immutable row
silently defeats it for exactly the assets a page loads most of.

**Fixed.** §6.6.5 now states that the share-link row wins every collision: `no-store` for
everything under `/s/*`, full stop.

### 1.4 The device-code flow has no approve or deny endpoint

**Sections:** §4.6.2, §11.26

§4.6.2 specifies `POST /api/v1/auth/device/start` and `POST /api/v1/auth/device/poll`. The screen
that a human actually uses (11.26) needs three more: a lookup that turns a typed
`QRTZ-8H4M` into the pending request's name, source IP and requested scopes; an approve; and a
deny. None exists in any part.

This is the only place in the spec where a whole flow is missing its middle. It is also Phase 1
work, so the build team hits it early.

**Fixed.** §4.6.2 now specifies `lookup`, `approve` and `deny`, session-authenticated, with the
approve response deliberately not carrying the token — it goes only to the polling agent, so the
secret never touches the browser that authorised it.

### 1.5 `install.sh` is served from a path nothing routes and nothing reserves

**Sections:** §9.8, §2.4, §6.3

§9.8 documents `https://share.c52.com/install.sh` as the CLI installer. The Caddyfile routes
`/~/*`, `/api/*`, `/mcp`, `/mcp/*`, `/auth/*`, `/s/*` and `/robots.txt` to the API, and everything
else to the artifact handler — so `/install.sh` resolves as an artifact name, fails, and 404s. It
is also absent from §6.3's reserved list, so an artifact can legitimately claim it.

Same applies to `/.well-known/mcp` (§9.8): `.well-known` is reserved in §6.3 but has no Caddy
route, and §6.4 rule 7 explicitly permits `/.well-known/` **inside** an artifact — which is the
right behaviour for artifact content and the wrong one for the instance's own descriptor.

**Fixed.** Both routes added to the Caddyfile in §2.4; `install.sh` added to §6.3's reserved list.
Part 14's F2 fuzzer ("no accepted name is captured by any Caddy route
prefix") should catch the class going forward — note it currently would have caught 1.5 in the
opposite direction and did not run against these two paths.

---

## 2 · The structural gap: the dashboard's API is not specified

Parts 4–10 specify the **agent-facing** API thoroughly — every field, every error code, every
limit. The **dashboard-facing** API is specified almost nowhere, and Part 11 calls it constantly.

Endpoints Part 11 depends on that no part in 2–10 defines:

| Endpoint | Needed by |
| --- | --- |
| `GET /api/v1/tags` | 11.5 filter bar |
| `GET /api/v1/tokens`, `POST`, `PATCH /{id}`, `DELETE /{id}` | 11.18, 11.6 |
| `GET`/`PATCH /api/v1/settings` | 11.21, and every default the product reads |
| `GET /api/v1/auth/passkeys` | 11.3, 11.19 |
| `GET /api/v1/auth/sessions` | 11.19 (§4.4 names it in a table but never specifies it) |
| `GET /api/v1/users` | 11.12 grant typeahead, 11.22 |
| `GET /api/v1/invites`, `GET /api/v1/invites/{token}` | 11.22, 11.4 |
| `GET /api/v1/artifacts/{name}/archive` | 11.7 "Download all" |
| `POST /api/v1/auth/device/{lookup,approve,deny}` | 11.26 — see 1.4 |

And four response shapes that are referenced by field name but never defined:

- **`GET /api/v1/status`** — §2.8 gives it one line. Part 11 reads `storageBytes`, `quotaBytes`,
  `artifactCount`, `trashBytes`, `staleBytes`, `diskFreeBytes`, `lastBackupAt`, `queueDepths`,
  `version`, `uptimeSeconds`, `migrationRevision`, and a stale count, across five screens.
- **`GET /api/v1/artifacts/{name}/links`** — §7.4 lists it as "list, owner only" with no shape.
  11.12 needs ten fields from it.
- **`GET /api/v1/artifacts/{name}/activity`** — §8.8 describes it in prose; 11.7 enumerates
  fourteen entry types.
- **The `settings` JSONB schema** — `app_user.settings` is `jsonb NOT NULL DEFAULT '{}'`, and the
  only enumeration of its keys anywhere is a table on a screens page (11.21). Defaults that the
  API enforces (`defaultShareTtl`, `versionRetention`, `notifyOnShare`) are therefore specified in
  the frontend document.

**This is the same boundary error as Parts 11/13, mirrored.** There, appearance leaked into the
spec. Here, API contract leaked into the screens.

**Partly closed, deliberately.** `05a-dashboard-api.md` is the build team's to write alongside the
code — it is CRUD over tables that already exist, and a shape specified by someone not building it
is wrong in ways nobody notices until it ships. But four of these are not free choices, because a
screen's honesty depends on what comes back, so **§5.13 of Part 5 now states them as requirements**:
the `settings` keys with their defaults, what `GET /status` must report, what a share-link list must
carry, and what an activity entry may never contain. Everything around those is the team's.

---

## 3 · A-resolutions that were only half-applied

§14.24's resolutions were mostly folded back. These seven were not, so the contradiction they
resolved is still live in the document a developer reads:

| # | Resolved | Still missing |
| --- | --- | --- |
| **A10** | `allowFraming` and `csp` become real artifact properties | §3.4's `artifact` table has no `allow_framing` or `csp` column, and §5.8's item shape omits both. They appear only in §5.4's field table and §5.9's `PATCH` list. |
| **A11** | Warnings get a catalogue "in §5.12 alongside the errors" | No catalogue exists. §5.4 points at §12.6 instead — two different homes named for the same list, and neither contains it. Nine warning codes are in flight (`shadowing_name`, `no_entry_point`, `ttl_with_live_links`, `entry_path_not_found`, `framing_ignored_password_link`, `possible_credential_form`, `archive_ratio_exceeded`'s advisory sibling, plus the two in §8.5). |
| **A15** | Link-token generation retries on an 8-char prefix collision | Neither §7.3 nor §7.3.1 nor §4.7 mentions the retry. |
| **A16** | View hashes are `HMAC(view_salt ‖ date, artifact_id ‖ ip)`; recipient hashes use `share_link_id` | §3.8 and §10.6 still say only "a salted daily hash". The unlinkability claim in §10.6 is untrue without the target in the message. |
| **A8** | The collection query keeps `ref_count <= 0`; a nightly log line makes the leak visible | §3.6's prose still says the counter "is advisory — the authoritative check at sweep time is a `NOT EXISTS`", which the query contradicts. The log line is not specified anywhere. |
| **A2** | `url` is the short form only for the owning root user; recipients get no `url` at all | Not recorded in §5.8, §6.2 or §7.7. |
| **A18** | Part 16 governs phase membership once written | §14.21 still opens "Part 16 does not exist at the time of writing." Part 16 exists. |

**All seven are now applied** in the sections named above. Each was a place where a careful
developer would otherwise have found two answers and picked one.

---

## 4 · Redis holds two things the spec says it doesn't

§3.10 opens: "Nothing durable lives here. A flush costs at most 60 seconds of view counts and
resets rate limits." Two things in the table contradict that, and neither is in the table:

**Idempotency records.** §5.1.3 caches the full serialised response for 24 hours in Redis, keyed
`(user, endpoint, key)`. A flush therefore turns a replayed `POST /artifacts` into a second
artifact — exactly the duplicate 11.13.8's network-failure retry path relies on not happening.
**Fixed:** moved to Postgres as `idempotency_record` (§3.9.1).

**`share_link.viewer_days` inputs.** A4 made `maxViews` enforce against an exact count maintained
by "a Redis set per link-day". That is enforcement data for a security-relevant ceiling. A flush
resets a burn-after-N link's count to zero, and the link outlives its limit.

Also absent from §3.10's table, which presents itself as complete: the API-token `last_used_at`
buffer (§4.6) and the recipient-session cache (§4.7). **Both added**, along with the split token
namespaces, and §3.10's opening now states the rule that produced the two moves above: **if it
enforces something, it is not in Redis.**

---

## 5 · Housekeeping

- **11.28 is assigned to two phases.** Part 16 lists it in Phase 3's screen set (§16.4) and again
  as "Instance status screen" in Phase 4's table (§16.5). Phase 3 is right — the reduced non-root
  view is useful as soon as there is a second user. **Fixed** — the Phase 4 row is gone.
- **The 10 GB anomaly threshold equals the artifact ceiling.** §10.4 raises "bytes posted in an
  hour by one token > 10 GB"; `SHARE_MAX_ARTIFACT_BYTES` is exactly 10 GB. One legitimate
  maximum-size post trips the alert. Raise the threshold to 25 GB or make it 3× the artifact
  ceiling, or the first video someone posts trains the operator to ignore the email. **Fixed** at
25 GB.
- **`artifact` has no `created_by_user` column.** §3.4 has `created_by_token` only, while §5.8's
  item shape returns `createdBy: {type: 'user' | 'token'}`. `artifact_version` has both. So
  "posted by a human" is inferred from a null token, which works but is undocumented and makes
  11.5's agent filter (`?token=`) subtly asymmetric.
- **Three view counters, one name.** `artifact.view_count`, `share_link.view_count`, and
  `view_daily.views` all exist; A4 defined the middle one. The other two are never related to each
  other — is the artifact's counter the sum of its daily rows, and does it include owner views?
  11.7 shows both an artifact `viewCount` and per-link ones on the same screen.
- **`favicon.ico` is reserved but unrouted** (§6.3 vs §2.4). Harmless; it 404s either way. Worth a
  route so it 404s cheaply instead of running the full resolver.

---

## 6 · What I looked for and did not find

Stated so the absence is on the record rather than assumed:

- **No hole in the access model.** `can_view` has four cases and no bypass. No `userId` on any
  write. No admin override, anywhere, including for root. Searched for one specifically; it is not
  there.
- **No unversioned destructive path.** Every delete is soft first, except `?purge=true`, which is
  scoped, audited, and tested against P8.
- **No permanent-link escape hatch.** `expires_at` is `NOT NULL` with a `CHECK`, there is no
  config variable, and §2.7 says so explicitly. P4 holds at the schema level, which is the only
  level that counts.
- **No content inference.** `kind` derives from the manifest's shape, never from opening a file.
  Search is trigram-over-metadata. No thumbnail, poster frame, or probe anywhere. P5 holds.
- **The error codes reconcile.** Every code in §4.9, §5.12, §6.8, §7.10, §8.9 and §10.9 is
  distinct, and the ones Part 11 handles all exist. This is unusual and worth saying.

---

## 7 · What to hand the build team

Six things, in this order.

**1 · `README.md`, `USE-CASES.md`, `01-overview.md`.** Read together, in that order, by everyone
before any code. Twenty minutes. The overview carries the privacy model and the numbered
guarantees; the use cases say what must be true at the end of each flow; the README says which
document wins when two disagree.

**2 · `16-roadmap.md` as the work breakdown.** It is the best-structured document in the set: four
phases, each with a table of what to build and a section reference for each row, plus exit
criteria that are testable rather than aspirational. Phase 1 is genuinely shippable. Give a team
Phase 1's table and they know what this week is.

**3 · Parts 2–10 as the implementation contract, with §14.24 read alongside.** Do not hand Parts
2–10 without §14.24 — it is where the nineteen contradictions were resolved, and a developer who
reads only the body will re-derive several of them. Then fix the five in §1 above and the seven
half-applied resolutions in §3, which is perhaps a day of editing, before the first sprint rather
than during it.

**4 · `14-testing.md` as the definition of done, and the release gate as written.** "Every
`T-PRIV-*` and every `@security` test passes, coverage thresholds are met, and the manual
checklist is signed with a date and a name." That gate is correct as it stands. The negative-case
rule — three mandatory negative tests per endpoint — is what will actually keep this honest.

**5 · Part 11 for behaviour, `12-copy.md` for words, the design output for appearance.** With the
precedence rule from the README on top. The frontend developer needs all three and should never
be reading a pixel value out of a spec.

**6 · `DECISIONS.md`, open and appended to.** §1.9's rule — resolve toward less exposure and no
new configuration surface, then record it — is the reason this document survived being written by
an agent. It should keep running during the build.

**What the team writes first:** `05a-dashboard-api.md` (§2), alongside the code, after reading
§5.13 for the four shapes that are constrained.

**What not to do:** do not rewrite Parts 2–10. They are better than they look from the outside,
and the instinct to start over after finding Part 13 would throw away the good ninety per cent
with the bad ten.
