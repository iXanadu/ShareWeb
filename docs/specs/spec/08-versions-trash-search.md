# Part 8 — Versions, Trash, Retention, and Search

## 8.1 Why these four are one part

They are the answer to a single question: *agents have full control over their own space, so
what stops a bad loop from destroying a year of work?* Versions make overwrites reversible,
trash makes deletes reversible, retention keeps both from becoming unbounded, and search makes
the result findable. Take any one away and full agent CRUD stops being safe.

## 8.2 Versions

Every commit creates an immutable version with a human-facing sequence number starting at 1.
Overwriting `postcal` produces version 2; version 1 remains, complete, and viewable.

```
GET /api/v1/artifacts/{name}/versions
```

```json
{
  "items": [
    { "id": "ver_01JAV…", "seq": 2, "isLive": true,
      "fileCount": 3, "totalBytes": 112743, "note": "November slots",
      "createdAt": "2026-08-24T18:04:00Z",
      "createdBy": { "type": "token", "id": "shr_01J…", "name": "grokbot@macmini" },
      "changes": { "added": 0, "modified": 1, "removed": 0 } }
  ],
  "nextCursor": null, "hasMore": false
}
```

`changes` compares manifests against the preceding version and is cached for 24 hours.

```
GET  /api/v1/artifacts/{name}/versions/{id}/files
GET  /api/v1/artifacts/{name}/versions/{id}/files/content?path=/index.html
POST /api/v1/artifacts/{name}/versions/{id}/restore   { "note": "back out the bad run" }
POST /api/v1/artifacts/{name}/versions/{id}/pin
DELETE /api/v1/artifacts/{name}/versions/{id}
```

**Restore** creates a *new* version whose manifest equals the old one, with the sequence
continuing — restoring version 1 while 3 is live produces version 4. History stays append-only,
so "what was live in March" always has an answer. No bytes move; a restore is a metadata copy
and completes in well under a second.

What restore carries and what it does not:

| Carried from the restored version | Left as it is now |
| --- | --- |
| Files and manifest | Share links and grants |
| `entryPath` | Name, title, description, tags |
| | TTL and pinned state |

Rolling back content must never silently change who can see something. That asymmetry is the
same one in §5.11: undoing does not re-open access, and it does not close it either.

**Preview.** A non-live version is viewable in the dashboard through
`/~/artifacts/{name}/versions/{id}/preview`, which streams files through the API rather than
mounting them at a public path. There are no per-version hostnames and no preview tokens — the
earlier draft had both and they existed only because artifacts were on wildcard subdomains,
which they no longer are. The signed-in owner is the only audience, so an authenticated proxy
route is simpler and leaks nothing.

The live version cannot be deleted (`409 version_is_live`). Deleting any other is soft, then
hard after the trash window.

## 8.3 Version retention

Per-user, in `settings.versionRetention`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `keepLast` | 20 | Always keep the N most recent versions of an artifact |
| `keepDays` | 365 | Always keep anything newer than N days |
| `keepPinned` | `true` | Pinned versions are never pruned |
| `minimum` | 3 | Never reduce an artifact below this many versions |

The nightly job soft-deletes versions failing every test. It never touches the live version.
Defaults are generous because files are deduplicated: twenty versions of a calendar that
changes a few lines a week cost twenty copies of one small HTML file and nothing else.

## 8.4 Trash

Deleting an artifact sets `trashed_at`. While trashed it is:

- invisible at its URL — `404` to everyone, including anyone holding a link;
- absent from listings, search, and "shared with me";
- listed only in `GET /api/v1/artifacts?trashed=true` and the trash screen (§11.15);
- still holding its name, so the name cannot be reused until it leaves the trash;
- still counted against storage quota.

`POST /api/v1/artifacts/{name}/restore` brings it back with its versions intact. Share links
and grants are **not** restored — trashing revoked them, and restoring does not un-revoke.

After `SHARE_TRASH_DAYS` (default 30) the nightly job hard-deletes: rows go, reference counts
drop, and the next collection pass removes any bytes nothing else references.

`DELETE /api/v1/artifacts/{name}?purge=true` skips the trash entirely. It requires the separate
`artifacts:delete` scope, is audited as `artifact.purge`, and is the path guarantee P8 is
tested against. Agent tokens do not hold that scope by default, so **the worst a runaway agent
can do is fill the trash**, which is a Tuesday afternoon and an undo, not a disaster.

