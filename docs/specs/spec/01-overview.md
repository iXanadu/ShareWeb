# Part 1 — Overview, Privacy Model, and Glossary

## 1.1 What this document is

A complete, implementation-ready specification for **Share**, a privately hosted service where
AI agents post finished artifacts and their owner keeps, finds, and hands them out.

It is written to be handed to two audiences without further human input:

- **Claude Design**, which renders every screen in Part 11 using the design system in Part 13
  and the copy in Part 12.
- **Coding agents**, which implement Parts 2–10 and 15 and verify against Part 14.

There are no open questions and no `TBD` markers. An implementer who finds an ambiguity
applies the resolution rule in §1.9 and records the decision rather than stopping.

### 1.1.1 Fixed names

Unlike the earlier draft, these are decided, not placeholders:

| Thing | Value |
| --- | --- |
| Product name | **Share** |
| Host | `share.c52.com` — one hostname, no subdomains, no second edge |
| CLI binary | `share` |
| Config directory | `~/.share/` |
| System user, database, systemd units | `share`, `share`, `share-api` / `share-worker` |
| Admin tool | `sharectl` |
| API token prefix | `shr_` |

## 1.2 The problem

Agents produce finished things all day — a market report, a posting calendar, a repo diagram, a
dashboard, a summary for a client. Those things are trapped in a chat transcript. Keeping one
means downloading it; a multi-file HTML artifact with styles and images usually breaks when
you do. Sending one means an attachment or a screenshot. A week later nobody remembers which
conversation it was in.

The commercial services that solve this are good and free, and everything sent to them sits on
someone else's disks indefinitely, with file excerpts indexed so their search works. Some of
what these agents produce touches client information. That is the wrong home for it.

## 1.3 Goals

**G1. One call to post.** An agent with a finished artifact posts it and gets back a working
URL, in one operation, with no interactive step.

**G2. Reachable from anywhere.** One public hostname. It works from a laptop on hotel wifi and
from a phone. There is no VPN, no network membership, and no "which URL was it" problem.

**G3. Three honest levels of access.** Signed in only; anyone holding an unguessable link;
that link plus a password. The owner picks per artifact, and the interface makes the choice
plain at the moment of sharing.

**G4. Stable, memorable addresses.** An agent names an artifact `postcal` and it lives at
`share.c52.com/postcal` — typed, bookmarked, linked from other artifacts, updated in place
week after week without the URL changing.

**G5. Agent-native, MCP first.** A remote MCP endpoint and an HTTP API of equal capability,
plus a CLI that can do everything either can. Nothing to install to get started.

**G6. Safe for agents to have full control.** Agents may overwrite and delete their own work.
That is only acceptable because overwrites keep versions and deletes go to a trash that can be
restored from.

**G7. Operable by one person.** One modest server, one database, files on local disk, one
backup job. No object storage, no queue broker beyond Redis, no orchestrator.

**G8. It never reads your files.** Not for titles, not for search, not for anything.

## 1.4 Non-goals

**N1. It is not a website host.** Share serves static artifacts. No server-side code, no
databases for published pages, no build steps, no application runtime. This line is what keeps
the system small enough for one person to hold in their head.

**N2. No embedded data storage or API proxying.** An earlier draft of this design let published
pages store records and call upstream APIs with server-injected credentials. Both are cut. They
were the largest source of security surface in the system and they serve a use case — building
applications — that N1 already excludes.

**N3. No teams, roles, or permission matrices.** An account is a person with a space. Sharing
is per-artifact. There is no owner/admin/member hierarchy, no invitations with roles, no
workspace.

**N4. No public sign-up.** Accounts exist because the operator created them.

**N5. No high availability.** One server. Restarts interrupt in-flight uploads. Acceptable.

**N6. No full-text search inside artifacts.** Deliberate, per G8 and P5.

**N7. No content moderation pipeline.** The operator and their invited users are the only
publishers.

## 1.5 Who uses it

| Persona | Credential | Can do |
| --- | --- | --- |
| **Owner** | Passkey | Everything. Holds the root namespace. Creates accounts. |
| **Agent** | API token `shr_…` | Full CRUD inside its owner's space. Cannot create share links unless its token carries `share:create`. |
| **User** | Passkey | Same as the owner, inside their own `~name` space. Sees their own artifacts plus what has been shared with them. |
| **Recipient** | A link, and possibly its password | Views one artifact. No account, nothing to install. |

