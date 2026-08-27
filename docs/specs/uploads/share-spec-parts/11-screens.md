# Part 11 — Every Screen and State

## 11.0 How to read this part

Screen numbers are fixed by `inventory.md` and are the join key between this part, the copy in
Part 12, and the design system in Part 13. Where an earlier part cites a screen number that
disagrees with the inventory, **the inventory wins** — §8.4's reference to "the trash screen
(§11.13)" means 11.15.

Three facts shape every screen here and are not restated in each one:

1. **The dashboard is a signed-in JavaScript application** served from `/~/*`, talking to
   `/api/v1/*` with the session cookie and the `X-Share-CSRF` header (§4.4). It has no
   server-rendered fallback and does not need one.
2. **R1–R7 are server-rendered HTML with inline CSS and no JavaScript at all.** They are
   emitted by the API (or by Caddy, for R6) and never load the dashboard bundle. R1 in
   particular must submit a form with scripting disabled (§7.4).
3. **Nothing on any screen is derived from file contents.** No generated titles, no summaries,
   no thumbnails, no previews rendered from parsing. An artifact with no `title` displays its
   `name` in the title position, in the same weight, with no placeholder text and no guess
   (P5). The only "preview" anywhere is the artifact's own bytes rendered in an iframe or a
   native element by the browser.

### 11.0.1 Vocabulary used by every screen

| Term on screen | Source |
| --- | --- |
| **Sharing state** | `artifact.visibility` plus `artifact.shareLinks[]` (§7.8) |
| **Posted by** | `artifact.createdBy` — `{type:'token'|'user', id, name}` |
| **Version** | `artifact.seq`, `versionCount` |
| **Expires** | Always an absolute UTC timestamp, with a relative hint in parentheses |

---

## 11.1 — Sign in — passkey

- **Purpose** — Get a returning user into the dashboard with one authenticator tap and nothing typed.
- **Route** — `/~/signin`. Any unauthenticated `/~/*` request redirects here with `?next=` holding the original path.
- **Entry points** — Typing the host; a bookmark; expiry of a session (`401 session_expired`); the "Sign in" link on R4 is deliberately absent — R4 reveals nothing.
- **Permissions** — Public. An already-authenticated visitor is redirected to `?next=` or `/~/artifacts` without rendering.
- **Layout** — Single centred column, max 380px, vertically centred, no chrome: no sidebar, no top bar. Wordmark, one line of copy, the primary button, then a single small link row. Nothing below the fold at any viewport ≥ 480px tall.
- **Components**
  - Wordmark and hostname (`share.c52.com`, from the served origin — not configurable client-side).
  - **Sign in** button — calls `POST /auth/passkey/login/begin` with an empty body, passes `publicKey` to `navigator.credentials.get()`, posts the assertion to `POST /auth/passkey/login/finish`. `allowCredentials` is empty, so the browser offers whichever discoverable credential matches (§4.3).
  - Link: **Use a recovery code** → 11.2.
  - No email field. No "remember me" — the session is 30 days sliding by default (§4.4).
- **States**
  - *Idle* — button enabled.
  - *Ceremony in progress* — button shows a spinner and is disabled; the browser's own passkey sheet is the primary feedback. A 120-second timeout matches `timeout: 120000`.
  - *Cancelled* (`NotAllowedError` / `AbortError`) — return to idle silently, no error text. A user who dismissed the sheet knows they dismissed it.
  - *Failed* — `401 invalid_credential` or `401 webauthn_verification_failed` → one inline error above the button (§12.5), button re-enabled.
  - *Counter regressed* — `401 credential_counter_regressed` → a distinct, more serious message stating the owner has been emailed; the recovery link is emphasised.
  - *Rate limited* — `429` on `webauthn_begin`/`webauthn_finish` → the button disables with a countdown from `Retry-After`.
  - *No passkey on this device* — the browser reports no credential; show the recovery-code link plus one sentence pointing at 11.3 on a device that has one.
- **Interactions** — Success sets `share_s` and `share_csrf` and navigates to `?next=` when it is a same-origin `/~/` path, otherwise `/~/artifacts`. An open-redirect check on `next` is mandatory: reject anything not matching `^/~/`.
- **Copy references** — §12.5 (11.1), §12.8 for the auth codes.

---

## 11.2 — Sign in — recovery code

- **Purpose** — Let a user who has lost every passkey get one 30-minute session whose only job is registering a new passkey.
- **Route** — `/~/signin/recovery`
- **Entry points** — The link on 11.1. Never linked from inside the app.
- **Permissions** — Public.
- **Layout** — Same centred column as 11.1. Two fields stacked (email, recovery code), a primary button, a back link, and a short paragraph explaining what happens next — this screen is used once every few years and must explain itself in place rather than in a help page.
- **Components**
  - Email field — `type="email"`, autocomplete `username`.
  - Code field — 24 characters, Crockford base32, monospace, auto-uppercased and stripped of spaces and hyphens on input; a submitted value is normalised client-side before `POST /auth/recovery/use`.
  - Advisory: using a code invalidates all others and issues a fresh one, shown *before* submission, not after.
- **States**
  - *Invalid* — `401` returns a single message that does not distinguish a wrong email from a wrong code.
  - *Rate limited* — `recovery_use` (5/hour/email) or `recovery_use_ip` (20/day/IP) → countdown from `Retry-After`.
  - *Success* — navigate straight to 11.3 in **forced mode**, with the new recovery code presented there once.
- **Interactions** — The session created here is restricted server-side to registering and listing passkeys. The dashboard reflects that: the app shell renders in a reduced form with the sidebar suppressed and every other route redirecting back to 11.3 until a passkey is registered. A visible strip states the session ends at an absolute time.
- **Copy references** — §12.5 (11.2), §12.9 `recovery_used`.

---

## 11.3 — Passkey registration / add a passkey

- **Purpose** — Register a WebAuthn credential, either as an addition from the security screen or as the forced step after recovery or invite acceptance.
- **Route** — `/~/security/passkeys/new`
- **Entry points** — **Add a passkey** on 11.19; the forced redirect from 11.2 and 11.4; the first-run checklist item on 11.6.
- **Permissions** — Any session, including a recovery-restricted one. No token can reach this — it is a browser ceremony.
- **Layout** — Centred card, max 480px. In forced mode the card sits on the bare page (no shell); in additive mode it renders as a modal dialog over 11.19 with the URL updated, so a refresh keeps the dialog.
- **Components**
  - **Register** button — `POST /auth/passkey/register/begin` → `navigator.credentials.create()` → `POST /auth/passkey/register/finish` with `{credential, name}`.
  - Name field, pre-filled from the AAGUID lookup ("1Password", "MacBook Touch ID") and editable before or after registration (§4.2).
  - In forced-after-recovery mode only: the freshly issued recovery code in a monospace block with a **Copy** control and a "shown once" line, plus a checkbox — *I have saved this code* — gating the finish button.
  - Existing credential list, read-only, from `GET /api/v1/auth/passkeys`, so the user does not register a duplicate authenticator by mistake.
- **States**
  - *Already registered* — `excludeCredentials` causes `InvalidStateError`; show "this authenticator is already registered" and name the matching credential.
  - *Cancelled* — silent return to idle.
  - *Second-key nudge* — when this is the user's first and only passkey after success, the screen does not dismiss; it repeats the prompt to add a second and offers **Do this later**, which is what closes the first-run checklist item (§4.2).
- **Interactions** — Success in additive mode closes the dialog, toasts, and prepends the new credential to 11.19's list optimistically using the `201` body. Success in forced mode navigates to `/~/artifacts`.
- **Copy references** — §12.5 (11.3), §12.3 for the checklist line.

---

## 11.4 — Invite acceptance

- **Purpose** — Turn an invite token into a user with a passkey and an empty space.
- **Route** — `/~/invite/{token}`
- **Entry points** — The emailed link only (§12.9 `invite`).
- **Permissions** — Public, gated by the token. A signed-in user opening someone else's invite sees an explanatory screen and a **Sign out and continue** action — silently binding an invite to the wrong session is worse than an extra click.
- **Layout** — Centred column. Who invited you, the handle you are about to claim, the space you will get (`share.c52.com/~sarah`), then the register button. The handle is shown as fixed text, not a field: it was claimed at invite time (§4.8).
- **Components** — Inviter display name and the target handle from `GET /api/v1/invites/{token}` (public, token-gated, returns only inviter name, handle, email, `expiresAt`); a display-name field, optional; the passkey ceremony inline (the same component as 11.3); the recovery code presented once on success with a copy control and a save-confirmation checkbox.
- **States**
  - *Expired* — `410 invite_expired` → a terminal card telling them to ask for a new invite. No retry control.
  - *Revoked or already accepted* — `404` → the same terminal card. The two are not distinguished.
  - *Handle now taken* — cannot happen (handles are claimed at invite time); if the API returns `409` anyway, show the generic failure and instruct them to contact the person who invited them.
- **Interactions** — Success creates the user, establishes a session, and lands on 11.6 with the first-run checklist for a non-root user (no "invite someone" item).
- **Copy references** — §12.5 (11.4).

---

## 11.5 — Home — artifact list

- **Purpose** — The default screen: everything the user owns, newest activity first, with each row stating its sharing state.
- **Route** — `/~/artifacts`. Filter and sort state lives in the query string (`?q=&tag=&kind=&sort=&hasLink=&token=`), so a filtered view is linkable and survives a refresh.
- **Entry points** — Sign-in landing; the wordmark; **Artifacts** in the sidebar; `Esc` from most sub-screens.
- **Permissions** — Any session. Shows only the caller's own space (§5.2) — there is no cross-space listing for anyone, including root.
- **Layout** — App shell (11.29.1) with the sidebar at left. Main column top to bottom: advisory banner stack, filter bar, table, pagination footer. Above the fold at 1280×800: banners, filter bar, and roughly twelve rows. The table is the only scrolling region on wide viewports; the page scrolls as a whole below 900px.

```
┌──────────────┬────────────────────────────────────────────────────────────────┐
│ Share        │  [ Search artifacts            ⌘K ]        [ Upload ]   (RM)   │
│              ├────────────────────────────────────────────────────────────────┤
│ LIBRARY      │  ⚠ 2 share links expire within 48 hours          Review        │
│ ▸ Artifacts  │  ⚠ postcal expires 26 Aug 2026, 09:00 UTC (in 2 days) Extend   │
│   Shared     ├────────────────────────────────────────────────────────────────┤
│   Trash      │  All ▾   Kind ▾   Tag ▾   Agent ▾   Shared ▾   Sort: Updated ▾ │
│              ├────────────────────────────────────────────────────────────────┤
│ AGENTS       │  NAME                 SHARING            UPDATED   SIZE  v     │
│   Tokens     │  ─────────────────────────────────────────────────────────────  │
│   Audit log  │  ▣ postcal            ◆ Link active      2h ago    110 KB  v2  │
│              │    Q4 posting calendar  expires 7 Sep 2026, 18:04 UTC          │
│ ──────────── │    bundle · grokbot@hosta                              ⋯     │
│ ▓▓▓░░ 41 GB  │  ─────────────────────────────────────────────────────────────  │
│  of 500 GB   │  ▤ q3/market-report   ● Shared with 2    1d ago    2.4 MB  v5  │
│ (RM) robert  │    document · claude-code@hosta                        ⋯     │
│              │  ─────────────────────────────────────────────────────────────  │
│              │  ▦ hero-render        ○ Private          3d ago    18 MB   v1  │
│              │    image · uploaded by you                              ⋯     │
│              ├────────────────────────────────────────────────────────────────┤
│              │  50 of 218                                   [ Load more ]     │
└──────────────┴────────────────────────────────────────────────────────────────┘
```

- **Components**
  | Element | Source |
  | --- | --- |
  | Rows | `GET /api/v1/artifacts?limit=50&sort=updated_desc` → `items[]` |
  | Kind glyph | `item.kind` (`bundle`/`page`/`document`/`image`/`video`/`file`) — a glyph per kind from §13, never a rendered thumbnail |
  | Name | `item.name`, monospace. Primary link to 11.7 |
  | Title line | `item.title`; **omitted entirely when null** — no placeholder, no guess |
  | Sharing state | The 11.29.2 component, from `item.visibility` + `item.shareLinks[]` |
  | Updated | `item.updatedAt`, relative, `title` attribute carrying the absolute UTC value |
  | Size | `item.totalBytes`, formatted |
  | Version | `v{item.seq}`; a link to 11.10 when `versionCount > 1` |
  | Agent | `item.createdBy.name` with a token glyph when `type === 'token'`, "you" when `type === 'user'`. Clicking it filters the list by `?token={id}` |
  | Pin | `item.pinned` — pinned rows sort above everything else within the current sort |
  | Row menu `⋯` | Open · Copy URL · Share… (11.12) · Versions · Rename · Move to trash |
  | Banners | Links within 48 h of expiry from `GET /api/v1/artifacts?hasLink=true` (§7.5); artifacts within 24 h of `ttlExpiresAt`; quota at 80/95/100% from `GET /api/v1/status`; anomaly notices from §10.4 |
  | Filter bar | Kind, tag (`GET /api/v1/tags`), agent token (`GET /api/v1/tokens`), sharing (`hasLink=true` / private only), sort |
