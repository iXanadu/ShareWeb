# Use cases

The document the draft did not have. Parts 2–10 say how the machinery works; Part 11 says what the
screens are; this says what people actually do, end to end, so that a developer can check the
machinery against the job and an implementer can tell when they are finished.

Every case names its actor, what starts it, the path it takes through the API and the screens, and
**what must be true at the end**. That last line is the acceptance criterion; Part 14 should have a
test for each one.

Actors are the four in §1.5: **Owner** (passkey, root namespace), **Agent** (token `shr_…`),
**User** (passkey, `~handle` space), **Recipient** (a link, maybe a password).

Names used throughout, for readability: Robert is the owner; `grokbot@hosta` and
`claude-code@hosta` are his agents; `~sarah` is a second user; the Fairfield listing team are
recipients.

---

## Part A — The core loop

### UC-1 · An agent posts a finished thing

**Actor** Agent · **Phase** 1 · **Spec** §5.4, §9.3

`grokbot@hosta` has built a four-file HTML posting calendar. It calls the MCP `share_post` tool
with a name (`postcal`), a title, and the file manifest. The three-phase post declares the
manifest, uploads only the files the server does not already hold, and commits. It gets back
`https://share.c52.com/postcal`.

**True at the end.** The artifact exists at v1, private, owned by Robert, attributed to
`grokbot@hosta`. One URL was returned and it works for a signed-in Robert. Nothing is reachable
without a session. An audit record names the token and the source IP. No title, summary, tag or
thumbnail was derived from any file's contents (P5).

**Fails when** the name is taken (`409`, and the agent is told it may overwrite), the name is
invalid (`422`), quota is exhausted (`413`), or a path fails normalisation (`422`). Every failure
is one sentence the agent can act on without a human.

### UC-2 · The same agent posts it again next week

**Actor** Agent · **Phase** 1 · **Spec** §5.6, §8.2

Same name, new files. The post becomes v2. v1 is retained.

**True at the end.** The URL is unchanged — this is G4, and it is the whole reason names are
chosen rather than generated. v1 is listed on 11.10 with its file count and author. Any live share
link now shows v2 to whoever holds it, without being touched (§7.2). Retention has not pruned
anything a user pinned.

**Watch for.** This is the case that makes share links slightly dangerous and it is stated to the
owner at creation time, in 11.13's summary block, naming the agent. It is the sentence most likely
to be cut for brevity and it must not be.

### UC-3 · Robert opens it from a phone, away from his desk

**Actor** Owner · **Phase** 1 · **Spec** §4.3, G2

He types the host on cellular data. One passkey tap on 11.1, no password anywhere, lands on 11.5,
taps the row, sees 11.7 with the sharing state above the fold.

**True at the end.** No VPN, no network membership, no "which URL was it". The sharing card is the
first thing in the stacked layout on a narrow viewport, because the answer to "who can reach this"
must never be below the fold. Session is 30 days sliding.

### UC-4 · Robert sends it to a client for two weeks, with a password

**Actor** Owner · **Phase** 2 · **Spec** §7.3–7.4, §11.12, §11.13

From 11.12 he sees what is already true, then goes to 11.13. He reads what becomes reachable, picks
14 days, leaves the password on **generate**, labels it "Fairfield listing team", continues to the
read-back, creates. The password appears once. He copies link and password together and pastes both
into a message.

**True at the end.** One link exists with a non-null expiry (P4 — there is no permanent link and no
way to reach one). An audit record carries actor, token, IP, artifact, expiry, and whether a
password was set (P3). Robert has an email saying a link was created. The artifact's sharing state
is now `shared`, everywhere it appears, with its absolute expiry. The password is nowhere on any
server in readable form.

**Fails when** the artifact is trashed (`422`, the dialog refuses to open), the TTL exceeds the
ceiling (`422`, inline), or he has made twenty links this hour (`429`, and he is notified).

### UC-5 · A recipient opens the link

**Actor** Recipient · **Phase** 2 · **Spec** §4.7, §7.4, R1

They tap it on a phone. R1 asks for a password and nothing else — no artifact name, no title, no
owner, no expiry, no branding. They paste it, get a recipient session scoped to that one link, and
see the artifact with its relative links intact.

