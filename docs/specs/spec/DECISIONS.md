# DECISIONS

Ambiguities and contradictions found in the draft, resolved per §1.9. Each entry states the
conflict, the resolution, and what it cost. Later entries append; nothing here is edited once a
build depends on it.

---

## D-01 — The spec does not own appearance

**Sections:** §11 (all), §13 (all)

**Conflict.** Part 11 specified layout in prose and diagrams — a 240px sidebar, 40px and 56px
table rows, a 520px modal, a 48px viewer bar, a 420px recipient column. Part 13 specified the same
layouts from its own token scale. They disagreed in roughly a dozen places. Part 13 additionally
authored a complete visual system for a project with an existing one.

**Resolution.** The spec is authoritative on presence and behaviour; the design is authoritative
on appearance. Part 11 keeps purpose, route, entry points, permissions, data sources, states,
interactions, and copy references, and loses layout prose and diagrams. Part 13 shrinks to the
visual requirements the product genuinely imposes for safety and accessibility, and names
Broadsheet as the visual system.

**Cost.** A developer can no longer read a pixel dimension out of the spec. They were reading one
of two conflicting dimensions before, so this is a gain disguised as a loss. Anything a diagram
communicated that a rule does not is now communicated by the design output, which is a better
medium for it.

---

## D-02 — Amber belongs to link-active alone

**Sections:** §13.2.2, §13.2.3, §11.5, §11.7, §11.12, §11.29.2

**Conflict.** §13.2.2 deliberately shared the amber hue family between the `shared` sharing state
and the `warning` family, and called that sharing "intentional and load-bearing". But §D1
separately forbade any other badge from being amber-gold, and screens routinely stack a warning
banner directly above a link-active badge — the same hue meaning "a deliberate act by the owner"
in one place and "this needs your attention" a few pixels away.

**Resolution.** Amber is reserved for the `shared` sharing state and its expiring modifier, and
appears nowhere else. Advisory and warning banners are rendered without a warm fill — neutral
surface, hairline boundary, icon at text weight. Errors and destructive actions keep red.
Sharing-state indicators never use red.

**Cost.** One paragraph of §13.2.2's reasoning, which was the weaker half of it. Warning banners
lose colour as a wayfinding cue and rely on position and a full sentence instead, which is
adequate for a banner and inadequate for a chip — hence the asymmetry.

---

## D-03 — Modifier chips may collapse to text; the state badge may not

**Sections:** §13.2.3, §13.6.8.5, §11.29.2, §11.29.8

**Conflict.** "Never colour alone" (§D4) forbids dropping the word from a state badge and says
that if the space is not there, the layout is wrong. "Identifiers are literal" (§D6) forbids
truncating an artifact name. But a live, password-protected, nearly-expired link legitimately
renders a state badge plus two modifier chips in a dense row beside an untruncatable monospace
name, on a narrow phone. All three rules cannot hold in one line.

**Resolution.** The state badge keeps colour, icon and word at every width, without exception. The
modifier chips are modifiers, not states (§13.2.3 says so), and are the thing that moves: on
narrow viewports the row becomes two lines and the modifiers render as plain text alongside the
expiry the row already carries — `Link · expires 7 Sep 2026, 18:04 UTC · password`. §11.29.3
already requires that absolute expiry as text in the row, so no fact is lost and §D4's own escape
clause is satisfied.

The dense row variant is available on wide viewports only. Density is a preference; the sharing
state is a privacy guarantee, so density is what yields.

**Cost.** Narrow-viewport rows are taller than a dense desktop row, and the two-line form is the
normal case on a phone rather than an exception.

---

## D-04 — A link password can be rotated

**Sections:** §11.13.7, §11.12, §7.4, P9

**Conflict.** 11.13.7 shows a generated password exactly once, refuses `Esc` and backdrop
dismissal, and closes only on **Done** — correct, and consistent with §11.30.1. But it did not say
what happens to a user who presses Done without copying. That user holds a live link nobody can
open, and the draft offered them only "create a new link", which changes the URL they may already
have sent.

**Resolution.** Two changes. **Done** stays enabled — blocking it inverts §D5 by obstructing the
safe direction — but when the copy control has not been used, Done asks once, inline: the password
has not been copied, and without it the link cannot be opened. Copy, or close anyway.