- **States**
  - *Loading* — eight skeleton rows with the real column widths (11.29.11). Never a spinner: the table's shape is known before the data arrives.
  - *Empty (no artifacts at all)* — 11.6 replaces this screen entirely.
  - *Empty (filters applied)* — an in-table empty row: what was filtered, and **Clear filters**. The filter bar stays.
  - *Error* — the table region is replaced by the 11.29.10 error block with **Retry**; banners and filters remain interactive.
  - *Over quota* — a persistent red banner: posting is refused, reading and deleting still work (§10.3). Links to 11.25 and 11.15.
  - *Link expiring soon* — amber banner naming the count, expanding to a list on **Review**, each row offering **Extend** (`PATCH /api/v1/links/{id}` with `ttl`) inline.
  - *TTL approaching* — amber banner per artifact within 24 h, with **Keep** (`PATCH /api/v1/artifacts/{name}` `{"ttl":null}`) and **Dismiss**.
  - *Stale-artifact nudge* — when `GET /api/v1/status` reports a stale count, a low-emphasis line at the foot of the list linking to 11.24. Never a banner; it is not urgent.
- **Interactions**
  - Row click → 11.7. `⌘`/`Ctrl`-click and middle-click open in a new tab (rows are real `<a>` elements).
  - **Copy URL** copies `item.url`, toasts "URL copied". This is the artifact's signed-in address, not a share link — the toast says so, because handing that URL to a client is the single most likely user error in the product.
  - **Move to trash** → destructive confirm (11.29.6) naming the 30-day window and warning that live links and grants are revoked immediately and are *not* restored on restore (§5.11). On confirm: optimistic row removal, `DELETE /api/v1/artifacts/{name}`, toast with **Undo** for 10 seconds calling `POST …/restore`. On failure, the row returns to its position with an error toast.
  - Multi-select via row checkboxes (revealed on hover and always visible once one is checked) enables bulk **Move to trash** only. No bulk share, ever — see 11.13's rationale.
  - **Load more** appends using `nextCursor`. No page numbers (11.29.4).
  - Sort or filter change rewrites the query string and refetches from a null cursor.
- **Copy references** — §12.5 (11.5), §12.6 for banner text.

---

## 11.6 — Home — empty state and first-run checklist

- **Purpose** — Turn a brand-new account into one with an agent posting to it, without the user reading documentation.
- **Route** — `/~/artifacts`, rendered instead of the table when `items.length === 0 && no filters applied`.
- **Entry points** — First sign-in; after emptying an account.
- **Permissions** — Any session. The root user's checklist has an invite item; other users' does not.
- **Layout** — Two stacked blocks in the main column: the checklist card (max 640px), then a quiet "nothing here yet" block below it. The checklist is above the fold; it is the point of the screen.
- **Components**
  - Checklist items, each with a state icon, one line of copy (§12.3), and one action:
    | # | Item | Done when |
    | --- | --- | --- |
    | 1 | Connect an agent — shows the MCP JSON block with this host filled in and a **Create a token** button → 11.18 | `GET /api/v1/tokens` returns ≥ 1 live token |
    | 2 | Post something — the exact `share_post` call and the `share post ./dir` equivalent | `artifact_count > 0` |
    | 3 | Add a second passkey → 11.3 | ≥ 2 live passkeys, or explicitly dismissed |
    | 4 | *(root only)* Invite someone → 11.22 | ≥ 1 invite sent, or dismissed |
  - Checklist completion is stored in `settings.firstRun` via `PATCH /api/v1/settings`; dismissal is per item and the card disappears when all items are done or dismissed.
  - **Upload from your browser** as a secondary action → 11.17, for a user with no agent yet.