There is no anonymous *post*. Every write carries a token or a session, and every token belongs
to an identity. This is the single non-negotiable divergence from the commercial reference: an
unauthenticated publish endpoint is an unlogged way for anything with shell access to move data
out of the perimeter.

## 1.6 Privacy and threat model

### 1.6.1 Where the wall is, and what that costs

The wall is **identity and capability**, not network position. Everything lives on a public
hostname; a sign-in or an unguessable link decides what a visitor sees.

An earlier draft put the wall at the network — artifacts were unroutable from the internet
unless deliberately exposed. That is a stronger property, and it was rejected for a good
reason: it made the owner's own access painful away from home, which is the opposite of the
point. The tradeoff is stated here rather than buried: **there is now a door facing the street,
and authentication is what holds it shut.**

Three things make that acceptable:

1. The door is the only thing on that surface. Share runs no user code, has no published-page
   database, and makes no outbound requests on behalf of published content. The attack surface
   is a static file server, a login, and a token check.
2. Passkeys (§4) remove the entire password-guessing and password-reset attack class.
3. Unguessable links carry 128 bits of entropy and always expire.

### 1.6.2 Adversaries considered

**A1. The internet at large.** Scans for artifacts, guesses names and share links, probes for
traversal. Mitigations: signed-in-only is the default; share tokens are 128-bit; there is no
listing, directory, or enumeration anywhere; strict path normalisation (§6.4); every artifact
served `noindex` with a deny-all `robots.txt`.

**A2. A holder of one share link.** Tries to reach other artifacts, the owner's namespace, or
the API. Mitigations: a share token authorises exactly one artifact and reveals neither owner
nor artifact name until used; share sessions never authorise the API or the dashboard (§4.7).

**A3. A compromised or looping agent.** Holds a valid token and shell access. This is the
adversary the product is shaped around. Mitigations: tokens are per-agent, named, scoped, and
individually revocable; `share:create` is a separate scope not granted by default; every post,
overwrite, delete, and share is audit-logged with token ID and source IP; deletes go to trash;
overwrites keep versions; anomaly thresholds notify the owner (§10.4).

**A4. Another user on the instance.** Mitigations: spaces are hard boundaries. There is no API
by which any principal writes into a space it does not own (§5.2). Reading requires an explicit
per-artifact share.

**A5. The hosting provider.** Has disk access. Mitigations: full-disk encryption (§15.1) and
encrypted off-host backups. Artifact bytes are not application-layer encrypted — they must be
servable — and this is a stated residual risk.

### 1.6.3 Guarantees

Each has a test in Part 14.

| ID | Guarantee | Test |
| --- | --- | --- |
| **P1** | An artifact with no share link and no signed-in session returns the same `404` as a name that does not exist — same body, same headers, no measurable timing difference. | T-PRIV-01 |
| **P2** | No artifact can be created, updated, or deleted without a token or a session. | T-PRIV-02 |
| **P3** | Creating, extending, or revoking a share link writes an audit record with actor, token ID, source IP, artifact, expiry, and whether a password was set. | T-PRIV-03 |
| **P4** | Every share link has a non-null expiry. There is no permanent share link. | T-PRIV-04 |
| **P5** | Artifact contents are never read for indexing, summarising, embedding, titling, or classification. Titles come from the poster or do not exist. | T-PRIV-05 |
| **P6** | Full IP addresses are never persisted. View records store a salted daily hash that cannot be recomputed the next day. | T-PRIV-06 |
| **P7** | No principal can read, write, list, or enumerate any artifact in a space it does not own, except through a share link explicitly granted to it. | T-PRIV-07 |
| **P8** | Deleting an artifact and emptying the trash removes its rows and dereferences its files; the next collection pass removes bytes no surviving version references. | T-PRIV-08 |
| **P9** | Revoking a share link, changing its password, or deleting the artifact invalidates every existing recipient session for it on the next request. | T-PRIV-09 |

### 1.6.4 Residual risks, stated