Trash has its own storage figure on the trash screen, because a user near quota should be able
to see that emptying it is the fix.

## 8.5 Artifact TTL

Distinct from share-link expiry. An artifact may carry its own `ttlExpiresAt`, meaning the thing
itself is temporary.

- Default is `null`: artifacts live until deleted. The posting calendar is not scratch.
- An agent posting throwaway output sets `"ttl": "30d"` and the artifact self-trashes.
- Expiry moves the artifact **to the trash**, not to deletion, so the 30-day recovery window
  still applies. An expired artifact is therefore recoverable for a month.
- The sweep runs every 15 minutes; `/internal/authorize` also checks inline, so an expired
  artifact is unreachable immediately.
- The owner is emailed 24 hours before an artifact with a TTL expires, but only when it has
  live share links or grants — otherwise the notification is noise about the owner's own
  scratch files.
- Setting `ttl` on an artifact with live share links returns a `ttl_with_live_links` warning:
  the links will die with it.

## 8.6 Staleness

Not a reaper. A view.

The worker recomputes nightly: for each user, artifacts with no view in *N* days (default 90),
excluding pinned ones and anything with a live link or grant. The dashboard surfaces the count
and total size — "34 artifacts you haven't opened in 90 days · 2.1 GB" — with a screen listing
them, sortable by size, and multi-select delete.

Nothing is ever deleted by this mechanism. Deleting things the owner did not ask to delete is
how a tool loses trust, and the trash exists precisely so that the owner can be decisive without
being careful.

## 8.7 Search

Metadata only. Artifact contents are never read, indexed, embedded, or classified (P5).

```
GET /api/v1/artifacts?q=calendar&tag=social&kind=bundle&owner=sarah
    &createdAfter=2026-06-01&hasLink=true&sort=updated_desc
```

| Filter | Matches |
| --- | --- |
| `q` | Name, title, description, and tags. Trigram-based, so partial words and typos work |
| `tag` | Exact tag, repeatable (AND) |
| `kind` | `bundle`, `page`, `document`, `image`, `video`, `file` |
| `owner` | Handle. Only ever returns artifacts you own or that are shared with you |
| `createdBefore` / `createdAfter` / `updatedBefore` / `updatedAfter` | Dates |
| `hasLink` | Artifacts with at least one live share link |
| `token` | Which agent token posted it |
| `trashed`, `shared`, `pinned` | Scope switches |
| `sort` | `updated_desc` (default), `created_desc`, `name_asc`, `size_desc`, `views_desc` |

Ranking for `q`: exact name match, then name prefix, then trigram similarity on name, then on
title, then on description. Tags match exactly and boost. The scoring is a single SQL
expression over the `pg_trgm` indexes in §3.4 — no search engine, no separate index to keep in
sync, no reindex job.

**What search cannot do, stated in the docs:** find an artifact by a phrase inside a PDF or a
sentence in an HTML report. That is the direct cost of P5 and it is the right trade for this
instance, but it means naming and tagging matter. The MCP tool description tells agents to
supply a title and tags on every post for exactly this reason (§9.3).

Search is scoped to the caller: their own artifacts plus anything granted to them. There is no
instance-wide search, not even for the root user, because a search that crosses spaces is a
listing of someone else's work.

## 8.8 Activity on an artifact

```
GET /api/v1/artifacts/{name}/activity
```

Merges audit events and daily view rollups for one artifact into a single reverse-chronological
feed: posted, overwritten, renamed, shared, link created or revoked, granted, copied, viewed
(*n* times on a date, via which link). This is what the artifact screen's activity tab shows
(§11.7), and it is the answer to "who has actually opened the thing I sent".

View entries carry counts and dates, never identities or addresses — the daily salted hash
(§3.8) supports "3 viewers on Tuesday" and cannot support "which three".

## 8.9 Error codes

| HTTP | Code | Meaning |
| --- | --- | --- |
| 404 | `version_not_found` | No such version |
| 409 | `version_is_live` | Deleting the live version |
| 409 | `version_deleted` | Restoring or previewing a deleted version |
| 409 | `artifact_not_trashed` | Restore called on something not in the trash |
| 409 | `name_taken` | Restoring when the name has been reused |
| 422 | `invalid_ttl` | Unparseable duration or a past timestamp |
| 422 | `invalid_filter` | Unsupported search parameter or sort |
| 422 | `restore_files_missing` | A file the target version needs was purged |