And 11.12 gains **Set a new password** on every password-protected link card. Rotating does not
widen access, so it does not need creation's full ceremony; it does invalidate every recipient
session for that link under P9, so it takes a small dialog naming that consequence, then shows the
new secret in the same one-time panel.

**Cost.** One more control on the link card and one more state in §7.4. The alternative was a
dead-end the product had no way out of.

---

## D-05 — Broadsheet is the visual system

**Sections:** §13 (all)

**Conflict.** Part 13 authored a design system from first principles. The project it was written
for already had one.

**Resolution.** Broadsheet is the visual system. Part 13's genuinely product-derived requirements
survive as requirements — the three sharing states and their relationships, colour-plus-icon-plus-
word, literal identifiers, the density target, the chrome-must-not-compete rule, both themes, the
recipient-page constraints, WCAG 2.2 AA. Its token tables, ramps, component anatomy and
dark-mode generation do not survive; those are the design's to decide and are decided in the
design project.

Where Broadsheet and the surviving requirements can both be satisfied, Broadsheet's answer wins:
the serif, and the preference for whitespace over rules and boxes.

**Cost.** Two visual vocabularies exist in the project's orbit — Broadsheet for everything, and
the console's own denser expression of it. That seam is normal and was going to exist either way.
The draft's version of it was two systems in one document contradicting each other, which is not.

---

## D-06 — Rotating a link password needs an API that does not exist

**Sections:** §7.4, §11.12, D-04

**Conflict.** D-04 added **Set a new password** to every password-protected link card. `PATCH
/api/v1/links/{id}` accepts a `password` string, but has no way to ask the server to *generate*
one (`password: true` exists only on create), and does not say the new secret is returned.

**Resolution.** `PATCH /api/v1/links/{id}` accepts `password` as a string (set your own), `true`
(generate one), or `null` (remove it). When it generates, the response carries `password` exactly
once, with the same treatment as create. All three values revoke every recipient session on that
link (P9) and audit as `link.password_change`, which §10.7 already lists.

**Cost.** One more shape on an existing endpoint. Without it D-04's dialog has nothing to call.

---

## D-07 to D-13 — carried from the plumbing audit

Recorded here so they are not rediscovered; the reasoning is in `PLUMBING-AUDIT.md` §1.

| # | Conflict | Resolution |
| --- | --- | --- |
| **D-07** | `sh:tok:` names both share-link and API-token cache entries, at 300 s and 30 s (§2.4.2, §3.10, §4.6) | Split into `sh:ltok:` (share links, 300 s) and `sh:atok:` (API tokens, 30 s). Two credential classes never share a cache namespace |
| **D-08** | Deleting an expired session's draft version cascades the session row away, making `409 upload_session_expired` unreachable (§5.7, §3.4) | `upload_session.version_id` becomes nullable and drops its cascade; the session row survives to answer the commit |
| **D-09** | A hashed asset behind a share link matches both `no-store` and `immutable` (§6.6.5) | The share-link rule wins. Everything under `/s/*` is `no-store`, without exception |
| **D-10** | The device-code flow has `start` and `poll` but no `lookup`, `approve` or `deny` (§4.6.2, §11.26) | Add all three, session-authenticated. The approve response never contains the token — it goes to the polling agent |
| **D-11** | `/install.sh` and `/.well-known/*` are documented paths with no Caddy route, and `install.sh` is not reserved (§9.8, §2.4, §6.3) | Route both to the API; add `install.sh` to §6.3's reserved list |
| **D-12** | Redis holds idempotency records (§5.1.3) and `viewer_days` enforcement sets (A4) while §3.10 says nothing durable lives there | Both move to Postgres. A cache flush must not create a duplicate artifact or reset a burn-after-N ceiling |
| **D-13** | The dashboard's API surface is defined only by implication, in Part 11 | A new `05a-dashboard-api.md` owns those endpoints and shapes; Part 11 references it. Written before the first sprint |

---

## D-14 to D-17 — from the design work

Recorded per §1.9. The values are in `Foundations.dc.html`; these are the four places the design
had to decide something the spec had not anticipated.

### D-14 — The product adds a red, because Broadsheet has none

**Sections:** §13.3, §13.9