- Artifact bytes sit unencrypted on disk so they can be served. Disk encryption is the only
  defence against physical or provider access.
- A share link is a bearer credential. It does not get guessed; it gets forwarded, saved,
  screenshotted, and archived. **Expiry is the control**, which is why P4 has no exception.
- Losing every registered passkey and the recovery code means the only way back in is
  server-side (§4.5). That is a real recovery burden accepted in exchange for deleting the
  password-reset attack class.
- A single server holds everything. Backups are encrypted; the live system is not.

## 1.7 Principles

1. **Signed-in is the default.** Anything that widens access is an explicit act with an end
   date and an audit record.
2. **Sharing is an object, not a setting.** A share link is a thing you create, list, and
   revoke — never a checkbox toggled in passing.
3. **The agent path and the human path are the same API.** The dashboard calls what the MCP
   server calls.
4. **Nothing is inferred from content.**
5. **Destructive actions are reversible.** Overwrite keeps versions; delete goes to trash.
6. **Failures are specific.** Every error carries a stable code and a sentence an agent can act
   on.
7. **Files are stored once.** Identical bytes are shared across versions, artifacts, and users,
   so history and copies are nearly free.

## 1.8 The whole product in twelve lines

```
agent → post artifact "postcal" (4 files)
      ← https://share.c52.com/postcal          signed-in only

owner → open it, from anywhere, one passkey tap

agent → post "postcal" again next week
      ← same URL, version 2, version 1 retained

owner → create share link, 14 days, with password
      ← https://share.c52.com/s/9fq2n4kw…      password: civil-marmot-71
                                                expires 2026-09-07 18:04 UTC
```

## 1.9 Ambiguity resolution rule

If this document is silent or self-contradictory:

1. Prefer the interpretation that exposes less.
2. Prefer the interpretation that matches an existing pattern in this spec.
3. Prefer the interpretation that adds no configuration surface.
4. Record it in `DECISIONS.md` at the repo root with the section number and the choice. Do not
   stop and ask.

## 1.10 Glossary

| Term | Meaning |
| --- | --- |
| **Artifact** | One published thing: a single file or a bundle of files that belong together. The unit of ownership, addressing, sharing, versioning, and deletion. |
| **Bundle** | An artifact with more than one file — an HTML page plus its styles, images, and fonts. Served as a unit with relative links intact. |
| **File** | An immutable blob of bytes, stored once instance-wide, addressed by its SHA-256. |
| **Name** | The artifact's address within its space: `postcal`, `q3/market-report`. Chosen, memorable, stable. |
| **Space** | One user's namespace. `~sarah` for a user, the bare root for the owner. A hard boundary: nothing writes across it. |
| **Version** | An immutable snapshot of an artifact's files. Overwriting creates one; earlier ones remain. |
| **Share link** | A capability URL at `/s/{token}` granting view access to exactly one artifact, always expiring, optionally password-protected. |
| **Recipient** | Someone viewing through a share link. No account. |
| **Token** | An agent's credential, `shr_…`, scoped and revocable. |
| **Passkey** | A human's credential. WebAuthn. No password exists anywhere in the system. |
| **Trash** | Where deleted artifacts wait 30 days before real deletion. |

## 1.11 Document map

| Part | Contents | Audience |
| --- | --- | --- |
| 1 | Overview, privacy model, glossary | Everyone |
| 2 | Architecture, deployment, request paths | Backend, ops |
| 3 | Data model and storage | Backend |
| 4 | Identity: passkeys, sessions, tokens, recovery | Backend, frontend |
| 5 | Spaces, ownership, and the artifact API | Backend, agents |
| 6 | URL model, resolution, and serving | Backend |
| 7 | Sharing: links, passwords, expiry, copies | Backend, frontend |
| 8 | Versions, trash, retention, and search | Backend |
| 9 | Agent surface: MCP and CLI | Agents |
| 10 | Limits, audit, notifications | Backend, ops |
| 11 | Every screen and state | **Claude Design**, frontend |
| 12 | All product copy | **Claude Design**, frontend |
| 13 | Design system | **Claude Design**, frontend |
| 14 | Test plan and acceptance criteria | All |
| 15 | Install and operations | Ops |
| 16 | Phasing and definition of done | Everyone |