**True at the end.** The recipient never had an account and was never invited to make one. Their
session authorises exactly one artifact, and cannot reach the API or the dashboard. The view is
recorded as a salted daily hash, not an address (P6). The page worked with JavaScript disabled,
which is tested, not assumed.

**Fails when** they get the password wrong (401, one line, no attempt counter), try too often
(429, and Robert is emailed the first time), or arrive after expiry (410 → R3).

### UC-6 · The link expires and they come back

**Actor** Recipient · **Phase** 2 · **Spec** §7.5, R3

R3 says the link is no longer active and suggests asking whoever sent it. Nothing else.

**True at the end.** Expired, revoked, burned past its view limit, and "the artifact was trashed"
are indistinguishable — same page, same status, no reason given. The link died the second after
its expiry, before any sweep ran. Robert had an email 24 hours before it happened.

### UC-7 · Robert kills a link early

**Actor** Owner · **Phase** 2 · **Spec** §7.5, §11.12

One click on **Revoke**, one confirm. Not a dialog with ceremony: narrowing access is never
obstructed.

**True at the end.** Every recipient session on that link is dead on its next request (P9). The
link stays visible on 11.12 in the revoked section, because what used to be reachable is part of
the record. It is not reversible and the confirm said so. A new link is a new URL.

---

## Part B — Where it protects you

### UC-8 · An agent tries to share something and cannot

**Actor** Agent · **Phase** 2 · **Spec** §7.9, §4.6.1

`claude-code@hosta` calls `share_create_link`. Its token does not carry `share:create`, which is
not granted by default. It gets `403 insufficient_scope` with a sentence it can pass to its human,
and a URL that takes Robert to the right place.

**True at the end.** No link was created. Robert decides, not the agent. A token that *does* hold
`share:create` renders its chip in a warning treatment on 11.18 forever, and the links it creates
are attributed to it by name on 11.12 — which is exactly the case Robert most needs to see.

### UC-9 · An agent goes wrong

**Actor** Agent, adversarially · **Phase** 4 · **Spec** §10.4, A3

A looping agent posts four hundred artifacts overnight, or trashes thirty, or creates links in a
burst, or appears from an IP it has never used.

**True at the end.** Every one of those is an audited event with a token ID and a source IP.
Thresholds fire an email within fifteen minutes. The trashed artifacts are all restorable for
thirty days. The overwritten ones all kept their previous versions. `sharectl panic` and its
dashboard equivalent kill every link and session at once.

**This is the adversary the product is shaped around.** Full agent autonomy is only acceptable
because every destructive act is reversible and every act is attributed.

### UC-10 · Robert deletes the wrong thing

**Actor** Owner · **Phase** 1 · **Spec** §5.11, §8.4, §11.15

He trashes an artifact, notices, and undoes it from the toast — or later, from 11.15.

**True at the end.** Versions came back. **Share links and grants did not**, and anyone holding a
link stays locked out until he makes a new one. That asymmetry is stated in the confirm before he
trashes, again in the restore confirm, and again on the artifact page while it sits in the trash.
It is the single most surprising behaviour in the product, so it is said three times.

### UC-11 · Robert loses a laptop

**Actor** Owner · **Phase** 1 · **Spec** §4.4, §11.19

From another device he opens 11.19, revokes that passkey, and signs out everywhere.

**True at the end.** Revoking the passkey revoked every session created with it, and the confirm
said how many. The laptop's cookie is worthless. No password existed to be found on it.

### UC-12 · Robert loses every passkey

**Actor** Owner · **Phase** 2 · **Spec** §4.5, §11.2, §11.3

He uses his recovery code on 11.2. He gets one thirty-minute session that can do exactly one
thing: register a new passkey. A fresh recovery code is issued and shown once.

**True at the end.** Using the code invalidated every other code, and he was told that before he
submitted, not after. The restricted session could not reach any other route. If he has also lost
the recovery code, the only way back is server-side, and that residual burden is the price of
deleting the entire password-reset attack class.

---

## Part C — More than one person

### UC-13 · A second person gets an account