Broadsheet ships two accents — cyan and magenta — and no red. §13.3 nonetheless requires a red for
destructive actions and failures, and requires it to be unmistakable against `shared`'s magenta,
which sits three rows above it in the same list.

**Resolution.** One value, `#9e2b1e`, added as a product role rather than a system token: a dark,
low-saturation brick that differs from `#aa0b56` in lightness and in saturation, not only in hue.
It appears on destructive buttons and failure text and nowhere else — never a sharing state, never a
fill larger than a button. 6.4:1 on paper.

**Cost.** One colour in the product that is not in the design system. The alternative was
destructive actions in magenta, which would have collapsed 13.3's one-warm-colour-one-meaning rule
on its first screen.

### D-15 — The focus ring is ink, not the accent

**Sections:** §13.9

A cyan focus ring cannot clear 3:1 against a cyan primary button, and a magenta one cannot clear it
against the `shared` badge. Broadsheet's default is a 2px accent ring.

**Resolution.** `2px solid #201e1d` at `2px` offset — ink on light, `#ece9e7` on dark. One ring
that clears 3:1 against every element in the product, including both accents and paper.

**Cost.** The product's focus ring departs from the design system's. Keeping the system's would have
meant a per-element ring colour, which is how focus rings end up missing on the one element that
needed it.

### D-16 — Advisory banners are neutral and take a rule

**Sections:** §13.3, §13.5, §13.8

D-02 withdrew warm from warnings, leaving advisories with no colour at all. Broadsheet also forbids
structuring a page with rules.

**Resolution.** Paper ground, ink text, a 3px ink left edge, and the word `Note` or `Warning` in
the serif's italic. This is the one place in the chrome that prints a rule, because a banner must
stay distinguishable from body copy with author styles disabled (13.8.3).

**Cost.** One sanctioned exception to a design-system prohibition. Position and a full sentence do
the rest of the work, per D-02.

### D-17 — Dark theme is authored here, not inherited

**Sections:** §13.7

Broadsheet defines no dark theme; §13.7 requires one, and requires every rule in Part 13 to hold in
both.

**Resolution.** A dark ground authored in `Foundations.dc.html` — `#1a1918` press-ink rather than
black — with the three sharing states restated so their lightness order inverts while the three
steps and the warm/cool split survive. `shared` stays the only solid badge. Recipient pages get
dark from `prefers-color-scheme` alone, since they carry no JavaScript and so cannot hold a
preference.

**Cost.** A second ramp to maintain by hand, and a documented divergence: the dashboard honours an
explicit choice, the recipient pages can only honour the OS.

### D-18 — Seven marked departures from Broadsheet's component layer

**Sections:** §13.5, §13.9, §13.10

Broadsheet's `.btn`, `.input` and `.seg-opt` are sized for a page, not for a console: 13-14px
labels and 36px controls. §13.9 requires 44px hit targets and 4.5:1 on a 17px label, and §13.5 asks
for a screen someone can read for eight hours.

**Resolution.** Build against the design system's classes and override exactly seven things, listed
with their reasons in `Foundations.dc.html` § departures from Broadsheet's component layer:
`.btn` and `.input`/`.seg-opt` sizing, `.btn-primary`'s ink pair (accent-700 on white, 5.6:1,
where the system's pairing measures 3.0:1), a new `.btn-danger`, `.table`'s rule at the system's
own `--color-divider` rather than 8% ink, `.nav` gaining that same rule below a 56px bar, and
`.dialog` at 520px. Nothing else changes. Icons are real Phosphor duotone (`lock-simple`,
`users`, `link` for the three states), inline on `currentColor`, per the system's icon rule. The state
badge and the modifier chips are stated as not being `.tag`, with the reason.

**Cost.** Seven overrides to keep in step if the design system moves. The alternative was either a
console that fails 13.9 or an unmarked second button, and an unmarked drift is how a third button
gets built.

---

## D-19 — Python 3.13 on the build machine

**Sections:** §15.2

**Conflict.** The spec installs Python 3.12. This box's FastAPI projects use pyenv 3.13.

**Resolution.** Local and this repo target 3.13 (`share-3.13`). Production on WebOne may follow the spec's 3.12; the application does not depend on a 3.12-only API.

**Cost.** Two Python minors across environments. Acceptable.

---

## D-20 — Local data directory

**Sections:** §3.5, §15.1