- **States** — *Partially complete* (items tick live as conditions become true — the screen polls `GET /api/v1/status` every 10 s while item 2 is outstanding, so an agent's first post appears without a refresh); *dismissed* (card gone, plain empty state remains); *error fetching status* (checklist renders with all items actionable and none ticked, no error surface — a failed poll must not block onboarding).
- **Interactions** — The token block's **Copy** copies the JSON with the token placeholder intact. It never contains a real token: tokens are shown once, on 11.18, and are not re-fetched into a checklist.
- **Copy references** — §12.3 in full, §12.4 for the linked agent-setup page.

---

## 11.7 — Artifact detail — overview and activity

- **Purpose** — The single page that answers "what is this, who can see it, what has happened to it, and who posted it".
- **Route** — `/~/artifacts/{name}` — `{name}` may contain slashes (`/~/artifacts/q3/market-report`); the router matches greedily to the end of the path minus a known sub-route segment (`files`, `view`, `versions`, `share`).
- **Entry points** — Any row on 11.5, 11.14, 11.16, 11.24; the toast after an upload; an emailed notification link.
- **Permissions** — Owner sees everything. A grantee (`visibility` includes a grant to them, `owner.isSelf === false`) sees a reduced page: overview, files, viewer, **Save a copy**, and nothing else — no share tab, no versions, no activity, no metadata editing. Attempting `/share` or `/versions` as a grantee redirects to the overview with a toast. A signed-in user with no access gets 11.29.10's not-found block inside the shell, matching the API's `404` (P1).
- **Layout** — Two columns above 1100px: a wide main column and a 320px right rail. Below that the rail collapses and its cards stack under the main column, with the **sharing card first** — the sharing state must never fall below the fold on a phone.

```
┌───────────────────────────────────────────────┬─────────────────────────────┐
│ ‹ Artifacts                                   │  SHARING                    │
│                                               │  ◆ Link active              │
│ postcal                            [ Open ↗ ] │  expires 7 Sep 2026,        │
│ Q4 posting calendar                    [ ⋯ ]  │  18:04 UTC (in 14 days)     │
│ ▣ bundle · v2 · 3 files · 110 KB              │  1 link · password set      │
│ share.c52.com/postcal            [ Copy URL ] │  [ Manage sharing ]         │
│                                               ├─────────────────────────────┤
│ ┌ Overview │ Files │ Versions │ Sharing ────┐ │  POSTED BY                  │
│ │                                           │ │  ⬡ grokbot@hosta          │
│ │ ACTIVITY                                  │ │  token shr_01J… · view all  │
│ │ ● Today  14:02  Overwritten → v2          │ │                             │
│ │          by grokbot@hosta               │ ├─────────────────────────────┤
│ │ ● Today  14:02  Link created, 14 days,    │ │  DETAILS                    │
│ │          password set, by you             │ │  Created 3 Aug 2026         │
│ │ ● Yest.  09:11  4 views via "Fairfield"   │ │  Updated 24 Aug 2026        │
│ │ ● 3 Aug  10:40  Posted v1                 │ │  Tags: social, grokbot      │
│ │          by grokbot@hosta               │ │  TTL: none                  │
│ │                          [ Load older ]   │ │  Views: 41 · last 2h ago    │
│ └───────────────────────────────────────────┘ │  [ Edit details ]           │
└───────────────────────────────────────────────┴─────────────────────────────┘
```

- **Components**
  | Element | Source |
  | --- | --- |
  | Name, title, kind, seq, fileCount, totalBytes | `GET /api/v1/artifacts/{name}` |
  | Canonical URL + **Copy URL** | `artifact.url` |
  | **Open ↗** | Navigates to `artifact.url` in a new tab — the real artifact, not the viewer |
  | Tab bar | Overview (this), Files (11.8), Versions (11.10), Sharing (11.12) |
  | Sharing card | 11.29.2 state, plus per-link summary: label, absolute expiry with relative hint, `hasPassword`, `viewCount`; grants listed by handle. **Manage sharing** → 11.12 |
  | Posted-by card | `artifact.createdBy` — token name and `display_prefix`; "view all" filters 11.5 by `?token=` |
  | Details card | `createdAt`, `updatedAt`, `tags[]`, `ttlExpiresAt`, `viewCount`, `lastViewedAt`, `pinned`, and `copiedFrom` when set |
  | Activity feed | `GET /api/v1/artifacts/{name}/activity` — merged audit events and daily view rollups (§8.8) |
- **Activity feed rules** — Reverse chronological, grouped by day with sticky day headers. Every entry names its actor: a token name with the token glyph, a user handle, or "system" for TTL expiry and link sweeps. View entries read "*n* views via **Fairfield listing team**" or "*n* views, signed in" and never carry an identity, an address, or an approximate location (P6) — a footnote in the feed says so once, at the bottom, rather than on each row. Entry types: posted, overwritten, renamed, metadata changed, link created, link revoked, link expired, password changed, granted, grant revoked, copied (including *by another user*, §5.10), trashed, restored, version restored, TTL expired.
- **States**
  - *Loading* — header skeleton, rail card skeletons, feed skeleton.
  - *Not found / no access* — the 11.29.10 not-found block; identical for "never existed" and "not yours".
  - *Trashed* — the whole page renders in a muted treatment behind a persistent bar: "In the trash. Permanently deleted on 23 Sep 2026 (in 30 days)." with **Restore** and **Delete permanently**. Editing, sharing, and versions are disabled; the sharing card reads Private and states that trashing revoked its links, which restoring will not bring back.
  - *TTL approaching* — an amber strip above the tabs, absolute date, with **Keep this artifact** and **Change TTL**.
  - *Link expiring soon* — the sharing card's expiry text turns amber inside 48 h and offers **Extend** inline.
  - *Grantee view* — the header shows `owner.handle` and an advisory: this belongs to someone else and can be deleted by them at any time; **Save a copy** is the primary button (§7.7.1).
  - *No entry point* — a note beside the kind line: the artifact root shows a file listing (R7), with **Set an entry file** opening the Files tab's picker.
  - *Empty activity* — impossible: every artifact has at least a "posted" event.
- **Interactions**
  - `⋯` menu: Rename, Edit details, Set TTL, Pin/Unpin, Copy to my space, Download all, Move to trash.
  - **Rename** opens a dialog stating plainly that the old URL stops working immediately and is not redirected, and that share links keep working because they address the artifact (§7.2). `PATCH /api/v1/artifacts/{name}` `{name}` → on success, replace the route without a history entry. `409 name_taken` shows inline, including the case where a trashed artifact holds the name, with a link to 11.15.
  - **Edit details** — inline dialog for title, description, tags. Optimistic; reverts with an error toast on failure. Passing `visibility` is impossible from this UI by construction; the API's `422 use_share_endpoint` is a backstop, not a path.
  - **Set TTL** — presets (7d, 30d, 90d, custom date, none). With live links, the dialog surfaces the `ttl_with_live_links` warning before confirming: the links die with the artifact (§8.5).
  - **Download all** — `GET /api/v1/artifacts/{name}/archive` streams a `.tar.gz` of the live version.
  - Feed pagination is cursor-based, **Load older** only.
- **Copy references** — §12.5 (11.7), §12.2 for the sharing-state definitions, §12.6 for the rename and TTL warnings.

---

## 11.8 — Artifact detail — files

- **Purpose** — Show exactly what is in the live version, at real paths and sizes, and let the owner choose which file answers at the root.
- **Route** — `/~/artifacts/{name}/files` — with `?version={id}` when viewing a non-live version (reached from 11.11).
- **Entry points** — The Files tab; "no entry point" advisories; R7's dashboard counterpart.
- **Permissions** — Owner and grantee. Grantees see the tree and can download; **Set as entry file** is absent.
- **Layout** — The same header and tab bar as 11.7, then a full-width file tree. Directories are derived by splitting `path` on `/`; the API returns a flat list and the client builds the tree. Depth beyond three levels indents at a fixed 12px to keep long paths readable.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Files · live version v2 · 3 files · 110 KB          [ Download .tar.gz ] │
├──────────────────────────────────────────────────────────────────────────┤
│  PATH                            TYPE          SIZE      ⋯               │
│  ▾ /                                                                     │
│    index.html            ★ entry  text/html    18.0 KB   ⋯               │
│    style.css                      text/css      4.1 KB   ⋯               │
│    ▾ img/                                                                │
│      chart.png                    image/png    88.1 KB   ⋯               │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components** — Rows from `GET /api/v1/artifacts/{name}/files?version=…` (`path`, `size`, `contentType`, `sha256`). Entry marker where `path === artifact.entryPath`. Row menu: Open (the artifact URL plus the path), Download (`files/content?path=…`), Copy path, Copy SHA-256, **Set as entry file**. Header shows which version is displayed and, when it is not the live one, a bar linking back to 11.10.
- **States** — *Loading* skeleton tree; *single file* (the tree collapses to one row and the header says "1 file"); *no entry point* (a banner naming R7 behaviour with **Set as entry file** on each HTML row); *file missing at serve time* (not detectable here — the manifest is authoritative); *error* → 11.29.10.
- **Interactions** — **Set as entry file** issues `PATCH /api/v1/artifacts/{name}` `{entryPath}` and takes effect without reposting (§5.9); optimistic star move, revert on failure. Copy SHA-256 exists because it is how an operator confirms deduplication and matches a blob on disk. There is no delete-a-file action: versions are immutable — the note says so where the action would be.
- **Copy references** — §12.5 (11.8).

---

## 11.9 — Artifact viewer

- **Purpose** — Look at the artifact inside the dashboard, with its sharing state visible, without leaving the app.
- **Route** — `/~/artifacts/{name}/view`, `?path=` for a specific file in a bundle, `?version=` for a non-live version.
- **Entry points** — Clicking the kind glyph on 11.5; **Preview** on 11.7; **View** on 11.11 and 11.14.
- **Permissions** — Owner and grantee. Recipients never reach this route — they get the artifact itself, or R2.
- **Layout** — A slim fixed top bar over a full-bleed content region. The bar is 48px and never scrolls. Content fills the rest of the viewport with no page scroll; scrolling happens inside the content element.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ‹ postcal   ◆ Link active · expires 7 Sep 2026, 18:04 UTC   ⤓  ↗  ✕      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                    [ artifact rendered here ]                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components by `kind`**
  | `kind` | Rendering |
  | --- | --- |
  | `page`, `bundle` | `<iframe src="{artifact.url}">` with `sandbox="allow-scripts allow-forms allow-popups allow-same-origin"`. The iframe loads the real artifact path, so relative links resolve exactly as a recipient sees them |
  | `document` (PDF) | `<iframe>` on the file URL; the browser's viewer. Office documents are not rendered — a download card with the file name and size |
  | `image` | `<img>` centred, fit-to-viewport by default, click to toggle 1:1, with dimensions read from the loaded element (not from the file — nothing is probed, §6.6.4) |
  | `video` | Native `<video controls preload="metadata">` on the file URL. Range requests make seeking work (§6.6.4). No transcoding, no poster frame — no poster is generated, ever |
  | `file` | Download card only |
  - Top bar: back to 11.7, artifact name, the 11.29.2 sharing indicator with absolute expiry, **Download**, **Open in a new tab**, **Close** (`Esc`).
  - For a bundle with more than one HTML file, a path selector in the bar listing HTML paths from the manifest.
- **States** — *Loading* (a neutral panel, no spinner over an iframe — the artifact's own load is the feedback); *unrenderable kind* (download card with the content type stated); *version preview* (an amber strip: "Viewing v1. The live version is v3." with **Restore this version**, streaming through `/~/artifacts/{name}/versions/{id}/preview` per §8.2); *no entry point* (the iframe shows R7's listing, which is correct and needs no special case); *video codec unsupported* (the browser's own failure plus a line naming H.264/AAC in MP4 as the format that plays everywhere).
- **Interactions** — `Esc` closes to 11.7. `←`/`→` move between artifacts in the list that was active when the viewer opened, when there was one. Nothing in the viewer mutates the artifact.
- **Copy references** — §12.5 (11.9).

---

## 11.10 — Artifact detail — versions

- **Purpose** — Show every retained version, who made it, what changed by count, and offer restore.
- **Route** — `/~/artifacts/{name}/versions`
- **Entry points** — The Versions tab; the `v{n}` chip on 11.5; the "Overwritten" entries in 11.7's activity feed.
- **Permissions** — Owner only. Grantees do not see version history — it is the owner's working record.
- **Layout** — Header and tabs, then a table with the live version pinned at the top and visually marked. Newest first.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Versions · 5 kept · retention: last 20, 365 days        [ Retention ⚙ ]  │
├──────────────────────────────────────────────────────────────────────────┤
│  v5  ● LIVE   24 Aug 2026, 18:04 UTC   3 files  110 KB   +0 ~1 −0    ⋯   │
│               grokbot@hosta · "November slots"                         │
│  v4  📌 pinned 17 Aug 2026, 09:22 UTC   3 files  109 KB   +1 ~0 −1   ⋯   │
│               grokbot@hosta                                            │
│  v3           10 Aug 2026, 09:20 UTC    2 files   96 KB   +0 ~2 −0   ⋯   │
│                                                    [ Load older ]        │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components** — Rows from `GET /api/v1/artifacts/{name}/versions`: `seq`, `isLive`, `createdAt`, `fileCount`, `totalBytes`, `note`, `createdBy`, `changes {added, modified, removed}`. Retention summary from `settings.versionRetention` (§8.3) with a link to 11.21. Row menu: View (11.11), Files, Restore, Pin/Unpin, Delete.
- **States** — *Only one version* (a single live row and a line explaining that overwriting creates the next one — no empty state); *pruned* (a footer line: older versions were removed by retention on a date, linking to the setting); *live row* (Restore and Delete are absent, not disabled — `409 version_is_live` is a backstop); *files purged* (a restore attempt returning `422 restore_files_missing` marks the row unrestorable with an explanation).
- **Interactions**
  - **Restore** — confirm dialog stating exactly what §8.2 says: this creates a **new** version (v6, not a rewind), carries files and `entryPath`, and leaves share links, grants, name, title, tags, TTL, and pinned state untouched. On confirm, `POST …/versions/{id}/restore` with an optional note; the new version is prepended and marked live; toast.
  - **Pin** — `POST …/versions/{id}/pin`; optimistic; pinned versions are exempt from retention.
  - **Delete** — only for non-live versions; soft, with the trash window named; `DELETE …/versions/{id}`.
- **Copy references** — §12.5 (11.10), §12.6 for the restore explanation.

---

## 11.11 — Version preview and compare

- **Purpose** — Look at a specific version and see its manifest against the live one before deciding to restore.
- **Route** — `/~/artifacts/{name}/versions/{id}`
- **Entry points** — A version row on 11.10; an activity entry on 11.7.
- **Permissions** — Owner only.
- **Layout** — Header strip naming the version and its live/non-live status, then two panes side by side above 1000px — **Manifest compare** left, **Preview** right — stacking with compare first below that. Compare first because the decision is made from the file list; the preview confirms it.
- **Components**
  - Compare pane: a per-path diff of two manifests (`GET …/versions/{id}/files` and the live version's files), each row marked *added*, *modified* (size and SHA differ), *removed*, or *unchanged*, with both sizes shown for modified rows. Unchanged rows collapse behind a "show N unchanged" control. **This compares manifests, not contents** — Share does not read files, so there is no line-level diff anywhere in the product, and the pane says so in one line.
  - Preview pane: the 11.9 viewer in an embedded mode, sourced from `/~/artifacts/{name}/versions/{id}/preview` (authenticated proxy, §8.2 — no per-version URL exists publicly).
  - Header: `seq`, `createdAt` absolute, `createdBy`, `note`, `totalBytes`, and buttons **Restore this version**, **Download**, **Back to versions**.
- **States** — *This is the live version* (compare pane replaced by a plain manifest; Restore absent); *deleted version* (`409 version_deleted` → a terminal card; preview unavailable); *large manifest* (over 500 rows, unchanged rows collapse by default and the pane virtualises); *loading* (two skeleton panes).
- **Interactions** — **Restore this version** runs 11.10's confirm and, on success, navigates to 11.10 with the new live version highlighted. Clicking a file row in the compare pane loads that path into the preview pane when it is renderable.
- **Copy references** — §12.5 (11.11).

---

## 11.12 — Sharing panel — links and grants

- **Purpose** — The complete, honest picture of who can currently reach this artifact, and the only place access is changed.
- **Route** — `/~/artifacts/{name}/share`
- **Entry points** — The Sharing tab; **Manage sharing** on 11.7; the sharing chip on 11.5's row menu; the expiring-links banner.
- **Permissions** — Owner only, and only for a signed-in session. **A dashboard session always carries full authority over its own space** — the `share:create` scope constrains API tokens, not people (§7.9). Grantees never see this tab. If the artifact is trashed, the panel renders read-only with `422 artifact_trashed` explained in place.
- **Layout** — Header and tabs, then a status block, then two sections: **Share links** and **People**. The status block is the loudest element on the page and states the widest thing currently true.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ◆ LINK ACTIVE                                                           │
│  Anyone with the link can view this until 7 Sep 2026, 18:04 UTC          │
│  (in 14 days). A password is required.                                   │
├──────────────────────────────────────────────────────────────────────────┤
│  SHARE LINKS                                    [ + Create share link ]  │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Fairfield listing team                              ⚿ password     │  │
│  │ share.c52.com/s/9fq2n4kw…              [ Copy ]                    │  │
│  │ Expires 7 Sep 2026, 18:04 UTC (in 14 days)                         │  │
│  │ 12 views · last 22 Aug 2026 · created by you, 24 Aug 2026          │  │
│  │                              [ Extend ] [ Change password ] [ Revoke ]│
│  └────────────────────────────────────────────────────────────────────┘  │
│  Expired and revoked links (3)                                       ▾   │
├──────────────────────────────────────────────────────────────────────────┤
│  PEOPLE                                            [ + Share with… ]     │
│  sarah   granted 12 Aug 2026 by you · "the Q4 draft"        [ Remove ]   │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components**
  | Element | Source |
  | --- | --- |
  | Status block | `artifact.visibility` + the earliest live `shareLinks[].expiresAt` |
  | Link cards | `GET /api/v1/artifacts/{name}/links` — `id`, `label`, `displayPrefix`, `expiresAt`, `hasPassword`, `viewCount`, `lastViewedAt`, `createdAt`, `createdBy`, `maxViews` |
  | Link URL | Reconstructed for display as `share.c52.com/s/{displayPrefix}…`; **Copy** copies the full URL, which the client retains in memory only from the creation response |
  | Grants | `GET /api/v1/artifacts/{name}/grants` — handle, note, `createdAt`, `createdBy` |
  | Creator attribution | `createdBy` on each link — a token name when an agent with `share:create` made it, which is exactly the case the owner most needs to see |
- **The full URL problem, decided** — The server stores only `token_hash` and `display_prefix`; the full token is unrecoverable after creation (§3.7). So **Copy** on a link created in an earlier session cannot produce the URL. The card states this plainly and offers **Create a new link** rather than a dead control. A link created in this session keeps its full URL in memory until reload and its **Copy** works. This is a real constraint of the security design and the UI names it instead of hiding it.
- **States**
  - *Private* — the status block reads Private, both sections show their empty state, and **Create share link** is the primary action on the page.
  - *Expiring soon* — a link inside 48 h renders its expiry in amber with **Extend** promoted.
  - *Expired / revoked* — moved into the collapsed section, shown greyed with the reason and date. Never deleted from the list: what used to be reachable is part of the record.
  - *Max views reached* — the card shows "burned after N views" and sits with the expired links.
  - *Trashed artifact* — read-only, with the §5.11 asymmetry stated: trashing revoked these; restoring will not restore them.
  - *Rate limited* — `429 link_create` → **Create share link** disables with a countdown and a line noting that 20 links an hour is the ceiling and the owner has been notified (§10.2.1).
  - *Loading / error* — skeleton cards; 11.29.10 with retry.
- **Interactions**
  - **Create share link** → 11.13. It is a route, not a modal-only state, so it is linkable and survives a refresh.
  - **Extend** — a small popover with the same TTL presets; `PATCH /api/v1/links/{id}` `{ttl}`. The popover states that extension **adds to the current expiry**, and previews the resulting absolute date before confirming (§7.4).
  - **Change password** — a dialog offering *generate a new one*, *set my own*, or *remove the password*. All three revoke every recipient session on that link immediately (P9), which the dialog says before confirming. A generated password is displayed once here, with the same one-time treatment as 11.13.
  - **Revoke** — destructive confirm. This one is **not** reversible and the dialog says so explicitly, in contrast to trash: revoking is immediate, kills recipient sessions, and cannot be undone — a new link is a new URL. On confirm, `DELETE /api/v1/links/{id}`; the card moves to the collapsed section optimistically.
  - **Share with…** — a dialog taking a handle (typeahead over `GET /api/v1/users` restricted to handles on the instance) and an optional note; `POST …/grants`. Errors surface inline: `404 user_not_found`, `409 grant_exists`, `409 cannot_grant_to_self`.
  - **Remove** a grant — confirm; takes effect on the grantee's next request (§7.7).
- **Copy references** — §12.5 (11.12), §12.2 for what each level means, §12.6 for the revoke and password warnings.

---

## 11.13 — Create share link dialog

> This is the most consequential screen in the product. It is the moment a private thing becomes
> reachable by anyone holding a URL. It is a deliberate, multi-field flow with a confirmation
> step and a terminal success state — never a toggle, never a one-click "share" button, and
> never available in bulk across multiple artifacts.

- **Purpose** — Create exactly one share link, with the owner having seen precisely what becomes reachable, for how long, and under what protection, before anything is created.
- **Route** — `/~/artifacts/{name}/share/new`. Rendered as a modal over 11.12; the URL changes so the flow is linkable, refresh-safe, and back-button-safe. Closing returns to `/~/artifacts/{name}/share`.
- **Entry points** — **Create share link** on 11.12; **Share…** in a row menu on 11.5 or 11.16 (which routes through 11.12 first, so the owner always sees existing links before adding another); the 403 remediation link an agent hands its human when `share_create_link` fails on scope (§7.9).
- **Permissions** — Owner, signed in. Not reachable for an artifact you do not own, or one that is trashed (`422 artifact_trashed` → the dialog refuses to open and 11.12 explains why).

### 11.13.1 Layout

One modal, 520px wide, three sequential states in the same frame: **Configure → Confirm → Created**. The header and the "what becomes reachable" summary persist across all three so the subject never leaves the screen. The modal does not scroll on a 720px-tall viewport in the Configure state; below that it scrolls with the summary pinned.

```
┌── Create a share link ─────────────────────────────────── ✕ ─┐
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ▣ postcal — Q4 posting calendar                        │  │
│  │   bundle · 3 files · 110 KB · live version v2          │  │
│  │   Currently: ○ Private — only you                      │  │
│  │   Anyone with this link will see the CURRENT version,  │  │
│  │   including any future updates by grokbot@hosta.     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  HOW LONG                                                    │
│  ( ) 30 minutes   ( ) 24 hours   (•) 14 days  ← your default │
│  ( ) 90 days      ( ) 180 days   ( ) Custom…                 │
│  → Expires 7 Sep 2026, 18:04 UTC (in 14 days)                │
│                                                              │
│  PASSWORD                                                    │
│  ( ) No password — anyone with the link gets in              │
│  (•) Generate a password for me                              │
│  ( ) Set my own password                                     │
│      [                                        ] min 8 chars  │
│                                                              │
│  LABEL (only you see this)                                   │
│  [ Fairfield listing team                                 ]  │
│                                                              │
│  ▸ Advanced — burn after N views                             │
│                                                              │
│                            [ Cancel ]  [ Continue → ]        │
└──────────────────────────────────────────────────────────────┘
```

### 11.13.2 What becomes reachable — the summary block

Always the first thing in the modal, and the only part rendered before the form controls. It is not decorative; it exists so that "what am I about to hand out" is never a memory exercise.

| Line | Source |
| --- | --- |
| Kind glyph, name, title (title omitted if null — the name stands alone) | `GET /api/v1/artifacts/{name}` |
| `kind` · `fileCount` files · `totalBytes` · live version `v{seq}` | same |
| Current state, using the 11.29.2 component | `visibility` |
| The follow-updates warning | Constant copy (§7.2): the link addresses the artifact, so future overwrites are visible to whoever holds it. When `createdBy.type === 'token'`, the sentence **names the agent**, because "an agent can change what this link shows" is the specific risk |
| Entry-point note, when `entryPath` is null | The recipient sees a file listing, not a page |
| Framing note, when the artifact declared `allowFraming` and a password is being set | The flag is ignored for password-protected links (§6.6.6) |

### 11.13.3 The TTL picker

- Presets: **30 minutes**, **24 hours**, **14 days**, **90 days**, **180 days**, **Custom**.
- The option equal to `SHARE_DEFAULT_SHARE_TTL` (14 days by default) is preselected and carries the marker "your default", sourced from `GET /api/v1/settings` → `defaultShareTtl`. A user who changed it in 11.21 sees their own value marked instead.
- Any preset exceeding `SHARE_MAX_SHARE_TTL` (180 days) is rendered disabled with the ceiling stated, rather than hidden — the limit should be visible.
- **Custom** reveals a date-time control, minimum now + 5 minutes, maximum now + `SHARE_MAX_SHARE_TTL`. It submits `ttl` as a duration string computed from the chosen instant, so the server remains the clock authority.
- Under the picker, always: `→ Expires 7 Sep 2026, 18:04 UTC (in 14 days)`. Absolute first, relative in parentheses, recomputed on every change and rendered in the user's chosen timezone display setting with `UTC` shown when that setting is UTC (11.29.3).
- There is no "never expires" option and no way to reach one. If a user asks, the copy answers: every link expires, by design (P4).

### 11.13.4 The password choice

Three radio options, never a checkbox, because the middle option has a consequence the user must see before confirming.

| Option | Behaviour |
| --- | --- |
| **No password** | `password: null`. Selecting it reveals one line of consequence copy: anyone who receives, forwards, or finds this URL can view the artifact until it expires. |
| **Generate a password for me** *(default)* | `password: true`. The server generates `{adjective}-{noun}-{2 digits}` and returns it once (§7.4). The helper line explains it is designed to be read aloud. |
| **Set my own** | A text field, minimum 8 characters, no composition rules, no strength meter — a meter would imply rules the server does not enforce. Client-side validation only checks length; `422 password_too_short` is the backstop. The field is `type="password"` with a reveal toggle and `autocomplete="new-password"`. |

Generate is the default because a link with a password is the safer thing to create by accident, and a generated one is guaranteed to be a real secret rather than a habit.

### 11.13.5 Label and advanced

- **Label** — free text, ≤ 120 characters, optional but always visible (not behind "advanced"), with helper text saying it is shown only to the owner and appears in link lists, activity, and audit records. A label makes the link cards on 11.12 usable a month later, which is why it is not buried.
- **Advanced** — collapsed by default, holding only **burn after N views**: an integer ≥ 1 mapping to `maxViews`. The helper text defines the unit precisely: distinct viewer-days, not requests, so one person reloading a page does not burn the link. Rarely wanted; hidden accordingly.

### 11.13.6 Confirm

**Continue** does not create anything. It replaces the form with a read-back panel and a single primary button reading **Create link**:

```
┌── Create a share link ─────────────────────────────────── ✕ ─┐
│  ▣ postcal — Q4 posting calendar                             │
│                                                              │
│  You are about to make this reachable by anyone holding a    │
│  URL, until it expires.                                      │
│                                                              │
│  Expires    7 Sep 2026, 18:04 UTC  (in 14 days)              │
│  Password   Generated — shown once, on the next screen       │
│  Label      Fairfield listing team                           │
│  Views      Unlimited                                        │
│                                                              │
│  You will be emailed when this link is created, and again    │
│  24 hours before it expires.                                 │
│                                                              │
│                              [ ‹ Back ]  [ Create link ]     │
└──────────────────────────────────────────────────────────────┘
```

The email sentence is present because `settings.notifyOnShare` defaults to true (§7.3); when a user has disabled it, that line is replaced by a quieter one noting notifications are off, with a link to 11.21. Being told what will and will not reach your inbox is part of understanding what you just did.

### 11.13.7 Created — the success state

The terminal state. It does not auto-dismiss, cannot be dismissed by clicking the backdrop, and cannot be closed by `Esc`; only the explicit **Done** button closes it. The password is displayed here and nowhere else, ever.

```
┌── Share link created ─────────────────────────────────────────┐
│  ✓ postcal is now reachable by anyone with this link          │
│                                                               │
│  LINK                                                         │
│  https://share.c52.com/s/9fq2n4kwPz3mXr7bTvQ8dL   [ Copy ]    │
│                                                               │
│  PASSWORD — shown once, right now                             │
│  ┌─────────────────────────────────────────────┐              │
│  │  civil-marmot-71                  [ Copy ]  │              │
│  └─────────────────────────────────────────────┘              │
│  This is the only time this password is displayed. It is not  │
│  stored in a form anyone can read, including us. If you lose  │
│  it, create a new link.                                       │
│                                                               │
│  Expires 7 Sep 2026, 18:04 UTC (in 14 days)                   │
│                                                               │
│  [ Copy link and password ]                    [ Done ]       │
└───────────────────────────────────────────────────────────────┘
```

- **Copy link and password** puts both on the clipboard as two lines, formatted for pasting into a message, with the absolute expiry as a third line — so the thing the owner sends states its own end date.
- Individual **Copy** controls for each. Each toasts and swaps its label to "Copied" for 2 seconds.
- **Done** is the only exit and is styled as the primary action. Closing without copying is possible and the password is then gone; the button carries no confirmation, because a nag would train dismissal.
- On close, 11.12 refetches and the new link card appears at the top, retaining the full URL in memory for this session's **Copy**.

### 11.13.8 States

| State | Behaviour |
| --- | --- |
| Loading the artifact | Skeleton summary block; the form is disabled until the summary is real. Never let someone configure a link for an artifact whose identity has not loaded. |
| Submitting | **Create link** shows a spinner and disables; the modal cannot be closed mid-request. |
| `403 insufficient_scope` | Cannot occur from a session; if it does, treat as a generic failure and log — a session is not scope-limited (§7.9). |
| `422 ttl_too_long` | Inline under the TTL picker with the server's ceiling; returns to Configure. |
| `422 password_too_short` | Inline under the password field; returns to Configure with the value preserved. |
| `422 artifact_trashed` | Terminal error card with **Go to trash** → 11.15. |
| `429 rate_limited` (`link_create`) | Terminal card naming the 20/hour ceiling, the `Retry-After` countdown, and the fact that the owner has been notified (§10.4). |
| Network failure mid-create | The dialog stays on Confirm with a retry button and a warning that a link **may** have been created; the retry sends the same `Idempotency-Key` generated when Confirm was first pressed, so a retry cannot produce a second link (§5.1.3). |
| Success with `warnings[]` | Rendered under the expiry line in the Created state, not as blocking errors. |

### 11.13.9 Interactions and rules

- `Esc` and backdrop click close the modal in Configure and Confirm (with no confirmation — nothing has been created). Both are inert in Created.
- The browser back button from Confirm returns to Configure; from Created it closes to 11.12 and the password is gone. This is stated in the Created panel's copy.
- The form never pre-fills a label from the artifact's title. Guessing who a link is for is exactly the class of inference this product refuses.
- **There is no bulk create.** Sharing is per-artifact and each one gets this dialog. A user with ten artifacts to share performs the act ten times, and that friction is the feature.
- **Copy references** — §12.5 (11.13) carries every string on this screen verbatim; §12.6 the advisory catalogue; §12.9 `link_created`.

---

## 11.14 — Shared with me

- **Purpose** — Everything other users on the instance have granted to this user, with the fact that it can vanish made obvious.
- **Route** — `/~/shared`
- **Entry points** — Sidebar; the emailed grant notification. The sidebar item is hidden when the instance has exactly one user and the call has never returned an item.
- **Permissions** — Any session. Lists only artifacts with a live grant to the caller (§7.7).
- **Layout** — Same table shape as 11.5 with the sharing column replaced by an **Owner** column and a per-row advisory. The filter bar loses the agent filter (another user's tokens are not visible) and gains an owner filter.
- **Components** — `GET /api/v1/artifacts?shared=true`: `name`, `title`, `kind`, `owner.handle`, `updatedAt`, `totalBytes`, `url` (the canonical `/~handle/name` form), grant note. Row actions: Open, View (11.9), Download, **Save a copy**.
- **States**
  - *Empty* — "Nothing has been shared with you." plus one line explaining that another user must grant it; no call to action, since the user cannot cause it.
  - *Owner may delete this* — a persistent, low-emphasis line on every row: this belongs to `@handle` and disappears if they delete it. **Save a copy** sits beside it. The advisory is per row rather than a page banner because the failure is per artifact and silent (§7.7.1).
  - *Grant revoked while viewing* — the next request 404s; the row is removed on refetch with a toast naming the artifact.
  - *Loading / error* — as 11.5.
- **Interactions** — **Save a copy** opens a small dialog with a name field defaulted to the source name (with a numeric suffix if taken in the caller's space) and a title field; `POST /api/v1/artifacts/{name}/copy`. The dialog states the two things that matter: it costs no storage against quota beyond what dedup implies, and the copy is **private with no share links regardless of the source** (§5.10). On success, toast with a link to the new artifact in the caller's own space, and a note that the original owner sees the copy in their activity.
- **Copy references** — §12.5 (11.14).

---

## 11.15 — Trash

- **Purpose** — Show what was deleted, when it disappears for good, how much space it is holding, and how to get it back.
- **Route** — `/~/trash`
- **Entry points** — Sidebar; the undo toast's expiry; the over-quota banner; `409 name_taken` when a trashed artifact holds a name.
- **Permissions** — Any session, own space only. **Delete permanently** requires nothing extra for a signed-in user; the `artifacts:delete` scope constrains tokens (§4.6.1).
- **Layout** — A header strip with the trash's own storage figure and **Empty trash**, then a table sorted by deletion time, newest first.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Trash · 12 artifacts · 3.4 GB · deleted after 30 days  [ Empty trash ]  │
│  Items here still count against your storage quota.                      │
├──────────────────────────────────────────────────────────────────────────┤
│  NAME              DELETED           GONE ON                SIZE         │
│  ▣ old-deck        24 Aug, 11:02     23 Sep 2026 (30 days)  2.1 GB   ⋯   │
│    by grokbot@hosta                                                    │
│  ▤ q2/report       02 Aug, 09:40     01 Sep 2026 (in 8 days) 410 MB  ⋯   │
│    by you                                    [ Restore ]                 │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components** — `GET /api/v1/artifacts?trashed=true`: `name`, `kind`, `trashedAt`, computed purge date (`trashedAt + SHARE_TRASH_DAYS`), `totalBytes`, `createdBy`. Trash total from `GET /api/v1/status` → `trashBytes`. Row menu: Restore, Delete permanently, View files.
- **States**
  - *Empty* — "Nothing in the trash." with a line stating the window: deleted artifacts stay here 30 days.
  - *Purging soon* — rows within 48 h of their purge date render the date in amber and float to the top of a "Going soon" group above the rest.
  - *Name conflict* — a row whose name has since been taken by a new artifact is marked; **Restore** opens a rename dialog first, because `POST …/restore` returns `409 name_taken` otherwise (§8.9).
  - *Over quota* — a banner at the top making the connection explicitly: emptying the trash frees `trashBytes` and is the fastest way back under quota.
  - *Loading / error* — as 11.5.
- **Interactions**
  - **Restore** — `POST /api/v1/artifacts/{name}/restore`. The confirm states the asymmetry: versions come back, share links and grants do not, and anyone who held a link stays locked out until a new one is made (§5.11). Optimistic removal from the table, toast linking to the restored artifact.
  - **Delete permanently** — the strongest confirmation in the product (11.29.6, type-to-confirm variant): the artifact name must be typed. Copy states that every version and every file unique to it goes, and that this cannot be undone. `DELETE /api/v1/artifacts/{name}?purge=true`.
  - **Empty trash** — the same type-to-confirm, with the phrase `empty trash`, naming the count and the bytes freed.
  - No bulk restore. Restoring is per artifact because each may need a rename.
- **Copy references** — §12.5 (11.15), §12.6 for both destructive confirmations.

---

## 11.16 — Search and command palette

- **Purpose** — Find an artifact by name, title, description, or tag from anywhere, in one keystroke, and jump to it.
- **Route** — `/~/search?q=…` for the full-page results view; `⌘K` / `Ctrl-K` opens the palette overlaying any screen without changing the route.
- **Entry points** — `⌘K`; `/` when no input is focused; the top-bar search field; the results link at the bottom of the palette.
- **Permissions** — Any session. Search is scoped to the caller's own artifacts plus anything granted to them. **There is no instance-wide search, including for root** (§8.7); the palette states this in its footer once, on first use.
- **Layout** — The palette is a 640px overlay pinned 15% from the top, over a dimmed backdrop. One input, then grouped results, then a footer of key hints. The full-page view is 11.5's table with the query in the filter bar.

```
┌──────────────────────────────────────────────────────────────┐
│ 🔍 postcal                                                   │
├──────────────────────────────────────────────────────────────┤
│ ARTIFACTS                                                    │
│ ▣ postcal          ◆ Link active · exp 7 Sep 2026     ⏎      │
│    Q4 posting calendar · bundle · grokbot@hosta            │
│ ▤ q3/postcal-old   ○ Private                                 │
├──────────────────────────────────────────────────────────────┤
│ ACTIONS                                                      │
│ ↗ Upload a file                                              │
│ ⚿ Create an API token                                        │
│ 🗑 Open trash                                                 │
├──────────────────────────────────────────────────────────────┤
│ ↑↓ navigate   ⏎ open   ⌘⏎ new tab   esc close   → all results│
└──────────────────────────────────────────────────────────────┘
```

- **Components** — Results from `GET /api/v1/artifacts?q=…&limit=8` with the `q` ranking of §8.7. Each row carries the **same sharing-state component as everywhere else** — a search result showing a private artifact and one showing a live link must be distinguishable at a glance without opening either. Actions group: static navigation commands, filtered by the same query string. Recent-artifacts group when the query is empty, from the last 8 `updatedAt` items.
- **States**
  - *Empty query* — recents plus the actions list.
  - *Searching* — a thin progress line under the input; previous results stay visible rather than blanking (queries are debounced 150 ms).
  - *No matches* — "No artifacts match *postcal*." plus the standing explanation that search covers names, titles, descriptions, and tags — **never the contents of files** — with a link to §12.4's explanation of why. This is where a user first meets P5 in anger, so the copy is load-bearing.
  - *Rate limited* — `429` on the `search` bucket → the input keeps working, results show a retry line with the countdown.
  - *Error* — an inline row with **Retry**; the palette never closes on an error.
- **Interactions** — Type-ahead is fully keyboard-driven: `↑`/`↓`, `⏎` opens (11.7), `⌘⏎` opens the artifact URL in a new tab, `→` or clicking "all results" navigates to `/~/search?q=…` and closes the overlay. `Esc` closes and restores focus to the element that opened it. Selecting an action executes it and closes.
- **Copy references** — §12.5 (11.16), §12.4 for the "why search cannot read files" page.

---

## 11.17 — Upload from the browser

- **Purpose** — Let a human post an artifact without an agent or the CLI: a report to hand over, a folder someone emailed, a first thing to look at.
- **Route** — `/~/upload`
- **Entry points** — The **Upload** button in the top bar; 11.6's secondary action; the `⌘K` action.
- **Permissions** — Any session, own space only.
- **Layout** — Single centred column, 720px. A drop zone above the fold, then, once files are chosen, a metadata form and a file table below it. The primary button is fixed to the bottom of the column so it stays reachable with a long file list.
- **Components**
  - Drop zone accepting files and directories (`webkitdirectory`), preserving relative paths as the manifest's `path` values.
  - Name field — pre-filled from the dropped directory name or the single file's stem, lowercased and normalised to the §5.3 pattern with the transformation shown live. Validation mirrors `^[a-z0-9][a-z0-9._-]*(/…)*$`.
  - Title, description, tags, TTL — all optional, all explicit. **No field is ever auto-filled from file contents.**
  - Entry file selector, defaulting per §5.5 and shown only when more than one file is present.
  - File table: path, size, type, and a per-file status once uploading. Client-side hashing (SHA-256, in a worker) produces the manifest, so the declare call can skip files the server already has.
  - A standing note beside the primary button: posting does not share anything; the artifact will be private (§9.6).
- **States**
  - *Idle* — drop zone only.
  - *Hashing* — a determinate bar over the file count; large files hash visibly slowly and the copy says so.
  - *Uploading* — per-file progress from the `PUT /api/v1/files/{sha256}` calls, up to 4 concurrent from a browser; a `skipped` summary line ("2 of 3 files already on the server").
  - *Committing* — one indeterminate step.
  - *Refused locally* — a path failing §6.4 normalisation, or a dotfile, is rejected before any upload with the offending path named. `.env`, `*.pem`, `*.key`, `id_rsa*` are refused with the loud secret warning of §9.4.2 and cannot be forced from the browser at all — the browser has no `--force-secrets`, deliberately.
  - *Errors* — `409 name_taken` (offer **Overwrite as a new version** or a different name, stating that overwriting keeps the old version); `413 quota_exceeded` (with current, projected, and quota bytes from `detail`, and a link to 11.25); `413 file_too_large`; `413 too_many_files`; `422 invalid_name`; `422 path_case_collision` naming both paths; `507 disk_full`.
  - *Interrupted* — a failed upload leaves the session resumable; the screen offers **Resume**, calling `GET /api/v1/uploads/{id}` for fresh signed URLs (§5.4).
- **Interactions** — On commit, navigate to 11.7 for the new artifact with a toast carrying **Copy URL**. Never auto-open the share dialog: posting and sharing are separate decisions, and joining them here would undo the whole shape of §11.13.
- **Copy references** — §12.5 (11.17), §12.8 for the upload error codes.

---

## 11.18 — API tokens

- **Purpose** — Create, inspect, scope, and revoke the credentials agents use; make it obvious which agent is which and what each can do.
- **Route** — `/~/tokens`
- **Entry points** — Sidebar; 11.6's first checklist item; the "view all" link on an artifact's posted-by card; 11.27's setup instructions.
- **Permissions** — Any session for its own tokens. Creating requires the session (tokens with `account:admin` can create tokens over the API; the dashboard path is always a session).
- **Layout** — Header with **New token**, then a table of live tokens, then a collapsed section of revoked ones.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  API tokens                                            [ + New token ]   │
├──────────────────────────────────────────────────────────────────────────┤
│  NAME                 PREFIX        SCOPES              LAST USED    ⋯   │
│  ⬡ grokbot@hosta    shr_7Fq2mR8v  read write ⚠share   2h ago       ⋯   │
│                       created 3 Aug 2026 · 412 artifacts posted          │
│  ⬡ claude-code@mini   shr_9Kd1pQ4x  read write          12m ago      ⋯   │
│  ⬡ ci@github          shr_2Bn8vT6z  read write          never        ⋯   │
├──────────────────────────────────────────────────────────────────────────┤
│  Revoked (2)                                                         ▾   │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components** — `GET /api/v1/tokens`: `id`, `name`, `displayPrefix`, `scopes[]`, `createdAt`, `lastUsedAt`, `expiresAt`, `revokedAt`. Artifact counts per token from the same response. Scope chips, with `share:create` always rendered in a warning treatment. Row menu: Edit scopes, Rename, View activity (11.23 filtered by `tokenId`), View artifacts (11.5 filtered by `token`), Revoke.
- **New token dialog** — name (required, with the convention `agent@machine` shown as placeholder), scope checkboxes with one line each from §12.2, optional expiry. `share:create` is unchecked by default and checking it expands an inline warning (§12.6): this token will be able to make your artifacts reachable by anyone with a URL, without asking you. `artifacts:delete` carries its own line: this token can permanently delete, skipping the trash.
- **Created state** — the token in a monospace block, shown once, with **Copy**, and beneath it a ready-to-paste MCP configuration block with the token substituted and the host filled in. A **Done** button is the only exit; the same one-time treatment as 11.13.7 down to the wording pattern.
- **States** — *Empty* (a first-token card pointing at both the dashboard flow and the device-code flow of 11.26); *never used* ("never" in the last-used column, not a dash); *expired* (greyed with the date); *revoked* (in the collapsed section with revocation time and actor); *loading/error* as usual.
- **Interactions** — **Revoke** is a destructive confirm naming what breaks: the agent using it stops working immediately, and its artifacts and versions remain and stay attributed to it. `DELETE /api/v1/tokens/{id}`; optimistic move to the revoked section. **Edit scopes** is `PATCH /api/v1/tokens/{id}`, audited as `token.scope_change`, and adding `share:create` re-shows the warning and requires an explicit confirm.
- **Copy references** — §12.5 (11.18), §12.6 for the scope warnings.

---

## 11.19 — Passkeys and sessions

- **Purpose** — Manage the credentials and browser sessions that can reach this account.
- **Route** — `/~/security`
- **Entry points** — User menu; 11.6's checklist; 11.20; the counter-regression email.
- **Permissions** — Any session, own account only. A recovery-restricted session (§4.5) may list and register only; every other control renders disabled with an explanation.
- **Layout** — Two stacked sections in a 760px column: **Passkeys**, then **Sessions**, then a **Recovery code** card.
- **Components**
  - Passkeys from `GET /api/v1/auth/passkeys`: `name`, `createdAt`, `lastUsedAt`, `backupState` (shown as "syncs across your devices" / "this device only"), `transports`. Actions: Rename, Revoke. **Add a passkey** → 11.3.
  - Sessions from `GET /api/v1/auth/sessions`: created, last seen, coarse user agent, IP, which passkey signed in, and a **This device** marker (§4.4). Actions: Revoke; **Sign out everywhere**.
  - Recovery-code card: whether one is outstanding and when it was generated, with **Generate a new code** — which invalidates the old one and shows the new one exactly once behind a saved-it checkbox.
- **States** — *One passkey only* — a persistent advisory at the top of the section: with a single passkey, losing it means recovery-code or server-side recovery (§4.5); **Add another** is promoted. *Revoking your last passkey* — refused in the UI with an explanation, not merely disabled. *Revoking the passkey that created this session* — the confirm states you will be signed out. *Recovery code never generated* — the card is amber.
- **Interactions** — Revoking a passkey revokes every session created with it (§4.4); the confirm names how many sessions that is. **Sign out everywhere** revokes all sessions including the current one and returns to 11.1.
- **Copy references** — §12.5 (11.19).

---

## 11.20 — Security overview

- **Purpose** — One page answering "is anything wrong": recent authentication activity, anomalies, and everything currently reachable without a sign-in.
- **Route** — `/~/security/overview`
- **Entry points** — User menu; anomaly notification emails; the banner an anomaly raises on 11.5.
- **Permissions** — Any session, own account. The root user additionally sees instance-level rows (failed auth across the instance, backup state) via `scope=instance`.
- **Layout** — A grid of four cards above the fold, then a recent-events list.
- **Components**
  - **Reachable without sign-in** — the count of artifacts with at least one live link, from `GET /api/v1/artifacts?hasLink=true`, each listed with its absolute expiry, sorted by soonest. This card is first because it is the answer to the question this product's threat model is built around.
  - **Recent sign-ins** — `GET /api/v1/audit?action=auth.&limit=10`, successes and failures, with IP and coarse user agent.
  - **Anomalies** — the §10.4 signals raised in the last 7 days: unusual link creation, first link by a token, bulk posting, bulk trashing, a token seen from a new IP, recovery-code use, counter regression. Each names the token and links to 11.23 filtered to it.
  - **Tokens** — count of live tokens, how many hold `share:create`, and the last-used spread. Links to 11.18.
- **States** — *All clear* (an explicit "nothing unusual in the last 7 days" rather than empty cards); *anomaly present* (the card takes the warning treatment and the sidebar item gets a dot); *root instance view* (a toggle between "my account" and "instance"); *loading/error* per card independently — one failing card must not blank the page.
- **Interactions** — Each anomaly row offers **Revoke this token** inline, going through 11.18's confirm. **Revoke all share links** is present here as the dashboard equivalent of `sharectl panic` (§10.5), with type-to-confirm and a count of what will die.
- **Copy references** — §12.5 (11.20), §12.6 for anomaly descriptions.

---

## 11.21 — Settings

- **Purpose** — The few per-user choices that exist, and nothing more.
- **Route** — `/~/settings`
- **Entry points** — User menu; links from 11.10 (retention), 11.13 (default TTL and notifications), 11.24 (staleness window).
- **Permissions** — Any session, own account.
- **Layout** — A 720px single column of labelled groups, each setting one row with its control right-aligned and its explanation beneath the label. Changes save on change, not on a Save button — every setting here is independently and instantly revertible.
- **Components** — `GET /api/v1/settings` / `PATCH /api/v1/settings`:
  | Group | Setting | Key | Default |
  | --- | --- | --- | --- |
  | Profile | Display name, email (read-only, changed by the operator), handle (read-only) | — | — |
  | Sharing | Default share-link duration — the preset marked "your default" on 11.13 | `defaultShareTtl` | `14d` |
  | Sharing | Email me when a share link is created | `notifyOnShare` | on |
  | Sharing | Email me 24 hours before a link expires | `notifyOnLinkExpiring` | on |
  | Versions | Keep last / keep days / keep pinned / minimum (§8.3) | `versionRetention` | 20 / 365 / true / 3 |
  | Staleness | Not-opened window driving 11.24 | `staleDays` | 90 |
  | Notifications | Quota warnings, token created, anomaly alerts | `notify*` | on |
  | Display | Time zone for displayed timestamps: UTC or the browser's zone | `timeZone` | UTC |
- **States** — *Saving* (a per-row spinner, then a check that fades); *save failed* (the control reverts and an inline error appears); *cannot be disabled* (recovery-code use and counter regression render as fixed "always on" rows with a one-line reason — §10.8); *no permanent-link setting* (the sharing group carries a standing line: every share link expires; there is no setting for that, §2.7).
- **Interactions** — Lowering `versionRetention` shows what it would prune, by count, before it applies; the prune itself happens on the nightly job, and the copy says so rather than implying an immediate effect.
- **Copy references** — §12.5 (11.21).

---

## 11.22 — Users and invites (root only)

- **Purpose** — Create and disable the small set of people who have accounts on this instance.
- **Route** — `/~/users`
- **Entry points** — User menu, visible only when `user.isRoot`; 11.6's root checklist item.
- **Permissions** — Root, or a user holding `account:admin` (§4.8). Anyone else gets the in-shell not-found block — not a "you are not allowed" page, which would confirm the route exists.
- **Layout** — Two tables: **Users**, then **Pending invites**.
- **Components** — Users from `GET /api/v1/users`: handle, display name, email, `isRoot`, `createdAt`, `lastSeenAt`, artifact count, storage used against quota. Invites from `GET /api/v1/invites`: email, handle, invited by, `expiresAt`, state. **Invite someone** dialog: email plus handle, with live validation against the reserved list (§6.3) and the handle pattern, and a preview of the space they will get (`share.c52.com/~sarah`).
- **States** — *Only you* (a one-line explanation that Share has no public sign-up, §1.4 N4); *invite pending* (with **Resend** and **Revoke**); *invite expired* (greyed, **Revoke** only, with a note that invites live 7 days); *rate limited* (`invite`, 10/day → the button disables with a countdown); *disabled user* (greyed row, with the note that all their sessions and tokens are revoked and their artifacts remain).
- **Interactions** — **Disable** is a destructive confirm stating exactly what happens: sessions and tokens revoked, artifacts retained, links on their artifacts continue to serve until they expire — and offering **Revoke their share links too** as a checkbox inside the confirm. There is no delete-user action in the dashboard; that is a `sharectl` operation, and the copy says so.
- **Copy references** — §12.5 (11.22).

---

## 11.23 — Audit log

- **Purpose** — The searchable record of everything that happened, and the evidence for P3.
- **Route** — `/~/audit`, with every filter in the query string.
- **Entry points** — Sidebar (Agents group); "view activity" from 11.18, 11.20, and any artifact.
- **Permissions** — Any session sees their own events. Root may switch to `scope=instance`.
- **Layout** — A filter bar over a dense table. Rows are one line with an expander revealing the full `metadata` JSON.
- **Components** — `GET /api/v1/audit?action=&actorType=&tokenId=&targetId=&from=&to=&q=`: time (absolute, seconds precision), action, actor (user handle, token name and prefix, or "system"), target label, IP, and the expander. Filters: action (a picker grouped by domain per §10.7, supporting prefix values like `link.`), actor type, token, date range, free text on `target_label`. A **Sharing only** shortcut sets `action=link.` — the most common reason to open this screen.
- **States** — *Empty for filters* (with **Clear filters**); *loading* (skeleton rows); *export running* (`GET /api/v1/audit/export?format=ndjson` triggers a download; the button shows progress and the copy notes it streams the current filter); *root instance mode* (a toggle with the scope stated in a strip, since instance mode shows other users' actions).
- **Interactions** — Cursor pagination with **Newer** / **Older**, never page numbers. Clicking an actor filters by it; clicking a target opens the artifact when it still exists, and otherwise shows the denormalised `target_label` with a note that the target was deleted — which is why `target_label` exists.
- **Copy references** — §12.5 (11.23), §12.2 for what each action name means.

---

## 11.24 — Staleness — things you have not opened

- **Purpose** — Show what has not been looked at in a long time so the owner can decide to delete it. Nothing here deletes on its own (§8.6).
- **Route** — `/~/stale`
- **Entry points** — The quiet line at the foot of 11.5; the storage screen; the `⌘K` action.
- **Permissions** — Any session, own space.
- **Layout** — A header stating the rule and the total, then 11.5's table sorted by size descending, with a bulk-action bar that appears on selection.
- **Components** — `GET /api/v1/artifacts?stale=true&sort=size_desc`. The header reads "34 artifacts you haven't opened in 90 days · 2.1 GB", with the window linking to 11.21. Every row shows `lastViewedAt` (absolute, with "never viewed" where null) and its sharing state — a stale artifact with a live link is a different decision from a stale private one, so both facts sit side by side.
- **States** — *Nothing stale* (a plain confirmation, no call to action); *excluded items explained* (a footnote: pinned artifacts and anything with a live link or grant are never listed, §8.6); *loading/error* as 11.5.
- **Interactions** — Multi-select → **Move selected to trash**, one confirm naming the count, the total bytes, and the 30-day restore window. Requests are issued sequentially with a progress line; a partial failure leaves the successful ones removed and names the failures. Per-row **Keep** sets `pinned: true`, which removes it from this view permanently and says so.
- **Copy references** — §12.5 (11.24).

---

## 11.25 — Storage and quota

- **Purpose** — Show what is using space, what would free some, and how close to the ceiling the user is.
- **Route** — `/~/storage`
- **Entry points** — The sidebar's storage meter; the over-quota banner; quota emails.
- **Permissions** — Any session, own account. Root additionally sees instance disk figures.
- **Layout** — A quota meter above the fold with the three numbers that matter, then two lists: **Largest artifacts** and **What would free space**.
- **Components** — `GET /api/v1/status`: `storageBytes`, `quotaBytes`, `artifactCount`, `trashBytes`, `staleBytes`, and, for root, `diskFreeBytes` and `lastBackupAt`. Largest artifacts from `?sort=size_desc&limit=20`. The "what would free space" list has exactly three rows: trash (`trashBytes`, → 11.15), stale artifacts (`staleBytes`, → 11.24), and old versions (an estimate from retention settings, → 11.21). Each names a number and a destination; none acts directly from here.
- **States** — *Under 80%* (neutral meter); *80–95%* (amber, with a line stating that email warnings are sent at most daily); *over 95%* (red); *at 100%* (red, with §10.3's rule stated plainly: posting fails, reading, sharing, and deleting continue); *dedup note* (a standing footnote that identical files are stored once instance-wide but each user is charged for every file their artifacts reference, §3.9 — the only honest way to explain a number that will not match a naive sum).
- **Interactions** — Read-only apart from navigation. `sharectl recompute-quota` is named in the footnote for the operator, since a drifted counter is an operator fix, not a user one.
- **Copy references** — §12.5 (11.25).

---

## 11.26 — Device authorization

- **Purpose** — Approve an agent's device-code request, with the human seeing what they are granting before they grant it.
- **Route** — `/~/authorize`, optionally `?code=QRTZ-8H4M` from a link the agent printed.
- **Entry points** — An agent's printed instruction (§4.6.2); `share login`; the sidebar's help page.
- **Permissions** — Any session. Unauthenticated visitors go to 11.1 with `next` preserved, then land back here with the code intact.
- **Layout** — Centred card, 480px. A single large code input, then, once matched, the approval panel.
- **Components**
  - Code input: eight characters, `XXXX-XXXX`, auto-uppercased, hyphen inserted automatically, paste-tolerant. `POST /api/v1/auth/device/lookup` with the user code returns the pending request's `name`, `createdAt`, and requested scopes.
  - Approval panel: the agent's declared name (`claude-code@hosta`), the request's source IP and coarse user agent, the scopes it will receive — always the agent default set, `artifacts:read` and `artifacts:write` — and an explicit line: **this token will not be able to create share links**. Buttons **Approve** and **Deny**.
- **States** — *No code entered*; *unknown or expired code* (`404`/`410` → one message, no distinction, with a line telling them to run the command again); *already approved*; *approved* (a terminal confirmation telling them to return to their terminal — the token itself is never shown here, it goes to the polling agent); *denied* (terminal, states the agent will report a refusal); *rate limited* (`device_start`, 10/hour/IP).
- **Interactions** — **Approve** issues the token server-side and audits `token.device_authorize`; the panel then offers **Manage this token** → 11.18, which is where scopes can be elevated deliberately (§4.6.2).
- **Copy references** — §12.5 (11.26).

---

## 11.27 — Help and agent setup

- **Purpose** — Everything an owner needs to point an agent at this instance, and short answers to the questions the design deliberately creates.
- **Route** — `/~/help`, `/~/help/agents`
- **Entry points** — Sidebar footer; 11.6; the empty state on 11.18; contextual "why?" links throughout.
- **Permissions** — Any session. Content is identical for every user; only the hostname and handle in the examples are substituted.
- **Layout** — A two-column documentation layout: a sticky section nav at left (200px), content at right (max 760px). Collapses to a top dropdown nav below 900px.
- **Components** — Content from §12.4, rendered client-side from bundled Markdown — no content is fetched from the network and none is generated. `/~/help/agents` carries copy-paste configuration blocks for Claude Code, Cursor, Codex, Cline, and a generic MCP host, each with `https://share.c52.com/mcp` filled in and a visible `shr_…` placeholder (§9.8), plus the CLI install line and the `share login` flow. Every block has a **Copy** control.
- **States** — *Anchor deep-link* (a `#fragment` scrolls and highlights); *no token yet* (a callout at the top of `/~/help/agents` with **Create a token** → 11.18); *printing* (the nav is hidden and blocks wrap rather than scroll).
- **Interactions** — Purely navigational. Three help topics are linked from elsewhere often enough to be named here: why search cannot read file contents (P5), why every share link expires (P4), and what happens when an agent overwrites an artifact that has a live link (§7.2).
- **Copy references** — §12.4 in full.

---

## 11.28 — Instance status

- **Purpose** — The operator's at-a-glance health check, inside the app rather than over SSH.
- **Route** — `/~/status`
- **Entry points** — User menu (root only); the R6 maintenance page's suggestion to retry; the backup-failure email.
- **Permissions** — Root sees everything. A non-root user sees a reduced version: version string, uptime, and their own quota — enough to answer "is it me or is it the server" without disclosing host details.
- **Layout** — A row of status tiles, then a table of subsystem checks, then a recent-jobs list.
- **Components** — `GET /api/v1/status`: `version`, `uptimeSeconds`, `diskFreeBytes` and percentage, `queueDepths` (precompression, view flush, sweeps), `lastBackupAt` and its outcome, `migrationRevision`, plus per-subsystem states for Postgres, Redis, the file root, and the worker. Recent system audit events (`system.`) from 11.23.
- **States** — *All green*; *degraded* (any tile amber, with the specific check named); *disk over 85%* (red tile matching the §10.8 notification); *backup stale or failed* (red, with the last successful time absolute); *worker behind* (queue depth over a threshold, stating that view counts and precompression lag but nothing is lost); *unreachable* (if this screen's own fetch fails, the app has already shown the global connection-lost banner from 11.29.10).
- **Interactions** — Read-only. No restart, no flush, no destructive control: those are `sharectl`, and putting them behind a browser session would widen the blast radius of a stolen cookie for no real gain. The screen names the relevant `sharectl` command beside each subsystem instead.
- **Copy references** — §12.5 (11.28).

---

# Recipient-facing and error pages (R1–R7)

These seven pages are served by the API (R6 by Caddy) as complete HTML documents with **inline
CSS, no JavaScript, no external requests, and no dashboard chrome**. They must render correctly
with scripting disabled, with a blocked font, and in a text browser. They carry
`Cache-Control: no-store`. None of them links to the dashboard, none names the instance's owner,
and none reveals an artifact's name unless the visitor is already authorised to see it.

Shared shell: a centred column, max 420px, vertically centred, system font stack, one wordmark
line at the top (`share.c52.com`, plain text), and nothing else. §13 gives the exact inline
style block; it is byte-identical across R1–R7 so that page identity cannot be inferred from
CSS differences.

## R1 — Share-link password gate

- **Purpose** — Take a password for one share link, and nothing else.
- **Route** — Any path under `/s/{token}` when the link has a password and the request carries no valid recipient session. Status **401**, code `recipient_auth_required`.
- **Permissions** — Anyone holding the URL.
- **Layout**

```
┌────────────────────────────────────┐
│           share.c52.com            │
│                                    │
│   This link needs a password.      │
│                                    │
│   [ Password                    ]  │
│                                    │
│   [        Continue             ]  │
│                                    │
└────────────────────────────────────┘
```

- **Components** — A `<form method="post" action="/s/{token}/unlock">` with `<input type="password" name="password" autocomplete="current-password" autofocus>` and a submit button. That is the entire page. **No JavaScript participates in submission**: the form works exactly as written with scripting disabled (§7.4), which is the hard requirement for this page.
- **What is deliberately absent** — the artifact's name, title, kind, size, or thumbnail; the owner's handle or display name; who sent it; how long the link has left; any branding beyond the hostname; any link anywhere else in the product (§7.6). A visitor who guesses a token learns only that some link exists.
- **States**
  - *First view* — 401 with the form.
  - *Wrong password* — re-render at 401 with one line above the field: the password is not correct. No count of remaining attempts, no distinction from a first view beyond that line.
  - *Rate limited* — 429 (buckets `link_password` 10/IP/hour, `link_password_link` 50/link/hour, §10.2.2). A plain page stating too many attempts and naming the `Retry-After` interval in minutes. The owner is emailed the first time a link's bucket empties.
  - *Link expired or revoked between load and submit* — 410 → R3.
  - *Correct* — set the recipient cookie `share_r_{prefix}` scoped to `Path=/s/{token}` (§4.7) and `302` to the originally requested path.
- **Interactions** — Submit only. `Enter` in the field submits natively. The form posts form-encoded; the same endpoint also accepts JSON so a scripted client can unlock, but the page itself never uses that path.
- **Copy references** — §12.7 (R1).

## R2 — Share-link landing for a non-HTML artifact

- **Purpose** — Give a recipient a sane page for a PDF, image, video, or file, instead of dropping raw bytes on them with no context.
- **Route** — `/s/{token}` where the resolved artifact's `kind` is not `page` or `bundle`. Status **200**.
- **Permissions** — A valid recipient session for that link.
- **Layout** — The shared shell, slightly wider (560px): title line, one metadata line, a preview element sized to the viewport, and two buttons.
- **Components** — The artifact's `title` **if the owner set one**, otherwise nothing in that position — never the file name dressed up as a title, and never a generated one. Below it: kind, file count, total size. Preview: `<img>` for images, `<video controls>` for video (range requests make seeking work, §6.6.4), an `<iframe>` for PDFs, and no preview at all for other kinds. Buttons: **View** (the file itself, same tab) and **Download** (`?download=1`, which sets `Content-Disposition: attachment`).
- **States** — *No title set* (the metadata line stands alone); *multi-file, no entry point* (the body is R7's listing inside this shell); *unrenderable* (download-only, with the content type stated); *expired mid-session* (the next request is R3).
- **Interactions** — Two links. No sharing controls, no copy-URL affordance, no account prompt: a recipient is never invited to become a user (§4.7).
- **Copy references** — §12.7 (R2).

## R3 — Link expired or revoked

- **Purpose** — Tell someone who was legitimately given a link that the link has ended — the single deliberate exception to P1's blanket 404.
- **Route** — `/s/{token}` and anything beneath it, when the link is past `expires_at`, revoked, burned past `maxViews`, or its artifact was trashed. Status **410**, code `link_expired`.
- **Permissions** — Anyone holding the URL.
- **Layout** — The shared shell: one heading, one sentence, nothing else.
- **Components** — "This link is no longer active." plus one line suggesting they ask whoever sent it for a new one. **No artifact name, no owner, no expiry date, no reason** — expired, revoked, burned, and trashed are indistinguishable (§7.6). No retry control, since there is nothing to retry.
- **States** — One. There are no variants, deliberately: a differing page would leak which of the four things happened.
- **Interactions** — None. The page has no controls at all.
- **Copy references** — §12.7 (R3).

## R4 — Not found

- **Purpose** — The universal answer for anything the visitor may not have. Status **404**.
- **Route** — Any artifact path that does not resolve, resolves to something the visitor cannot view, has an expired TTL, is trashed, or names a missing file inside a visible artifact.
- **Permissions** — Everyone, in every state.
- **Layout** — The shared shell: heading, one sentence.
- **Components** — "Not found." and one neutral line. **Byte-identical for every cause** (P1): the body, the headers, and the status must not differ between "no such artifact" and "not yours", and negative resolutions are cached with the same TTL as positive ones so the timing matches too (§6.5.2). No sign-in link — offering one would tell an unauthenticated scanner that signing in might help.
- **States** — One, with one exception that is not a state change: if an artifact defines its own `/404.html`, that file is served with status 404 in place of this page for paths inside that artifact (§6.6.1). A signed-in owner hitting a missing path inside their own artifact sees the same page; the dashboard's in-shell not-found block (11.29.10) is a different surface entirely.
- **Interactions** — None.
- **Copy references** — §12.7 (R4).

## R5 — Rate limited

- **Purpose** — Say that too many requests arrived and when to come back. Status **429**.
- **Route** — Any surface: artifact paths, `/s/*`, the API (which returns the JSON envelope instead when the client accepts JSON), the dashboard.
- **Layout** — The shared shell.
- **Components** — One heading, one sentence naming the wait in minutes derived from `Retry-After`. The bucket name is **not** shown to recipients; it appears only in `detail.bucket` on API responses, where an agent can act on it (§10.2).
- **States** — Two: an anonymous or recipient visitor gets the plain page; a signed-in dashboard user gets the in-app version (11.29.10) with a live countdown, because they can usefully wait in place.
- **Interactions** — None on the static page.
- **Copy references** — §12.7 (R5).

## R6 — Maintenance

- **Purpose** — Answer when the API is down, without the API. Status **503**.
- **Route** — Served by Caddy from a static file when `forward_auth` fails or the socket is unreachable (§2.4.1).
- **Layout** — The shared shell.
- **Components** — One heading, one sentence, and no timestamp — a static file cannot know when service resumed and a stale estimate is worse than none. No auto-refresh meta tag: an unattended tab reloading a downed service is exactly the traffic an operator does not need mid-incident.
- **States** — One.
- **Interactions** — None. This page is a file on disk with no dependencies; it must render if Postgres, Redis, and the API are all gone.
- **Copy references** — §12.7 (R6).

## R7 — Artifact file listing

- **Purpose** — Show the contents of a bundle that has no entry point, as a plain index. Status **200** (§6.6.2).
- **Route** — The root of any artifact whose live version resolves no `entry_path`, at whichever address the visitor reached it by: `/name`, `/~handle/name`, or `/s/{token}`.
- **Permissions** — Whoever could reach the artifact. **Listings exist only for the artifact being addressed** — there is no listing of a space, ever, for anyone.
- **Layout**

```
┌──────────────────────────────────────────────┐
│  share.c52.com                               │
│                                              │
│  postcal                                     │
│  3 files · 110 KB                            │
│  ────────────────────────────────────────    │
│  index.html                text/html  18 KB  │
│  style.css                  text/css  4.1 KB │
│  img/chart.png            image/png  88.1 KB │
└──────────────────────────────────────────────┘
```

- **Components** — The artifact `name` (or `title` when set), the file count and total size, then one row per file: path, content type, size — each path a relative link so it resolves under whichever address is in the bar, including `/s/{token}/…` (§7.6). Sorted by path, directories grouped, using the same inline CSS as R3–R6.
- **States** — *Reached through a share link* (identical page; the heading shows the title only if set, and never the owner's handle); *single file* (cannot occur — §5.5 rule 4 always assigns an entry path); *empty version* (cannot occur — a version has at least one file).
- **Interactions** — Links only. No sorting, no search, no download-all: those need JavaScript or an API call, and this page has neither.
- **Copy references** — §12.7 (R7).

---

## 11.29 — Global patterns

### 11.29.1 App shell

Everything under `/~/` except 11.1–11.4 renders inside one shell: a fixed 240px sidebar, a 56px top bar, and a scrolling main region.

**Sidebar**, top to bottom:

| Group | Items |
| --- | --- |
| Wordmark | `Share` → `/~/artifacts` |
| **Library** | Artifacts (11.5), Shared with me (11.14, hidden until the instance has more than one user), Trash (11.15) |
| **Agents** | API tokens (11.18), Audit log (11.23) |
| Footer | Storage meter — a thin bar with `storageBytes / quotaBytes` → 11.25; then the user chip |

Counts appear beside Trash and Shared with me only when non-zero. A dot appears beside Audit log when 11.20 has an unacknowledged anomaly.

**Top bar**: a search input that opens the 11.16 palette on focus, the **Upload** button (11.17), and the user menu.

**User menu**: display name, handle, and email; then Settings (11.21), Security (11.19), Security overview (11.20), Users (11.22, root only), Instance status (11.28), Help (11.27), Sign out.

Below 900px the sidebar becomes an off-canvas drawer behind a hamburger; the top bar keeps search and Upload. Below 600px the search input collapses to an icon.

### 11.29.2 The sharing-state indicator

One component, one appearance, everywhere an artifact appears — the list, detail, search results, viewer, shared-with-me, trash, and the create-link summary. Three states, from `visibility` (§7.8):

| State | Glyph | Label | Detail line |
| --- | --- | --- | --- |
| `private` | `○` hollow, neutral | **Private** | "Only you" — or "Only you and anyone you grant" where space allows |
| `granted` | `●` filled, informational | **Shared with 2 people** | Handles, where space allows |
| `shared` | `◆` filled, amber | **Link active** | **Always** the absolute expiry of the soonest-expiring live link: `expires 7 Sep 2026, 18:04 UTC`, with `(in 14 days)` where the container is wide enough |

Rules that hold without exception:

1. When both grants and links are live, `shared` wins — the widest true thing is what gets shown (§7.8).
2. **A live link never renders without its expiry.** In a space too narrow for the full string, the row wraps or truncates the artifact's title instead; the expiry is the last thing to go, and if it cannot be shown, the state renders as an icon-only chip whose accessible name and tooltip carry the full absolute string.
3. A padlock glyph is appended when any live link has `hasPassword`.
4. Inside 48 hours of expiry the amber deepens to a warning treatment; the label and the data do not change.
5. The component is never interactive in a list row — clicking a row opens the artifact. In detail contexts it links to 11.12.

### 11.29.3 Time

- **Absolute is the truth; relative is the hint.** Any time that governs access — link expiry, artifact TTL, trash purge date, token expiry, session expiry — renders as `7 Sep 2026, 18:04 UTC` with the relative form in parentheses. Never relative alone.
- Times that are merely informational — "updated", "last used", "last viewed" — render relative (`2h ago`, `3 days ago`) with the absolute value in the `title` attribute and in the accessible name.
- Anything older than 7 days renders as an absolute date even in the informational case; "47 days ago" is not information anyone can use.
- Timezone follows `settings.timeZone`, defaulting to UTC, and the zone abbreviation is always printed. Dates are `D MMM YYYY`, times `HH:mm` 24-hour, seconds only in the audit log.

### 11.29.4 Tables and pagination

- Left-aligned text, right-aligned numbers, monospace for names, paths, hashes, and token prefixes.
- Row height 56px when a secondary line is present, 40px otherwise. Rows are `<a>`-wrapped so middle-click and modifier-click work.
- Sort is a header control only where the API supports the sort (§8.7); unsupported columns are not clickable rather than clickable-and-inert.
- **Pagination is cursor-based everywhere and page numbers appear nowhere.** Forward-only lists (artifacts, activity, trash) use a single **Load more** that appends. Bidirectional lists (audit) use **Newer** / **Older**, replacing the page. The footer states `50 of 218` where a total is cheaply known and `50 shown` where it is not. Offsets are unsupported by the API (§5.1.2) and no UI implies them.
- Empty and error states render inside the table body, preserving the header row, so the column structure does not jump.

### 11.29.5 Toasts

Bottom-left, stacked to a maximum of three, 5 seconds for a confirmation, 10 seconds when it carries an **Undo**, and indefinite for an error until dismissed. One line of text plus at most one action. Errors carry the `error.code` in small type so a user can quote it, and the `requestId` behind a copy control. Toasts never carry a password, a token, or a share URL — those live in their own one-time panels.

### 11.29.6 Destructive confirmation

Every destructive action confirms in a dialog that states three things in this order: **what happens**, **whether it can be undone and for how long**, and **what it does not do**.

| Action | Reversible | Confirmation |
| --- | --- | --- |
| Move to trash | Yes, 30 days | Standard dialog; names the restore date absolutely; states that live links and grants are revoked now and are not restored on restore |
| Delete permanently / Empty trash | **No** | Type-to-confirm: the artifact's name, or the phrase `empty trash` |
| Revoke a share link | **No** | Standard dialog, stating that recipient sessions die immediately and a new link means a new URL |
| Change or remove a link password | **No** (the old password is gone) | Standard dialog, stating that everyone currently viewing is signed out of the link |
| Revoke a token | **No** | Standard dialog naming the agent and stating its artifacts remain |
| Revoke a passkey | **No** | Standard dialog naming how many sessions die with it |
| Delete a version | Yes, trash window | Standard dialog |
| Disable a user | Reversible by re-enabling | Standard dialog listing what is revoked and what is retained |

The primary button in a destructive dialog carries the destructive treatment and a verb, never "OK". The cancel button is focused on open. Type-to-confirm dialogs disable the primary button until the string matches exactly, case-sensitively.

### 11.29.7 Keyboard shortcuts

| Key | Action |
| --- | --- |
| `⌘K` / `Ctrl-K` | Command palette (11.16) |
| `/` | Focus search, when no input is focused |
| `g` then `a` / `s` / `t` / `k` | Go to artifacts / shared / trash / tokens |
| `u` | Upload (11.17) |
| `Esc` | Close dialog, palette, or viewer; never navigates back a level from a plain screen |
| `↑` `↓` | Move selection in tables and the palette |
| `⏎` | Open the selected row |
| `⌘⏎` | Open the selected row's artifact URL in a new tab |
| `?` | Shortcut reference sheet |

No single-letter destructive shortcut exists. Deleting always takes a menu and a confirmation.

### 11.29.8 Responsive breakpoints

| Width | Changes |
| --- | --- |
| ≥ 1280px | Full layout; 11.7's right rail is present; 11.11 shows both panes side by side |
| 1100–1280px | 11.7's rail narrows to 280px |
| 900–1100px | 11.7's rail collapses beneath the main column, **sharing card first**; 11.11 stacks with compare first |
| 600–900px | Sidebar becomes an off-canvas drawer; tables drop the size and version columns; the sharing state stays |
| < 600px | Tables become stacked cards: name and title on line one, the sharing state on line two, updated and size on line three. Search collapses to an icon. Dialogs go full-screen with a sticky footer holding the primary action |

The sharing state is present at every width. It is the last thing any breakpoint is allowed to remove, and no breakpoint removes it.

### 11.29.9 Empty states

One glyph, one heading naming what is absent, one sentence of explanation, and at most one action. Two rules: an empty state caused by filters always offers **Clear filters** and keeps the filter bar; an empty state the user cannot act on (11.14 with nothing shared) offers no action rather than a decorative one.

### 11.29.10 Error states

- **Field errors** — inline beneath the field, from `error.detail.fields[].path`.
- **Region errors** — a bordered block replacing just the failed region: one line from `error.message`, the `error.code` in small type, **Retry**, and a copy control for `requestId`. Sibling regions stay live.
- **Route errors** — a full-page block inside the shell for 404 and 403 on dashboard routes. The 404 variant is worded identically whether the artifact does not exist or is not the caller's (P1).
- **Connection lost** — a top strip when three consecutive requests fail at the transport layer, with automatic retry and a manual **Retry now**. Distinguished from `503`, which routes to the maintenance message.
- **Never** invent a friendly message over an unknown code: show `error.message` from the API, which §12.8 guarantees is one sentence, safe to print, and free of paths and credentials.

### 11.29.11 Skeleton loading

Skeletons, not spinners, wherever the shape of the result is known: table rows, cards, the artifact header, both panes of 11.11. They match the real element's dimensions so nothing reflows on arrival. Spinners are reserved for in-place actions with an unknown duration — a button mid-request, an upload commit. Content that arrives in under 200ms renders without a skeleton at all, to avoid a flash. The artifact viewer (11.9) shows a neutral panel rather than a skeleton: the artifact's own load is the real feedback.

---

## 11.30 — Accessibility

Baseline: WCAG 2.2 AA. These are the requirements this product's specific shapes create.

### 11.30.1 Focus management in dialogs

Every dialog — 11.13 above all — is a `<dialog>` element with `aria-modal="true"` and `aria-labelledby` pointing at its heading.

- On open, focus moves to the dialog's heading (not the first field), so a screen reader announces what the dialog is before what it wants.
- Focus is trapped for the dialog's lifetime and returns to the invoking control on close, including when the close came from the browser's back button.
- `Esc` closes 11.13's Configure and Confirm states. **`Esc` does not close 11.13's Created state or 11.18's created-token state** — a one-time secret must not be dismissible by a reflex keystroke. In those states the only exit is the **Done** button, which is the initially focused element, and the dialog's `aria-describedby` points at the "shown once" sentence.
- Destructive dialogs open with **Cancel** focused.
- Type-to-confirm inputs are `aria-describedby` the exact string required.

### 11.30.2 A keyboard path for every primary action

No action in the product requires a pointer. Specifically: create a share link (`g a`, `↓`, `⏎`, then the tab bar, then the button), copy a generated password (the copy control is a real button in the tab order immediately after the password text), restore a version, restore from trash, revoke a link or token, set an entry file, and approve a device code. Hover-revealed controls — row checkboxes, row menus — are focusable and become visible on focus, not only on hover.

### 11.30.3 ARIA for the artifact table and the file tree

- **Artifact tables** use real `<table>` markup with `<th scope="col">`. Sortable headers carry `aria-sort`. Each row's accessible name is composed as: name, title if present, **sharing state including the absolute expiry**, updated time absolute, size. The sharing state is never conveyed by colour or glyph alone — the visible label carries the word, and the icon-only variant (11.29.2 rule 2) has an `aria-label` with the full string.
- **The file tree** (11.8) is `role="tree"` with `role="treeitem"`, `aria-expanded`, `aria-level`, and `aria-setsize`/`aria-posinset` on each node. Arrow keys navigate, `←`/`→` collapse and expand, `⏎` opens. The visual indentation is mirrored by `aria-level` rather than inferred from it.
- Bulk-selection checkboxes are grouped under an `aria-label` naming the selection count, and the bulk-action bar is `role="region"` with `aria-live="polite"` so the count is announced as it changes.

### 11.30.4 Contrast and colour

- Text meets 4.5:1; large text and UI boundaries meet 3:1; focus rings meet 3:1 against both the element and its background.
- The three sharing states are distinguishable without colour: hollow circle, filled circle, filled diamond, each with a text label. The amber "expiring soon" treatment adds a warning glyph rather than only deepening a hue.
- Destructive actions are identified by verb and confirmation flow, never by red alone.
- Both light and dark themes are specified in §13; every rule here holds in both.

### 11.30.5 Reduced motion

Under `prefers-reduced-motion: reduce`: skeleton shimmer becomes a static tint, dialogs and drawers appear without transform or fade, toasts appear and disappear without sliding, and progress bars keep their determinate fill (real information) while indeterminate spinners become a static label. No essential state is conveyed by motion anywhere.

### 11.30.6 Screen-reader announcements for async results

A single polite `aria-live` region for confirmations and a single assertive one for errors, both at the document level.

| Event | Politeness | Announced |
| --- | --- | --- |
| Toast confirmation | polite | The toast text |
| Toast error | assertive | The message plus the error code |
| List loaded / **Load more** | polite | "50 more artifacts loaded. 100 of 218." |
| Filter or search change | polite | The result count, debounced to fire once per settled query |
| Upload progress | polite | Every 25%, not per file, and not per byte |
| Share link created | assertive | "Share link created. Expires 7 September 2026 at 18:04 UTC. The password is shown once on screen." |
| Copy to clipboard | polite | "Link copied", "Password copied" |
| Optimistic action reverted | assertive | What was undone and why |

Announcements spell out the absolute expiry in full words rather than the abbreviated visual form, because an abbreviated date read aloud is worse than a long one.

### 11.30.7 R1 works without JavaScript

This is a hard requirement, tested, not a preference (§7.4).

- R1 is a complete HTML document containing a `<form method="post">` whose `action` is an absolute path. No script is required to submit it, and no script is present on the page.
- The password input has `autocomplete="current-password"` and `autofocus`, so a password manager can fill it and a keyboard user lands in it.
- The error state is a re-rendered document at 401, not a client-side update, so it is announced by every assistive technology as a new page.
- The same absence of JavaScript applies to R2–R7. R6 in particular must render from a static file with the API, database, and Redis all unavailable.
- Every one of these pages is legible at 320px wide, at 200% zoom, and with author styles disabled — which follows from their being a heading, a paragraph, and at most a form.