**Actor** Owner, then User · **Phase** 3 · **Spec** §4.8, §6.2, §11.4, §11.22

Robert invites `sarah` from 11.22, choosing her handle at invite time. She accepts on 11.4,
registers a passkey, saves a recovery code, and lands on an empty space at
`share.c52.com/~sarah` with a first-run checklist that has no "invite someone" item.

**True at the end.** There is no public sign-up (N4). She can prove by test that she cannot see,
list, search, guess, or reach anything of Robert's. There are no roles and no permission matrix —
she is a person with a space (N3).

### UC-14 · Robert shares one artifact with Sarah

**Actor** Owner, then User · **Phase** 3 · **Spec** §7.7, §5.10, §11.14

He grants it from 11.12's People section. It appears on her 11.14 with his handle and a standing
per-row advisory: this belongs to someone else and disappears if they delete it. She takes
**Save a copy**.

**True at the end.** Her copy is private with no share links, regardless of what the original had.
It survives the original being purged. Robert sees the copy in his activity feed. Revoking the
grant takes effect on her next request. The artifact's state on Robert's screens is now `granted`
rather than `shared` — a different colour, a different word, and a different degree of exposure.

---

## Part D — Living with it

### UC-15 · A human posts something without an agent

**Actor** Owner or User · **Phase** 2 · **Spec** §11.17, §9.6

Robert drags a folder onto 11.17. The name is derived from the directory name and normalised
visibly as he watches. The browser hashes the files so already-held files are skipped. He commits.

**True at the end.** He lands on 11.7, not on the share dialog — posting and sharing are separate
decisions and joining them here would undo the shape of the whole product. A note beside the button
said so before he pressed it. `.env`, `*.pem`, `*.key` and `id_rsa*` were refused outright, with no
way to force them from a browser.

### UC-16 · Robert needs something from a month ago

**Actor** Owner · **Phase** 2 · **Spec** §8.7, §11.16

`⌘K`, a few characters, `⏎`.

**True at the end.** Search covered names, titles, descriptions and tags, and **never the contents
of any file** (N6, P5). Each result carried the same sharing-state component as everywhere else,
because a private result and a link-active result must be distinguishable without opening either.
There is no instance-wide search, including for root.

### UC-17 · An agent posts a bundle with no obvious entry point

**Actor** Agent, then Owner · **Phase** 1 · **Spec** §5.5, §6.6.2, R7

No `index.html`. The artifact root serves R7 — a plain file listing of that artifact and nothing
else. Robert sets an entry file from 11.8 without reposting.

**True at the end.** The listing is scoped to the one artifact being addressed. There is no listing
of a space, ever, for anyone. Setting the entry file took effect immediately, on the live version,
without a new version being created.

### UC-18 · Robert runs out of room

**Actor** Owner · **Phase** 3 · **Spec** §10.3, §11.25, §11.15, §11.24

He crosses 80%, then 95%, then 100%. Banners appear; emails arrive at most daily.

**True at the end.** At 100%, posting fails and reading, sharing and deleting all keep working —
the system never traps him. 11.25 tells him the three things that would free space and how much
each holds. The trash counts against his quota and the banner says so, because emptying it is the
fastest way back.

### UC-19 · The operator proves it can be restored

**Actor** Operator · **Phase** 1 and 4 · **Spec** §15.5, §14

A restore drill from an encrypted off-host backup, followed by `verify-integrity`.

**True at the end.** Zero missing files. The drill is automated and its outcome is visible on
11.28, with the last successful backup as an absolute time. A stale or failed backup is a red tile
and an email, because a backup nobody checks is not a backup.

---

## What no use case does

Worth stating, because their absence is the design:

- Nobody publishes anonymously. Every write carries a token or a session, and every token belongs
  to an identity. This is the thing the instance exists to not have.
- Nobody makes a permanent share link. Not a phase, not a flag, not a future consideration.
- Nobody runs code on the server. Share serves static artifacts; there is no runtime, no build
  step, no page database, and no API proxying.
- Nothing reads a file to be helpful. No generated title, summary, thumbnail, embedding, or
  classification, anywhere, for any reason.
- Nobody administers another person's space. Spaces are hard boundaries and root is not an
  exception.