**Conflict.** Spec stores files at `/var/lib/share`. That path needs root on hosta.

**Resolution.** Local defaults to `<repo>/var/share/{files,tmp}`. Production still uses `/var/lib/share`. Same sharding layout.

**Cost.** One extra setting (`SHARE_FILE_ROOT` / `SHARE_TMP_ROOT`).

---

## D-21 — FastAPI serves artifacts when Caddy is absent

**Sections:** §2.4, §6.5

**Conflict.** Spec has Caddy `forward_auth` + `file_server`. Caddy is not installed on hosta.

**Resolution.** `/internal/authorize` is implemented as specified. A catch-all in the API serves the blob after the same `can_view` decision. When Caddy exists (WebOne), disable the catch-all or let Caddy take `:443` and proxy only `/api`, `/~/`, `/internal`. `can_view` stays four lines either way.

**Cost.** Range requests and `sendfile` are worse locally than Caddy. Fine for the hosta sprint.

---

## D-22 — Bootstrap prints an API token and a session cookie before passkeys exist

**Sections:** §3.11, §4.2

**Conflict.** Spec completes bootstrap only after the first passkey. Phase 1 screens and WebAuthn are not built yet, and agents must post.

**Resolution.** `sharectl bootstrap` creates the root user, one `artifacts:read+write` token, and one 30-day `share_s` session, and prints both once. Passkey registration remains required before production. Token still does not get `share:create`.

**Cost.** A temporary credential-class shortcut on local. Remove when passkeys ship.

---

## D-23 — Schema as SQL files, not Alembic, this sprint

**Sections:** §3.1

**Conflict.** Spec names Alembic.

**Resolution.** `server/migrations/*.sql` applied by `db.apply_migrations`. Alembic can wrap these later without changing the SQL.

**Cost.** No autogenerate. Acceptable while the schema is still the spec's.

---

## D-24 — Local Postgres peer auth as the OS user

**Sections:** §15.2

**Conflict.** Spec uses role `share`. Local Homebrew Postgres authenticates the OS user with no password.

**Resolution.** Local `SHARE_DB_USER` is the OS user. Production uses role `share`.

**Cost.** None beyond the setting.

---

## D-25 — Cookie `Secure` is off on localhost

**Sections:** §4.4

**Conflict.** Spec sets `Secure` on `share_s`. Local hosta is HTTP.

**Resolution.** `Secure` is set when `SHARE_HOST` is not `localhost`/`127.0.0.1`. Production keeps `Secure`.

**Cost.** A local-only cookie flag fork. Remove when local TLS exists.

---

## D-26 — Dashboard APIs written as we built them

**Sections:** PLUMBING-AUDIT §2

**Conflict.** Token list/create/revoke, passkey list, and artifact file list had no request/response spec.

**Resolution.** This sprint:

- `GET /api/v1/artifacts/{name}/files` → `{items:[{path,size,contentType,sha256}]}`
- `GET /api/v1/artifacts/{name}/files/content?path=`
- `GET/POST /api/v1/tokens`, `DELETE /api/v1/tokens/{id}` — secret only on create
- `GET /api/v1/auth/passkeys` → `{items:[{id,name,createdAt,lastUsedAt,backupState,transports}]}`

`share:create` cannot be granted by an agent token. Device-code flow is still unbuilt.

**Cost.** These shapes become the contract for 11.8 / 11.18 / 11.19. Change them in this file, not silently.

---

## D-27 — Local URL is http://hosta:8310, never :8000

**Conflict.** Port 8000 is already used by another app on the dev box. The owner is not on that machine and cannot use localhost.

**Resolution.** Bind a dedicated LAN port. `SHARE_HOST` is the box hostname. HTTP origin and RP ID follow that host. Cookie `Secure` is off for single-label names.

**Cost.** Passkeys created against localhost will not work on the LAN hostname.

---

## D-28 — WebOne prod is nginx + loopback, not Caddy

**Sections:** §2.4, chat.c52 install

**Conflict.** Spec names Caddy `forward_auth`. Production for c52 apps is nginx.

**Resolution.** First prod deploy: systemd unit on loopback, nginx terminates TLS. FastAPI serves artifacts. Caddy can wait.

**Cost.** `sendfile` is worse than Caddy `file_server`. Acceptable until a dedicated edge is worth it.
