# Part 12 — All Product Copy

This part is the authority on wording. Where an earlier part sketches a string in passing and
this part gives a different one, **this part wins** — it is the finished text, and the earlier
sketch was shorthand. Screen numbers are from `inventory.md`.

Substitutions written as `{name}`, `{expiry}`, `{handle}` are filled at render time. Every
absolute time renders per §11.29.3: `7 Sep 2026, 18:04 UTC`, relative hint in parentheses.

---

## 12.1 Voice and tone

Share is a tool for keeping and handing out finished work, some of it about other people's
business. It should read the way a competent colleague talks: plainly, without decoration, and
without pretending anything is more or less serious than it is.

### The rules

**1. Say what happened, then what to do.** An error that only names a condition is half an
error.

> Good: "That name is already taken by an artifact in your trash. Restore it, rename it, or
> empty the trash."
> Bad: "Conflict. Name unavailable."

**2. No exclamation marks. Anywhere.** Not in success toasts, not in emails, not in the empty
states. There is nothing in this product worth an exclamation mark.

> Good: "Share link created."
> Bad: "Share link created!"

**3. Never apologise for a working system, never joke about a broken one.** No "Oops", no
"Something went wrong", no "Uh oh", no sad-face glyphs.

> Good: "The server did not respond. Retry, or check the instance status."
> Bad: "Oops! Something went wrong on our end."

**4. Be specific about consequence, especially about access.** Sharing copy names who gets in,
until when, and what protects it. Never "anyone can see this" without an end date attached.

> Good: "Anyone with the link can view this until 7 Sep 2026, 18:04 UTC (in 14 days). A password
> is required."
> Bad: "This artifact is shared."

**5. Absolute times govern; relative times hint.** Anything that controls access is written as
a full timestamp. "Expires soon" is never the whole sentence.

> Good: "Expires 7 Sep 2026, 18:04 UTC (in 2 days)."
> Bad: "Expires in 2 days."

**6. Do not soften a permanent thing.** If something cannot be undone, the copy says so in the
same breath as the verb.

> Good: "Revoking is immediate and cannot be undone. A new link is a new URL."
> Bad: "Are you sure you want to revoke this link?"

**7. Never claim knowledge the system does not have.** Share does not read files, so no copy may
imply it did. No "we noticed", no "based on your content", no generated summaries or titles.

> Good: "Search covers names, titles, descriptions, and tags."
> Bad: "We couldn't find anything matching that in your documents."

**8. Sentence case everywhere.** Headings, buttons, table headers, email subjects. Proper nouns
and the product name keep their capitals. Column headers in dense tables may be small caps
visually, but the string is sentence case.

**9. Buttons are verbs, and they name the specific act.** Never "OK", never "Submit", never
"Yes".

> Good: "Create link", "Move to trash", "Delete permanently", "Extend"
> Bad: "OK", "Confirm", "Proceed"

**10. Second person for the reader, no first-person plural for the system.** "You", "your
artifacts". The system is "Share" or it is nothing — not "we". The one place "us" appears is
the password panel's "including us", which is an honest technical statement about what is
stored, and it is deliberate.

**11. American spelling.** Authorize, recognize, canceled, color, license (noun and verb),
behavior. Applies to copy only; API field names and RFC terms are unchanged.

**12. Number and unit style.** Digits for all counts ("3 files", "1 link"). Sizes as `110 KB`,
`2.4 MB`, `18 GB`, one decimal place above 1 MB, none below. Percentages as `80%`. Durations
spelled out in prose ("14 days"), abbreviated in code and flags (`14d`).

**13. Length.** One sentence for a toast. Two for an error. Three for a destructive
confirmation, in the order: what happens, whether it can be undone, what it does not do.

**14. No progress-blocking cheerfulness.** Empty states describe the absence and offer at most
one action. They do not congratulate, encourage, or promise.

> Good: "Nothing in the trash. Deleted artifacts stay here for 30 days."
> Bad: "All clean! Your trash is empty."

---

## 12.2 Canonical terminology

### 12.2.1 Use this, never that

| Use | Never | Why |
| --- | --- | --- |
| **artifact** | file, site, page, project, upload, asset, doc | An artifact is the unit of ownership, addressing, sharing, versioning, and deletion. "File" means one blob inside one. |
| **file** | asset, resource | Only ever a single blob inside an artifact. |
| **bundle** | site, folder, app, deployment | A multi-file artifact. Share does not host sites. |
| **post** | publish, deploy, push live, upload to the web | "Publish" implies the internet; posting does not widen access at all. |
| **share link** | public link, published link, shareable URL, magic link | It is a capability, not a publication. |
| **private** | unlisted, hidden, secret, draft | Private means signed-in only. "Unlisted" implies public-but-obscure, which is exactly what a share link is and private is not. |
| **grant** / **shared with** | invite to artifact, collaborator, member, permission | Grants are per-artifact reads for one named user. |
| **recipient** | viewer account, guest user, external user | A recipient never has an account. |
| **trash** | archive, bin (UK), deleted items, recycle bin | "Archive" implies keeping; trash implies a clock, and there is one. |
| **passkey** | password, credential (in user-facing copy), 2FA, MFA | There is no password on an account. Ever. |
| **share-link password** | link password is fine; never "your password" | It protects one link, not an identity. |
| **token** / **API token** | key, API key, secret, credential | Matches `shr_` and the CLI. |
| **agent** | bot, integration, app, client | The thing holding a token. |
| **space** | workspace, team, org, account area | One person's namespace. There are no teams. |
| **version** | revision, snapshot, backup, history entry | |
| **entry file** | index, homepage, default document, root page | |
| **staleness** / **not opened in N days** | inactive, abandoned, unused, orphaned | Nothing is deleted for being stale, so no word implying doom. |
| **expires** | times out, dies, is revoked (unless it was) | Expiry and revocation are different events. |
| **revoke** | delete, remove, cancel (for links, tokens, grants) | |
| **sign in** / **sign out** | log in, login (verb), log out | `login` remains correct as a noun in `share login`. |
| **instance** | server, deployment, environment, cloud | |
| **operator** | admin, owner (when talking about the machine) | The owner owns artifacts; the operator runs the box. |

Two further bans: never write **"public"** as a state of an artifact — the states are private,
link, and link plus password. And never write **"secure"** or **"safe"** as a bare adjective
about anything the product does; say what protects it instead.

### 12.2.2 Tooltip definitions

Exactly one sentence each. These are the strings behind every `?` and every glossary hover in
the dashboard, and they are identical everywhere they appear.

| Term | Tooltip |
| --- | --- |
| **Artifact** | One finished thing you posted — a single file or a bundle of files that belong together — with its own name, URL, versions, and sharing. |
| **Bundle** | An artifact made of more than one file, such as an HTML page with its styles and images, served as a unit so relative links keep working. |
| **Name** | The artifact's address inside your space, like `postcal` or `q3/market-report`, chosen by you or your agent and stable until you rename it. |
| **Space** | Your own namespace, where every artifact you own lives; nothing outside it can write into it and nothing inside it is listed to anyone else. |
| **Version** | An immutable snapshot of an artifact's files, created every time the artifact is posted again, with earlier ones kept and restorable. |
| **Share link** | A URL at `/s/…` that lets anyone holding it view exactly one artifact until it expires, optionally behind a password. |
| **Grant** | Read access to one artifact for one named user on this instance, who reaches it signed in as themselves with no link to forward. |
| **Recipient** | Someone viewing an artifact through a share link, with no account, who can see that one artifact and nothing else. |
| **Token** | An agent's credential, starting `shr_`, with its own name, its own scopes, and its own revoke button. |
| **Passkey** | The credential you sign in with, held by your device or password manager instead of typed, which is why this account has no password. |
| **Trash** | Where deleted artifacts wait 30 days before they are removed for good, still counting against your storage the whole time. |
| **TTL** | An optional expiry on the artifact itself, after which it moves to the trash automatically and stays recoverable for another 30 days. |
| **Staleness** | Artifacts you have not opened in the last 90 days, listed so you can decide what to delete; nothing here is ever deleted for you. |

---

## 12.3 First-run checklist

Shown on 11.6 in place of the artifact table when the space is empty. Card heading and
intro, then the items in order. Item 4 renders for the root user only. Item 6 is present for
every user.

**Heading:** Set up Share
**Intro:** Five things, once. The first two get an agent posting to this instance; the rest
make sure you can still get in and still know what is reachable.

| # | Title | Description | CTA |
| --- | --- | --- | --- |
| 1 | Connect an agent | Point Claude Code, Cursor, Codex, or any MCP host at this instance with one configuration block and a token. | Create a token |
| 2 | Post your first artifact | Have your agent call `share_post`, or run `share post ./folder`. It stays private until you say otherwise. | See the setup page |
| 3 | Add a second passkey | One passkey is one device away from a recovery process. A second one on another device is what makes losing the first uneventful. | Add a passkey |
| 4 | Save your recovery code | Twenty-four characters, shown once, good for one sign-in if every passkey is gone. Put it where you keep other things you cannot regenerate. | Show my recovery code |
| 5 | Check what reaches your inbox | Share emails you every time something of yours becomes reachable without a sign-in, including when an agent does it. Confirm that is still on. | Review notifications |
| 6 | *(root only)* Invite someone | Share has no sign-up. People get accounts because you create them, and each gets their own space at `share.c52.com/~handle`. | Invite someone |

**Per-item states**

| State | String |
| --- | --- |
| Done | Done |
| Dismissed | Skipped · Undo |
| Dismiss control | Do this later |
| Item 2 while polling | Waiting for your first post. This updates on its own. |
| Card footer | You can leave this at any time — it disappears once every item is done or skipped. |

**Below the card**, the plain empty state:

- Heading: Nothing here yet
- Body: Artifacts your agents post appear here, newest first.
- Secondary action: Upload from your browser

---

## 12.4 In-app documentation

Rendered at `/~/help` from bundled Markdown (11.27). `{host}` is `share.c52.com`, `{handle}` is
the reader's own handle; nothing else is substituted and nothing is fetched.

---

### 12.4.1 Quickstart

Share is where your agents put finished work so you can find it later and hand it to people.
Two ways in: connect an agent, or upload from this browser.

**The agent path.** Share speaks MCP at `https://share.c52.com/mcp`. There is nothing to
install. Create a token on the API tokens screen, then paste this into your MCP host's
configuration:

```json
{
  "mcpServers": {
    "share": {
      "type": "http",
      "url": "https://share.c52.com/mcp",
      "headers": { "Authorization": "Bearer shr_YOUR_TOKEN" }
    }
  }
}
```

Restart the host. Your agent now has `share_post`, `share_list`, `share_get`, `share_versions`,
and the rest. Ask it for something finished — "make me a Q4 posting calendar as an HTML page and
post it to Share as `postcal`" — and it will come back with a URL:

```
https://share.c52.com/postcal
```

That URL is **private**. Open it in this browser, signed in, and it works. Open it in a private
window and it is a 404, indistinguishable from a name that never existed. Posting never widens
access; that is a separate, deliberate act.

Post it again next week and the URL does not change. You get version 2, and version 1 stays
where it is.

**The human path.** No agent, or something that arrived by email: use **Upload** in the top bar.
Drop a file or a whole folder — the folder's relative paths are preserved, so a page with a
`style.css` and an `img/` directory keeps working. Give it a name, which becomes its address, and
a title if you want one shown. Nothing is ever filled in from the contents of your files.

**Handing something to a person.** Open the artifact, go to **Sharing**, and create a share
link. You choose how long it lives — every link expires, and 14 days is the default — and
whether it needs a password. You get the URL and, if you asked for one, a generated password,
shown once. Send them separately if the contents deserve it.

**When you want it back.** Search from `⌘K` covers names, titles, descriptions, and tags. Deleted
artifacts sit in the trash for 30 days. Overwritten ones keep their old versions. Almost nothing
here is one keystroke from gone.

---

### 12.4.2 Posting artifacts

**What an artifact is.** One finished thing, at one address, with one history. It might be a
single PDF, or an HTML page with eleven supporting files. Either way it is one artifact: one
name, one URL, one set of versions, one sharing state, one entry in the trash if you delete it.
The unit is deliberate — it is what makes "send the client the report" a single act rather than
an attachment-management exercise.

**Naming.** The name is the address. `postcal` lives at `share.c52.com/postcal`. Slashes work,
so `q3/market-report` is a legal name and gives you a shallow hierarchy without folders being a
real thing. Names are lowercase (a submitted `PostCal` is lowercased for you), start with a
letter or digit, and may contain `.`, `_`, `-`, and `/`. Up to 200 characters and 8 segments.

If your agent does not supply a name, Share generates one like `civil-marmot-a4f2`. Those are
fine for scratch output. Anything you intend to return to should be named on purpose, because
the name is what you will search for.

**Entry points.** For a bundle, one file has to answer at the artifact root. Share picks in this
order: the `entryPath` you supplied, then `/index.html`, then the only HTML file if there is
exactly one, then the only file if there is exactly one. If none of those apply, the artifact
root shows a plain file listing instead, and you get a `no_entry_point` warning. You can set or
change the entry file at any time on the Files tab — it takes effect immediately, without
posting again.

**Multi-file bundles.** Relative links inside a bundle resolve exactly as they would on a normal
web server: `./style.css` from `/index.html` works, `img/chart.png` works, a directory with its
own `index.html` works. What does not exist is a fallback route — a missing `.json` returns 404
rather than your index page, because Share serves artifacts, not applications. If you include a
`404.html`, it is served for missing paths inside that artifact.

**Overwriting in place.** Post to a name that already exists and you get a new version of it, at
the same URL. Nothing about the artifact resets: title, description, tags, TTL, pinned state,
share links, and grants all survive. Only the files change. The old version stays complete and
restorable, and unchanged files are not re-uploaded or re-stored — identical bytes are kept once
instance-wide, so twenty versions of a calendar that changes a few lines a week cost almost
nothing.

Two things overwriting does affect. First, anyone holding a live share link sees the new version
immediately — see "What happens when an agent overwrites something you shared". Second, the
artifact's `updatedAt` moves, so it returns to the top of your list, which is usually what you
want and occasionally a surprise.

---

### 12.4.3 Privacy and sharing

This is the page to read if you read only one.

**Three levels, and nothing between them.**

| Level | Who gets in | What they need |
| --- | --- | --- |
| **Private** | You, and any user you granted | A passkey and a signed-in session |
| **Link** | Anyone holding the link | The URL, which contains 128 bits of randomness |
| **Link + password** | Anyone holding the link and the password | Both, given separately if you have any sense |

Private is the default and where most things stay. An artifact with no share link and no grant
returns exactly the same 404 to a stranger as a name that never existed — same body, same
headers, no timing tell. There is no fourth level, no "public" flag, and no way for an artifact
to be found by a search engine: every response carries `noindex, nofollow` and `robots.txt`
denies everything, with no per-artifact override.

There is also no toggle. A share link is an object you create, label, list, and revoke, and
creating one is a multi-step flow with a confirmation step. That friction is the design. A
switch you can flip in passing is a switch you can flip by accident.

**Why every link expires.** There is no permanent share link, no setting to make one, and no way
to ask the API for one. Links do not leak by being guessed — at 128 bits, guessing is not a
thing that happens. They leak by being forwarded, saved into a folder, pasted into a ticket,
screenshotted, and archived. A link that stopped working in February is a non-event when the
archive holding it surfaces three years later. The default is 14 days, the ceiling is 180, and
extending is one click from the email you get 24 hours before it dies.

**What a recipient can learn.** Deliberately, almost nothing:

- The URL contains no owner handle, no artifact name, and no artifact ID.
- The password gate names nothing at all — not the artifact, not who sent it, not the file type,
  not how long the link has left.
- Assets load under `/s/{token}/…`, so someone viewing a bundle never sees its real path or the
  name of your space.
- Expired, revoked, burned through its view limit, and trashed all produce the same page: "This
  link is no longer active." A recipient cannot tell which happened.
- What you can see about them is a count and a date. Views are recorded as a salted daily hash
  that cannot be recomputed the next day, so "4 views on Tuesday via Fairfield listing team" is
  the finest resolution that exists, for you and for anyone with database access.

**Why your agents cannot create share links.** An agent token holds `artifacts:read` and
`artifacts:write` by default, and not `share:create`. It can post, overwrite, tag, and trash its
own owner's work. It cannot make any of it reachable from the internet. Ask an agent to "share
this with my client" and it fails with `insufficient_scope`, naming the scope, and the right
answer is for it to hand you a link to the dashboard so you can decide.

This is the single most important line in the product. Putting something in front of a person
outside the system is a human decision, and an agent that can post but cannot publish has a
worst case of a messy space rather than a client's numbers on the open internet.

You can grant `share:create` to a token deliberately, on the tokens screen, with a warning
attached, and the grant is audited. If you do, that token's link creations show its name as the
creator everywhere they appear, and you are emailed the first time it ever creates one.

**Your own sessions are not scoped.** The `share:create` scope constrains tokens, not people.
Signed in, you can always share anything of your own.

---

### 12.4.4 Share links and grants

Two ways to let someone see one artifact. They are not variations on a theme.

**A share link** is a bearer capability. Anyone holding the URL is in, until it expires. Use it
for people who do not have accounts here: clients, counterparties, someone's phone. Its
strengths and its weakness are the same fact — nothing about the recipient is checked, so
nothing about the recipient needs arranging.

**A grant** gives one named user on this instance read access to one artifact. They reach it at
its canonical URL signed in as themselves. There is no bearer token to forward, no password to
mishandle, and no expiry to manage. They can view, download, and save a copy. They cannot edit,
rename, delete, share it onward, or see anything else in your space. Use it for anyone who has
an account here.

**Passwords on links.** Choose *generate a password for me* unless you have a reason not to. The
generated form is `{adjective}-{noun}-{digits}` — `civil-marmot-71` — designed to survive being
read aloud on a phone call. It is shown once, at creation, and no endpoint will ever return it
again; the server keeps only an argon2id hash. If you lose it, create a new link. Your own
passwords need 8 characters and nothing else: no composition rules, no strength meter, because
a meter would imply rules the server does not enforce.

Attempts against a link's password are limited to 10 per IP per hour and 50 per link per hour,
and you are emailed the first time a link's ceiling is hit.

**Revoking.** Immediate and not reversible. Every recipient session on that link dies on the
next request, the cache is purged in the same call, and anyone holding the URL gets "This link
is no longer active." There is no un-revoke — a new link is a new URL. Revoking a grant takes
effect on that user's next request.

For the morning something looks wrong, the security overview has **Revoke all share links**,
which is the dashboard equivalent of `sharectl panic`: every live link on your account, gone,
with a count shown before you confirm.

**Extending.** Extension adds to the current expiry rather than restarting from now, so
extending can never accidentally shorten a link. The dialog shows you the resulting absolute
date before you confirm.

**Reposting an artifact that has a live link.** The link keeps working and now shows the new
version. This is deliberate and it has a sharp edge — see the dedicated page.

**Copying the URL later.** Share stores a hash of each link token and the first few characters,
never the token itself. So the **Copy** control works for a link created in this browser session
and cannot work for one created last week: the full URL is genuinely unrecoverable, including by
the operator. The card says so and offers to create a new link instead of showing you a dead
button.

---

### 12.4.5 Versions, trash, and getting things back

Agents have full control over their own space. These are the two mechanisms that make that
acceptable.

**Versions.** Every post to an existing name creates a new version, numbered from 1. The
previous ones stay complete and viewable. On the Versions tab you get, per version: when, by
which agent or person, how many files, total size, the version note if one was supplied, and a
count of what changed — added, modified, removed.

That count compares *manifests*, not contents. Share does not read your files, so there is no
line-level diff anywhere in this product, and there never will be. "3 files, 1 modified" is the
finest answer available.

**Restoring a version creates a new one.** Restoring v1 while v3 is live gives you v4 with v1's
files. History stays append-only, so "what was live in March" always has an answer. A restore
carries the files and the entry file. It leaves everything else exactly as it is now: name,
title, description, tags, TTL, pinned state, share links, and grants. Rolling back content must
never quietly change who can see something.

**Retention.** By default Share keeps the last 20 versions and anything from the last 365 days,
never fewer than 3, and never prunes a pinned version or the live one. Pin any version you want
kept regardless. Pruning happens on the nightly job, so lowering the setting shows you what it
would remove and then removes it overnight, not instantly.

**Trash.** Deleting an artifact moves it to the trash for 30 days. While it is there it returns
404 at its URL to everyone including anyone holding a link, it is absent from listings and
search, it still holds its name, and it still counts against your storage. Restore brings it
back with every version intact.

**One asymmetry to know.** Trashing revokes every share link and grant on the artifact
immediately. Restoring does **not** bring them back. Undoing a deletion should not silently
re-open access, so anyone who had a link stays locked out until you make a new one. Every
confirmation dialog that trashes something says this before you press the button.

**Permanent deletion** skips the trash and cannot be undone: every version goes, and every file
nothing else references is removed from disk on the next collection pass. It needs the
`artifacts:delete` scope over the API, which agent tokens do not get by default. That is why the
worst a runaway agent can do is fill your trash.

**Names and the trash.** A trashed artifact keeps its name, so posting to that name returns
`name_taken` until you restore it, rename it, or empty the trash. If the name has since been
taken by something new, restoring asks you to rename first.

---

### 12.4.6 Search

`⌘K` from anywhere, `/` when nothing is focused, or the search field in the top bar. Results
show the same sharing-state indicator as every other list, because a private artifact and one
with a live link are different things and you should not have to open either to tell.

**What search covers:** names, titles, descriptions, and tags. Matching is trigram-based, so
partial words and typos work — `postcl` finds `postcal`, `calend` finds "Q4 posting calendar".
Ranking goes exact name, then name prefix, then similarity on name, then title, then
description. Tags match exactly and boost.

**Filters**, in the palette and in the URL of the full results page: `q`, `tag` (repeatable, all
must match), `kind` (`bundle`, `page`, `document`, `image`, `video`, `file`), `token` (which
agent posted it), `hasLink`, `createdAfter` / `createdBefore`, `updatedAfter` / `updatedBefore`,
and `sort` (updated, created, name, size, views). Filter state lives in the query string, so a
filtered view is a URL you can bookmark or send to yourself.

**What search cannot do: find a phrase inside your files.** Not a sentence in an HTML report,
not a number in a PDF, not a word spoken in a video. This is not a missing feature. Share never
reads the contents of anything you post — not to index, not to summarize, not to generate a
title, not to make a thumbnail. That guarantee is the reason this instance exists rather than a
commercial one, and full-text search is what it costs.

**So name and tag things.** The practical consequences:

- Give artifacts real names. `q3/market-report` is findable; `civil-marmot-a4f2` is not.
- Set a title when the name is terse. Titles are searched.
- Use the description field for the sentence you would have searched for. It is searched too,
  and nothing else in the product reads it.
- Tag by project, client, and source. `--tag fairfield --tag listing` costs one flag and turns a
  guess into a filter.
- Tell your agents to do all of the above. The `share_post` tool description says exactly this,
  for exactly this reason.

Search is scoped to your own artifacts plus anything granted to you. There is no instance-wide
search, including for the root user, because a search that crosses spaces is a listing of
someone else's work.

---

### 12.4.7 Connecting agents

Share speaks MCP over streamable HTTP at `https://share.c52.com/mcp`, authenticated with the
same `shr_` token the HTTP API and the CLI use. There is nothing to install for the MCP path.

Create a token first: **API tokens → New token**. Name it `agent@machine` — `grokbot@macmini`,
`claude-code@laptop` — because that name appears on every artifact it posts and in every audit
row, and "which of these three is the Mac Mini" needs an answer before you revoke one.

**Claude Code** — `~/.claude/settings.json`, or `.mcp.json` in a project:

```json
{
  "mcpServers": {
    "share": {
      "type": "http",
      "url": "https://share.c52.com/mcp",
      "headers": { "Authorization": "Bearer shr_YOUR_TOKEN" }
    }
  }
}
```

**Cursor** — `~/.cursor/mcp.json`, or `.cursor/mcp.json` in a project:

```json
{
  "mcpServers": {
    "share": {
      "url": "https://share.c52.com/mcp",
      "headers": { "Authorization": "Bearer shr_YOUR_TOKEN" }
    }
  }
}
```

**Codex** — `~/.codex/config.toml`:

```toml
[mcp_servers.share]
url = "https://share.c52.com/mcp"

[mcp_servers.share.headers]
Authorization = "Bearer shr_YOUR_TOKEN"
```

**Any other MCP host** — the endpoint descriptor is at
`https://share.c52.com/.well-known/mcp`. If the host speaks only stdio, install the CLI and run
`share mcp`, which is a thin proxy to the same endpoint rather than a second implementation:

```json
{
  "mcpServers": {
    "share": { "command": "share", "args": ["mcp"] }
  }
}
```

**Letting an agent get its own token.** An agent with shell access can run the device-code flow
instead of being handed a secret:

```
$ share login
Open https://share.c52.com/~/authorize and enter QRTZ-8H4M
Waiting for approval…
Signed in. Token saved to ~/.share/credentials (mode 0600).
Scopes: artifacts:read artifacts:write  (cannot create share links)
```

You approve it in the dashboard, signed in with your passkey, seeing the agent's declared name,
the source address, and the scopes it will get, before anything is issued. The token never
appears on that screen — it goes to the waiting process.

**What an agent token can do:** list, read, and download your artifacts; post new ones;
overwrite existing ones; rename, tag, describe, set a TTL; move to the trash and restore;
restore versions; read its own identity and quota.

**What it cannot do:** create, extend, or revoke a share link. Grant an artifact to another
user. Permanently delete anything (that is `artifacts:delete`, separate on purpose). Touch any
space but yours — there is no parameter anywhere in the API that names a different owner. Create
other tokens, invite users, or change your settings without `account:admin`.

Every token is individually revocable, and revoking takes effect within seconds. Its artifacts
and versions stay, still attributed to it.

---

### 12.4.8 CLI reference

Install with `curl -fsSL https://share.c52.com/install.sh | sh`. It writes
`~/.share/config.json` pointing at this instance and offers to run `share login`. It never
writes a credential you did not give it interactively.

| Command | Does |
| --- | --- |
| `share post <path>` | Post a file or directory, creating or overwriting an artifact |
| `share ls` | List your artifacts |
| `share get <name>` | Show one artifact in detail, including live links |
| `share open <name>` | Print the artifact's URL, or open it in a browser |
| `share cat <name> <path>` | Print one file from an artifact to stdout |
| `share pull <name> [dir]` | Download an artifact's files |
| `share rm <name> [--purge]` | Move to trash, or delete permanently |
| `share restore <name>` | Bring an artifact back from the trash |
| `share versions <name>` | List versions with change counts |
| `share rollback <name> <seq>` | Restore a version as a new version |
| `share link <name>` | Create a share link |
| `share links <name>` | List an artifact's links |
| `share unlink <linkId>` | Revoke a link, immediately and permanently |
| `share grant <name> <handle>` | Give another user on this instance read access |
| `share tag <name> <tag…>` | Add or remove tags |
| `share search <query>` | Search names, titles, descriptions, and tags |
| `share trash` | List what is in the trash and when it goes |
| `share login` | Device-code flow; writes credentials at mode 0600 |
| `share whoami` | Handle, scopes, quota used and remaining, artifact count |
| `share logout` | Remove stored credentials |
| `share doctor` | Check connectivity, credentials, and clock skew |
| `share mcp` | Run a local stdio MCP proxy to the remote endpoint |

**Common flags on `post`:** `--name`, `--title`, `--description`, `--tag` (repeatable),
`--entry`, `--ttl`, `--note`, `--include` / `--exclude` (globs, repeatable), `--dry-run`,
`--bundle` / `--no-bundle`, `--concurrency`, `--link`, `--link-ttl`, `--password`, `--label`.

**Global flags:** `--host`, `--token`, `--json`, `--quiet`, `--no-color`, `--yes`, `--timeout`.

```
$ share post ./calendar --name postcal --title "Q4 posting calendar" --tag social
Posting ./calendar  (3 files, 110 KB)
  1 new, 2 unchanged
  ████████████████████ 1/1 uploaded
Posted postcal v2 — private

https://share.c52.com/postcal
```

The URL is always the last line, so `$(share post ./x | tail -1)` works. `--json` emits the
commit response and nothing else. Warnings go to stderr with a `warning:` prefix. Errors print
`error: <code>: <message>` and exit with a code from the table in the agent surface — 3 for no
credentials, 5 for insufficient scope, 8 for quota, 9 for rate limits, 11 for a local refusal.

**Files the CLI will not send.** `.git/`, `node_modules/`, `__pycache__/`, `.venv/`, build
caches, `.DS_Store` and friends are skipped silently. `.env`, `*.pem`, `*.key`, `id_rsa*`,
`*.p12`, `credentials`, and `.netrc` are refused loudly, by name, and need `--force-secrets` to
proceed. The server rejects dotfiles anyway; the point of the client rule is to fail in your own
terminal before anything leaves the machine.

**From CI.** Put the token in the runner's secret store as `SHARE_TOKEN` — never a credentials
file. Use `--yes`, since a confirmation prompt in a non-TTY is an error rather than a silent
assumption. The documented pattern is:

```
share post ./out --name preview-$BRANCH --ttl 30d
```

which gives every branch a stable private URL that cleans itself up. Do not use `--link` from
CI: a pipeline that can create share links is a pipeline whose compromise creates share links.

---

### 12.4.9 Passkeys and recovery

**How sign-in works.** Open `share.c52.com`, press **Sign in**, approve with Touch ID, Windows
Hello, your phone, a security key, or 1Password. There is no email field, because the browser
offers whichever passkey matches this site. One tap, done.

**Why there is no password.** Not as a hardening measure — as a subtraction. A password brings a
reset flow with it, and a reset flow is a path that bypasses the password entirely. That is
where real account takeovers happen. No password means no reset email, no security questions, no
credential stuffing, and nothing in the database whose disclosure would let anyone in: a stolen
copy of this instance's data contains hashes and public keys and no usable credential.

Share-link passwords are a different thing — a shared secret protecting one link, not an
identity — and they are not stored or handled like one either.

**Three layers of recovery**, in the order you should rely on them.

*Layer 1 — a second passkey.* This is the one that handles almost every real case, which is why
the setup checklist pushes it. A passkey in a synced password manager plus one platform passkey
on a second machine means losing a laptop is an inconvenience. With a single passkey you are one
lost device from Layer 2.

*Layer 2 — your recovery code.* Twenty-four characters, Crockford base32, generated when your
account was created and regenerable any time from the security screen. It is shown exactly once
and stored only as an argon2id hash. Using it gives you a 30-minute session that can do exactly
two things: list your passkeys and register a new one. Using it also invalidates every other
code, issues you a fresh one, emails you, and writes an audit record. That notification cannot
be turned off.

*Layer 3 — the server.* This instance is a machine you control, which is the one thing no hosted
service can offer. With SSH access:

```
sharectl grant-session --email you@c52.com --minutes 30
```

prints a one-time URL that establishes a session on first use, audited as a system action. It is
the true backstop, and it means you can never be permanently locked out of your own files while
you can still reach the box.

**What deliberately does not exist:** recovery by email link. Adding it would reintroduce exactly
the bypass that removing passwords eliminated.

**Two things you will be emailed about and cannot mute:** a recovery code being used, and a
passkey signature counter going backwards. The second one means an authenticator reported a
lower use count than Share last saw, which can indicate a cloned credential. The sign-in is
refused, nothing is revoked automatically, and you should sign in with a different passkey and
revoke the suspect one from the security screen.

---

### 12.4.10 Users and invites

Share has no sign-up page. Accounts exist because the root user created them, and there is no
way to request one.

**Inviting.** Users and invites, root only: **Invite someone**, then an email address and a
handle. The handle is claimed at that moment, so two pending invites cannot collide, and it
determines their space: `sarah` gets `share.c52.com/~sarah`. Invites live 7 days. Up to 10 a day.

The invitee opens the emailed link, registers a passkey, saves a recovery code, and lands in
their own empty space. No password is created because none exists.

**What another user is.** A person with their own space and nothing else. There are no roles, no
permission matrix, no shared folders, and no workspace. Specifically, a second user:

- has their own artifacts, at `/~handle/name`, with their own quota, tokens, versions, and trash;
- cannot list, read, or write anything in your space, and neither can you in theirs;
- sees your artifact only if you grant it, one artifact at a time;
- can save a copy of anything you granted them, which costs no storage because identical bytes
  are stored once, and which is the right move for anything they need to survive your deleting
  it.

Search never crosses spaces, for anyone, including root.

**Disabling someone.** Revokes their sessions and every token they hold, immediately. Their
artifacts remain, and any live share link on their artifacts keeps serving until it expires —
so the confirmation offers **Revoke their share links too** as a checkbox. Disabling is
reversible by re-enabling.

There is no delete-a-user button in the dashboard. Removing a user and their artifacts for good
is `sharectl delete-user`, on the box, on purpose.

---

### 12.4.11 Storage, quotas, and what counts

The default quota is 500 GB per user, with a 10 GB ceiling per artifact version, 5 GB per file,
and 5,000 files per version. These are generous because video is in scope and bundles are the
main event; the binding constraint should be the disk the operator bought, not a number in a
config file. The operator can change every one of them.

**What counts against your quota:** every file referenced by every version of every artifact you
own, including artifacts in your trash, including versions you no longer look at, including
copies you saved of things other people granted you.

**What does not:** anything in someone else's space, even if you granted it to them; the same
file counted twice because it appears at two paths, or in twenty versions, or in two artifacts —
identical bytes are stored once and charged once per user.

**Why your number will not match a naive sum.** Files are deduplicated instance-wide: if two
users hold the same 40 MB video, one copy is on disk and each of them is charged for it. Your
quota figure is what your artifacts reference, not what is uniquely yours on disk, and it is the
honest number for "what would I be using if nobody else were here".

**Warnings and what happens at the ceiling.** You are emailed at 80% and again at 95%, at most
once a day. At 100%, posting fails with `quota_exceeded` — which is returned at declare time,
before any bytes move, with your current, projected, and limit figures so an agent can report
something actionable. Reading, downloading, sharing, and **deleting** keep working. Someone over
quota must always be able to dig out.

**Getting space back**, in order of how much it usually returns:

1. **Empty the trash.** It holds full artifacts and full versions and is charged in full. The
   trash screen shows its own total, and this is the fastest route back under a ceiling.
2. **Review what you have not opened.** The staleness screen lists artifacts with no view in 90
   days, largest first, excluding pinned ones and anything with a live link or grant. Nothing is
   ever deleted for you here.
3. **Tighten version retention.** Lowering "keep last" from 20 shows you what it would prune
   before you save; the prune itself happens on the nightly job.

If the number ever looks wrong, `sharectl recompute-quota` recounts from the manifests. A drifted
counter is an operator fix, not something you should work around.

---

### 12.4.12 Why search cannot read your files

*Linked from the search palette's no-results state, the artifact list, and the FAQ.*

Every commercial service that does this well reads what you upload. It extracts text from your
PDFs, indexes sentences from your HTML, embeds the result, and keeps that index for as long as
the account exists. That is how "find the deck where I mentioned the Fairfield numbers" works.

Share does not do it, and the guarantee is stronger than a promise not to look. Artifact contents
are never read for indexing, summarizing, embedding, titling, classification, thumbnail
generation, or format probing. There is no pipeline that opens your files, so there is no index
to leak, no extraction to misconfigure, and no cache of your text sitting beside the bytes. A
video is not probed for its dimensions. A PDF is not opened to guess a title. An artifact with no
title shows its name, because the alternative is a guess derived from reading.

This costs you exactly one thing: you cannot search for a phrase that only exists inside a file.

**What to do instead.** Put the words you would have searched for into the fields that are
searched — name, title, description, tags — at the moment you post, when you know them.

- Name things deliberately: `q3/market-report`, not the generated `civil-marmot-a4f2`.
- Title anything whose name is terse.
- Use the description as the one sentence you would have typed into search later.
- Tag by project and by client. Tags match exactly and boost ranking.
- Tell your agents. The `share_post` tool description instructs them to supply a title and tags
  on every post, and this is why.

Search is forgiving about the rest: matching is trigram-based, so `postcl` finds `postcal` and
partial words work.

---

### 12.4.13 Why every share link expires

*Linked from the create-link dialog, settings, and every expiry email.*

There is no permanent share link in Share. No setting enables one, the API rejects an unbounded
TTL, and the ceiling is 180 days.

The reason is how links actually get out. Not by being guessed — a share token carries 128 bits
of randomness, base58-encoded, and guessing one is not a threat anyone models seriously. They
get out by being forwarded to a colleague, saved into a shared folder, pasted into a ticket,
quoted in a thread, screenshotted, and swept into somebody's archive. Every one of those is
normal behavior by a person you deliberately gave the link to, and none of it is something you
will hear about.

An expiry turns all of that into a non-event. A link that stopped working in February is inert
when the archive holding it surfaces in 2029.

**How this plays out day to day.** The default is 14 days, changeable in settings. Presets run
from 30 minutes to 180 days. You get an email 24 hours before a link expires with a one-click
extend, and links inside 48 hours of expiry show in amber on your dashboard with **Extend** on
the row. Extending adds to the current expiry rather than restarting from now, so you can never
shorten a link by extending it.

If something genuinely needs to be readable indefinitely by a named person, that is a grant, not
a link: a grant has no expiry and no bearer token to forward, because the person signs in as
themselves.

---

### 12.4.14 What happens when an agent overwrites something you shared

*Linked from the create-link dialog, the artifact screen, and the FAQ.*

A share link points at the artifact, not at a version and not at a name. That has three
consequences, two good and one you need to hold in your head.

**Renaming does not break links.** Reorganize your space freely; a client's URL keeps working.

**Reposting does not break links either.** The client keeps seeing the current report rather than
a snapshot from the day you sent it. For a weekly calendar or a rolling dashboard, this is the
whole point.

**And that means a repost is immediately visible to everyone holding a live link.** If an agent
overwrites `postcal` at 3am with a draft, a debug build, or a version containing something that
was not meant to leave the building, anyone with a live link sees it on their next request.
There is no review step, no staging, and no approval — an agent with `artifacts:write` can
change what a live link shows without being able to create one.

**What Share does about it.** The artifact screen always shows live links prominently, at the
top of the right rail and above the fold on a phone, so you can see who is currently watching
before you ask for a repost. The create-link dialog states this before you create anything, and
when the artifact was last posted by an agent, it names that agent: *"Anyone with this link will
see the current version, including any future updates by grokbot@macmini."* Every overwrite is
in the artifact's activity feed with its actor and timestamp.

**What to do about it.** If the thing you sent should be frozen, take the snapshot: use **Copy to
my space** to make a second artifact from the current version, and share that copy instead. It
costs no storage, no agent posts to it, and it cannot change under your recipient. Otherwise,
revoke the link (immediate) and make a new one when the content is right — and remember that
revoking is not reversible, so the recipient will need the new URL.

---

## 12.5 UI microcopy

Every string in the dashboard, by screen. Strings marked *(dynamic)* interpolate values named in
braces. Where a screen reuses a global pattern (§12.5.29), the pattern's string is not repeated.

### 12.5.1 — Sign in (11.1)

| Element | String |
| --- | --- |
| Wordmark | Share |
| Host line | share.c52.com |
| Intro | Sign in with a passkey. |
| Primary button | Sign in |
| Button, in progress | Waiting for your passkey… |
| Recovery link | Use a recovery code |
| Error — `invalid_credential` | That passkey is not registered here. Try another, or use a recovery code. |
| Error — `webauthn_verification_failed` | That sign-in could not be verified. Try again, or use a recovery code. |
| Error — `credential_counter_regressed` | This passkey reported an unexpected use count, which can mean it has been copied. Sign-in was refused and the account owner has been emailed. Sign in with a different passkey and revoke this one from your security settings. |
| Error — rate limited *(dynamic)* | Too many attempts. Try again in {minutes} minutes. |
| No credential on this device | This device has no passkey for share.c52.com. Sign in on a device that does and add one there, or use a recovery code. |

### 12.5.2 — Sign in with a recovery code (11.2)

| Element | String |
| --- | --- |
| Heading | Sign in with a recovery code |
| Intro | Use this if every passkey is gone. You will get a 30-minute session that can do one thing: register a new passkey. |
| Field — email | Email address |
| Field — code | Recovery code |
| Code helper | 24 characters. Spaces and hyphens are ignored. |
| Advisory (before submit) | Using this code invalidates every other recovery code and issues you a new one, shown once. You will be emailed that it was used. |
| Primary button | Continue |
| Back link | Back to sign in |
| Error — invalid | That email and code do not match a recovery code on this instance. |
| Error — rate limited *(dynamic)* | Too many attempts. Try again in {minutes} minutes. |
| Restricted-session strip *(dynamic)* | Recovery session. Register a passkey to continue. This session ends at {expiry}. |

### 12.5.3 — Add a passkey (11.3)

| Element | String |
| --- | --- |
| Heading, additive | Add a passkey |
| Heading, forced | Register a passkey |
| Intro, additive | A second passkey on another device is what makes losing the first uneventful. |
| Intro, forced | Register a passkey to finish signing in. Nothing else is available until you do. |
| Primary button | Register a passkey |
| Field — name | Name this passkey |
| Name helper | Defaults to your authenticator's name. Change it to something you will recognize when you have three. |
| Existing list heading | Already registered |
| Error — `InvalidStateError` *(dynamic)* | This authenticator is already registered as "{name}". Use a different one. |
| Recovery code heading | Your new recovery code |
| Recovery code body | Shown once, right now. Store it where you keep things you cannot regenerate. Every earlier code is now invalid. |
| Recovery checkbox | I have saved this code |
| Second-key nudge heading | Add a second passkey |
| Second-key nudge body | You have one passkey. If you lose it, the only ways back are your recovery code or access to the server. |
| Second-key nudge actions | Add another · Do this later |
| Success toast | Passkey registered. |

### 12.5.4 — Invite acceptance (11.4)

| Element | String |
| --- | --- |
| Heading *(dynamic)* | {inviterName} invited you to Share |
| Body *(dynamic)* | You are claiming the handle **{handle}**. Your space will be share.c52.com/~{handle}. |
| Field — display name | Display name (optional) |
| Primary button | Register a passkey and continue |
| Explainer | Share has no password. You will sign in with a passkey and get a recovery code to store. |
| Signed-in-as-someone-else heading | You are signed in as {handle} |
| Signed-in-as-someone-else body | This invite is for a different account. Sign out to accept it. |
| Signed-in-as-someone-else action | Sign out and continue |
| Expired heading | This invite has expired |
| Expired body | Invites are good for 7 days. Ask whoever invited you to send a new one. |
| Not found heading | This invite is not valid |
| Not found body | It may have been used already or withdrawn. Ask whoever invited you to send a new one. |
| Generic failure | That did not complete. Contact whoever invited you. |

### 12.5.5 — Home, artifact list (11.5)

| Element | String |
| --- | --- |
| Page title | Artifacts |
| Search placeholder | Search artifacts |
| Upload button | Upload |
| Column headers | Name · Sharing · Updated · Size · Version |
| Filter labels | All · Kind · Tag · Agent · Shared · Sort |
| Sort options | Recently updated · Recently created · Name · Largest · Most viewed |
| Sharing filter options | Any · Link active · Private only |
| Posted-by, user | you |
| Pagination footer *(dynamic)* | {shown} of {total} |
| Load more | Load more |
| Empty for filters | No artifacts match these filters. |
| Empty for filters action | Clear filters |
| Row menu | Open · Copy URL · Share… · Versions · Rename · Move to trash |
| Copy URL toast | URL copied. This is the signed-in address — it will not work for anyone else. |
| Stale nudge *(dynamic)* | {count} artifacts you have not opened in {days} days · {bytes}. Review |
| Banner — links expiring *(dynamic)* | {count} share links expire within 48 hours. — Review |
| Banner — artifact TTL *(dynamic)* | {name} expires {expiry} ({relative}). — Keep · Dismiss |
| Banner — quota 80% *(dynamic)* | You are using {percent} of your {quota} storage. — Manage storage |
| Banner — over quota | You are out of storage. Posting is refused until you free space; reading, sharing, and deleting still work. — Empty trash · Manage storage |
| Trash confirm heading *(dynamic)* | Move {name} to the trash? |
| Trash confirm body *(dynamic)* | It stops resolving at its URL immediately and is deleted for good on {purgeDate} ({relative}). You can restore it until then. Its share links and grants are revoked now and are not restored when you restore it. |
| Trash confirm button | Move to trash |
| Trash toast *(dynamic)* | {name} moved to the trash. — Undo |
| Bulk trash confirm *(dynamic)* | Move {count} artifacts to the trash? Their share links and grants are revoked now and are not restored on restore. |

### 12.5.6 — Empty state and checklist (11.6)

Full copy in §12.3.

### 12.5.7 — Artifact detail (11.7)

| Element | String |
| --- | --- |
| Back link | Artifacts |
| Tabs | Overview · Files · Versions · Sharing |
| Meta line *(dynamic)* | {kind} · v{seq} · {fileCount} files · {bytes} |
| Copy URL button | Copy URL |
| Copy URL toast | URL copied. This is the signed-in address — it will not work for anyone else. |
| Open button | Open |
| Rail — sharing heading | Sharing |
| Rail — sharing action | Manage sharing |
| Rail — sharing, private detail | Only you, and anyone you grant. |
| Rail — sharing, link detail *(dynamic)* | 1 link · expires {expiry} ({relative}) · password set |
| Rail — posted by heading | Posted by |
| Rail — posted by link | View all from this agent |
| Rail — details heading | Details |
| Rail — details labels | Created · Updated · Tags · TTL · Views |
| Rail — no TTL | None |
| Rail — views *(dynamic)* | {count} · last {relative} |
| Rail — edit action | Edit details |
| Activity heading | Activity |
| Activity — posted *(dynamic)* | Posted v{seq} by {actor} |
| Activity — overwritten *(dynamic)* | Overwritten → v{seq} by {actor} |
| Activity — renamed *(dynamic)* | Renamed from {old} by {actor} |
| Activity — metadata *(dynamic)* | Details changed by {actor} |
| Activity — link created *(dynamic)* | Link created, {ttl}, {password}, by {actor} |
| Activity — link revoked *(dynamic)* | Link revoked by {actor} |
| Activity — link expired | Link expired |
| Activity — password changed *(dynamic)* | Link password changed by {actor} |
| Activity — granted *(dynamic)* | Shared with {handle} by {actor} |
| Activity — grant revoked *(dynamic)* | Access removed for {handle} by {actor} |
| Activity — views via link *(dynamic)* | {count} views via "{label}" |
| Activity — views signed in *(dynamic)* | {count} views, signed in |
| Activity — copied *(dynamic)* | Copied to {handle}'s space |
| Activity — trashed / restored *(dynamic)* | Moved to the trash by {actor} · Restored by {actor} |
| Activity — version restored *(dynamic)* | v{old} restored as v{new} by {actor} |
| Activity — TTL expired | Expired and moved to the trash |
| Activity footnote | View counts are daily totals. Share records no identity, address, or location for a view. |
| Activity pagination | Load older |
| Trashed bar *(dynamic)* | In the trash. Deleted for good on {purgeDate} ({relative}). — Restore · Delete permanently |
| Trashed sharing card | Private. Trashing revoked this artifact's links and grants; restoring will not bring them back. |
| TTL strip *(dynamic)* | This artifact expires {expiry} ({relative}) and moves to the trash. — Keep this artifact · Change TTL |
| Grantee advisory *(dynamic)* | This belongs to @{handle}. They can change or delete it at any time, and your access goes with it. |
| Grantee primary action | Save a copy |
| No entry point note | No entry file, so this artifact's root shows a file listing. — Set an entry file |
| Menu | Rename · Edit details · Set TTL · Pin · Copy to my space · Download all · Move to trash |
| Rename dialog heading | Rename this artifact |
| Rename dialog body *(dynamic)* | The current URL, share.c52.com/{name}, stops working immediately and is not redirected. Existing share links keep working — they point at the artifact, not the name. |
| Rename button | Rename |
| Rename error — `name_taken` | That name is taken. If it is in your trash, restore it, rename it, or empty the trash. — Open trash |
| Edit details heading | Edit details |
| Edit details fields | Title · Description · Tags |
| Edit details helper | Titles, descriptions, and tags are the only things search can see. Nothing here is filled in from your files. |
| Set TTL heading | Set an expiry for this artifact |
| Set TTL options | 7 days · 30 days · 90 days · Custom date · None |
| Set TTL body | When it expires, the artifact moves to the trash and stays restorable there for 30 days. |
| Download all | Download all |

### 12.5.8 — Files (11.8)

| Element | String |
| --- | --- |
| Header *(dynamic)* | Files · live version v{seq} · {fileCount} files · {bytes} |
| Header, single file | Files · live version v{seq} · 1 file · {bytes} |
| Header, non-live *(dynamic)* | Files · version v{seq} — not the live version. Back to versions |
| Download button | Download .tar.gz |
| Column headers | Path · Type · Size |
| Entry marker | entry |
| Row menu | Open · Download · Copy path · Copy SHA-256 · Set as entry file |
| Entry set toast *(dynamic)* | {path} now answers at the artifact root. |
| No entry banner | No file answers at this artifact's root, so visitors see a file listing. Pick an entry file to change that. |
| No delete note | Versions are immutable, so files cannot be removed from one. Post again without the file to change what is live. |

### 12.5.9 — Viewer (11.9)

| Element | String |
| --- | --- |
| Controls | Download · Open in a new tab · Close |
| Path selector label | File |
| Version strip *(dynamic)* | Viewing v{seq}. The live version is v{liveSeq}. — Restore this version |
| Unrenderable card *(dynamic)* | This is a {contentType} file. Download it to open it. |
| Video unsupported | Your browser cannot play this video's format. H.264 audio and video in an MP4 container plays everywhere. Share does not transcode anything. |
| Download card action | Download |

### 12.5.10 — Versions (11.10)

| Element | String |
| --- | --- |
| Header *(dynamic)* | Versions · {count} kept · retention: last {keepLast}, {keepDays} days |
| Retention link | Retention |
| Live marker | Live |
| Pinned marker | Pinned |
| Changes *(dynamic)* | +{added} ~{modified} −{removed} |
| Row menu | View · Files · Restore · Pin · Delete |
| Single version note | This is the only version. Posting to this name again creates the next one and keeps this one. |
| Pruned footer *(dynamic)* | Older versions were removed by retention on {date}. — Retention settings |
| Unrestorable row | A file this version needs has been removed from disk. It cannot be restored. |
| Restore dialog heading *(dynamic)* | Restore v{seq}? |
| Restore dialog body *(dynamic)* | This creates a new version, v{next}, with v{seq}'s files and entry file. It is not a rewind: v{liveSeq} stays in the history. Name, title, description, tags, TTL, pinned state, share links, and grants are unchanged. |
| Restore note field | Version note (optional) |
| Restore button | Restore as a new version |
| Restore toast *(dynamic)* | v{seq} restored as v{next}. |
| Delete version dialog *(dynamic)* | Delete v{seq}? It goes to the trash and is removed for good after 30 days. The live version is not affected. |
| Pin toast | Version pinned. It will not be pruned by retention. |

### 12.5.11 — Version preview and compare (11.11)

| Element | String |
| --- | --- |
| Header *(dynamic)* | v{seq} · {date} · {actor} · {bytes} |
| Buttons | Restore this version · Download · Back to versions |
| Compare pane heading | Files compared with the live version |
| Compare note | This compares file lists, sizes, and hashes. Share does not read your files, so there is no line-by-line diff. |
| Row markers | Added · Modified · Removed · Unchanged |
| Collapse control *(dynamic)* | Show {count} unchanged files |
| Preview pane heading | Preview |
| Live version state | This is the live version. |
| Deleted version heading | This version has been deleted |
| Deleted version body | Its files are no longer listed and it cannot be previewed or restored. |

### 12.5.12 — Sharing panel (11.12)

| Element | String |
| --- | --- |
| Status — private heading | Private |
| Status — private body | Only you can reach this. Anyone you grant can too. |
| Status — granted heading *(dynamic)* | Shared with {count} people |
| Status — granted body *(dynamic)* | {handles} can view this signed in as themselves. There is no link to forward. |
| Status — link heading | Link active |
| Status — link body *(dynamic)* | Anyone with the link can view this until {expiry} ({relative}). A password is required. |
| Status — link body, no password *(dynamic)* | Anyone with the link can view this until {expiry} ({relative}). No password is required. |
| Links section heading | Share links |
| Create button | Create share link |
| Links empty | No share links. Nobody can reach this without signing in. |
| Link card — password chip | password |
| Link card — expiry *(dynamic)* | Expires {expiry} ({relative}) |
| Link card — views *(dynamic)* | {count} views · last {date} · created by {actor}, {createdDate} |
| Link card — never viewed | Not viewed yet |
| Link card — buttons | Copy · Extend · Change password · Revoke |
| Link card — URL unavailable | The full URL was only shown when this link was created. Share stores a hash of it and cannot show it again. |
| Link card — URL unavailable action | Create a new link |
| Expired section *(dynamic)* | Expired and revoked links ({count}) |
| Expired card *(dynamic)* | Expired {date} · Revoked {date} by {actor} · Burned after {maxViews} views |
| People section heading | People |
| Share-with button | Share with… |
| People empty | Not shared with anyone on this instance. |
| Grant row *(dynamic)* | {handle} — granted {date} by {actor} · "{note}" — Remove |
| Trashed panel | This artifact is in the trash, so its sharing cannot be changed. Trashing revoked its links and grants; restoring will not bring them back. |
| Rate limited | You have created 20 share links in the last hour, which is the ceiling. Try again in {minutes} minutes. The account owner has been notified. |
| Extend popover heading | Extend this link |
| Extend popover body *(dynamic)* | Extension is added to the current expiry, so a link can never be shortened by extending it. New expiry: {expiry} ({relative}). |
| Extend button | Extend |
| Change password heading | Change this link's password |
| Change password options | Generate a new password · Set my own · Remove the password |
| Change password warning | All three sign out everyone currently viewing this link, immediately. The old password stops working and cannot be recovered. |
| Change password button | Change password |
| Revoke heading | Revoke this link? |
| Revoke body | Anyone holding the URL is locked out on their next request, and everyone currently viewing is signed out. This cannot be undone — a new link is a new URL. The artifact itself is untouched. |
| Revoke button | Revoke link |
| Revoke toast | Link revoked. |
| Share-with heading | Share with someone on this instance |
| Share-with field | Handle |
| Share-with note field | Note (optional, shown to them) |
| Share-with helper | They view it signed in as themselves at its canonical URL. They cannot edit it, share it onward, or see anything else in your space. |
| Share-with button | Share |
| Share-with error — `user_not_found` | No user with that handle on this instance. |
| Share-with error — `grant_exists` | Already shared with that person. |
| Share-with error — `cannot_grant_to_self` | That is your own account. |
| Remove grant heading *(dynamic)* | Remove access for {handle}? |
| Remove grant body | It takes effect on their next request. Any copy they already saved into their own space stays theirs. |
| Remove grant button | Remove access |

### 12.5.13 — Create share link dialog (11.13) — verbatim

Every string on this screen, in order, for all three states.

**Configure**

| Element | String |
| --- | --- |
| Dialog heading | Create a share link |
| Close control label | Close |
| Summary — meta line *(dynamic)* | {kind} · {fileCount} files · {bytes} · live version v{seq} |
| Summary — current state, private | Currently: Private — only you |
| Summary — current state, granted *(dynamic)* | Currently: Shared with {count} people |
| Summary — current state, link *(dynamic)* | Currently: Link active — expires {expiry} |
| Summary — follow-updates, agent *(dynamic)* | Anyone with this link will see the current version, including any future updates by {agentName}. |
| Summary — follow-updates, no agent | Anyone with this link will see the current version, including any future updates you post. |
| Summary — no entry point | This artifact has no entry file, so they will see a file listing rather than a page. |
| Summary — framing note | This artifact asked to allow framing. That is ignored for password-protected links, because a framed password gate is a way to steal the password. |
| Section heading — duration | How long |
| Duration presets | 30 minutes · 24 hours · 14 days · 90 days · 180 days · Custom |
| Default marker | your default |
| Disabled preset *(dynamic)* | Over the {maxTtl} ceiling set on this instance |
| Custom label | Ends at |
| Custom helper *(dynamic)* | Between 5 minutes and {maxTtl} from now. |
| Expiry readout *(dynamic)* | Expires {expiry} ({relative}) |
| No-permanent note | Every share link expires. There is no permanent option. — Why |
| Section heading — password | Password |
| Password option 1 | No password — anyone with the link gets in |
| Password option 1 helper | Anyone who receives, forwards, or finds this URL can view the artifact until it expires. |
| Password option 2 | Generate a password for me |
| Password option 2 helper | Two words and two digits, made to be read aloud over the phone. Shown once, when the link is created. |
| Password option 3 | Set my own password |
| Password field label | Password |
| Password field helper | Minimum 8 characters. No other rules. |
| Password reveal control | Show |
| Section heading — label | Label |
| Label field helper | Only you see this. It appears in your link list, this artifact's activity, and the audit log. |
| Label placeholder | Who is this for? |
| Advanced disclosure | Advanced |
| Max views label | Burn after this many views |
| Max views helper | Counted in distinct viewer-days, not requests, so one person reloading the page does not burn the link. Leave empty for unlimited. |
| Buttons | Cancel · Continue |
| Error — `ttl_too_long` *(dynamic)* | This instance caps share links at {maxTtl}. |
| Error — `password_too_short` | Passwords need at least 8 characters. |

**Confirm**

| Element | String |
| --- | --- |
| Dialog heading | Create a share link |
| Lead sentence | You are about to make this reachable by anyone holding a URL, until it expires. |
| Read-back labels | Expires · Password · Label · Views |
| Expires value *(dynamic)* | {expiry} ({relative}) |
| Password value, generated | Generated — shown once, on the next screen |
| Password value, own | Set by you |
| Password value, none | None — anyone with the link gets in |
| Label value, empty | None |
| Views value, unlimited | Unlimited |
| Views value *(dynamic)* | Burns after {maxViews} views |
| Notification line, on | You will be emailed when this link is created, and again 24 hours before it expires. |
| Notification line, off | Share-link emails are off, so you will not be notified about this link. — Notification settings |
| Buttons | Back · Create link |
| Submitting | Creating… |
| Network failure | The request did not complete, and a link may have been created. Retrying is safe — it cannot create a second one. — Retry |
| Error — `artifact_trashed` heading | This artifact is in the trash |
| Error — `artifact_trashed` body | Restore it before sharing it. |
| Error — `artifact_trashed` action | Go to trash |
| Error — rate limited *(dynamic)* | You have created 20 share links in the last hour, which is the ceiling on this instance. Try again in {minutes} minutes. The account owner has been notified. |

**Created**

| Element | String |
| --- | --- |
| Dialog heading | Share link created |
| Lead *(dynamic)* | {name} is now reachable by anyone with this link. |
| Section heading — link | Link |
| Copy link control | Copy |
| Section heading — password | Password — shown once, right now |
| Password explainer | This is the only time this password is displayed. It is not stored in a form anyone can read, including us. If you lose it, create a new link. |
| Expiry line *(dynamic)* | Expires {expiry} ({relative}) |
| Back-button note | Closing this panel or pressing back loses the password. The link stays. |
| Combined copy button | Copy link and password |
| Combined clipboard payload *(dynamic)* | {url}\nPassword: {password}\nExpires {expiry} |
| Copy confirmation | Copied |
| Copy toasts | Link copied · Password copied · Link and password copied |
| Exit button | Done |
| Screen-reader announcement *(dynamic)* | Share link created. Expires {expiryLongForm}. The password is shown once on screen. |

### 12.5.14 — Shared with me (11.14)

| Element | String |
| --- | --- |
| Page title | Shared with me |
| Column headers | Name · Owner · Updated · Size |
| Row advisory *(dynamic)* | Belongs to @{handle}. If they delete it, it disappears from here. |
| Row actions | Open · View · Download · Save a copy |
| Empty heading | Nothing has been shared with you |
| Empty body | Another user on this instance has to grant you an artifact for it to appear here. |
| Grant revoked toast *(dynamic)* | {name} is no longer shared with you. |
| Save-a-copy heading | Save a copy |
| Save-a-copy body | The copy lands in your space as your own artifact. It is private with no share links, whatever this one has. It costs no extra storage — identical files are stored once. |
| Save-a-copy fields | Name · Title |
| Save-a-copy button | Save a copy |
| Save-a-copy toast *(dynamic)* | Saved as {name} in your space. The owner sees the copy in their artifact's activity. — Open |

### 12.5.15 — Trash (11.15)

| Element | String |
| --- | --- |
| Header *(dynamic)* | Trash · {count} artifacts · {bytes} · deleted after 30 days |
| Subheader | Items here still count against your storage quota. |
| Empty trash button | Empty trash |
| Column headers | Name · Deleted · Gone on · Size |
| Going-soon group | Going soon |
| Row menu | Restore · Delete permanently · View files |
| Empty heading | Nothing in the trash |
| Empty body | Deleted artifacts stay here for 30 days before they are removed for good. |
| Name conflict marker | Name taken |
| Name conflict body *(dynamic)* | Another artifact now uses the name {name}. Restoring will ask you to pick a new one. |
| Over-quota banner *(dynamic)* | You are over your storage quota. Emptying the trash frees {bytes} and is the fastest way back under it. |
| Restore heading *(dynamic)* | Restore {name}? |
| Restore body | Every version comes back and the artifact resolves at its URL again. Its share links and grants do not come back — trashing revoked them, and anyone who held a link stays locked out until you make a new one. |
| Restore button | Restore |
| Restore rename field | New name |
| Restore toast *(dynamic)* | {name} restored. — Open |
| Delete permanently heading *(dynamic)* | Delete {name} permanently? |
| Delete permanently body *(dynamic)* | Every version of this artifact goes, and every file nothing else references is removed from disk. {bytes} freed. This cannot be undone. |
| Type-to-confirm label *(dynamic)* | Type {name} to confirm |
| Delete permanently button | Delete permanently |
| Empty trash heading | Empty the trash? |
| Empty trash body *(dynamic)* | {count} artifacts and every version they hold are deleted for good, freeing {bytes}. This cannot be undone. |
| Empty trash confirm label | Type empty trash to confirm |
| Empty trash button | Empty trash |

### 12.5.16 — Search and command palette (11.16)

| Element | String |
| --- | --- |
| Input placeholder | Search names, titles, descriptions, and tags |
| Group headings | Artifacts · Actions · Recent |
| Actions | Upload a file · Create an API token · Open trash · Review storage · Things you have not opened |
| Key hints | ↑↓ navigate · ⏎ open · ⌘⏎ new tab · esc close · → all results |
| All results link | See all results |
| No matches *(dynamic)* | No artifacts match "{query}". |
| Standing explanation | Search covers names, titles, descriptions, and tags — never the contents of your files. — Why |
| First-use footer | Search covers only your own artifacts and anything shared with you. There is no instance-wide search. |
| Rate limited *(dynamic)* | Too many searches. Results resume in {seconds} seconds. |
| Full page title *(dynamic)* | Results for "{query}" |

### 12.5.17 — Upload (11.17)

| Element | String |
| --- | --- |
| Page title | Upload |
| Drop zone | Drop a file or a folder here, or choose one |
| Drop zone helper | A folder keeps its structure, so a page with its styles and images works as posted. |
| Choose file button | Choose files |
| Choose folder button | Choose a folder |
| Name field | Name |
| Name helper *(dynamic)* | This is the address: share.c52.com/{name}. Lowercase letters, digits, `.`, `_`, `-`, and `/`. |
| Name normalized note *(dynamic)* | Posting as {normalized} |
| Title / description / tags labels | Title (optional) · Description (optional) · Tags (optional) |
| Metadata helper | These are the only things search can see. Nothing is filled in from your files. |
| Entry file label | Which file answers at the root |
| TTL label | Expires after (optional) |
| Standing note | Posting does not share anything. This artifact will be private until you create a share link. |
| Primary button | Post artifact |
| Hashing *(dynamic)* | Reading {count} files… Large files take a moment. |
| Uploading *(dynamic)* | Uploading {done} of {total} |
| Skipped *(dynamic)* | {skipped} of {total} files are already on the server. |
| Committing | Finishing… |
| Refused — path | This path cannot be posted: {path}. Rename it and try again. |
| Refused — dotfile | Files and folders starting with a dot cannot be posted: {path}. |
| Refused — secret *(dynamic)* | {path} looks like a credential file. Share will not accept it from a browser. |
| Error — `name_taken` *(dynamic)* | {name} already exists. Overwriting keeps the current version and makes this v{next}. |
| Error — `name_taken` actions | Overwrite as a new version · Use a different name |
| Error — `quota_exceeded` *(dynamic)* | This would use {projected} of your {quota} quota. You are at {current} now. — Manage storage |
| Interrupted | The upload stopped. Nothing is live yet and the files already sent are still on the server. — Resume |
| Success toast *(dynamic)* | Posted {name} v{seq} — private. — Copy URL |

### 12.5.18 — API tokens (11.18)

| Element | String |
| --- | --- |
| Page title | API tokens |
| New token button | New token |
| Column headers | Name · Prefix · Scopes · Last used |
| Never used | never |
| Revoked section *(dynamic)* | Revoked ({count}) |
| Row summary *(dynamic)* | created {date} · {count} artifacts posted |
| Row menu | Edit scopes · Rename · View activity · View artifacts · Revoke |
| Empty heading | No tokens yet |
| Empty body | An agent needs a token to post here. Create one below, or run `share login` and approve it from this browser. |
| New token heading | New API token |
| Name field | Name |
| Name placeholder | agent@machine |
| Name helper | This name appears on every artifact it posts and in every audit record. |
| Expiry field | Expires (optional) |
| Scopes heading | What this token can do |
| Scope — `artifacts:read` | Read and download your artifacts |
| Scope — `artifacts:write` | Post, overwrite, rename, tag, and move to the trash |
| Scope — `artifacts:delete` | Delete permanently, skipping the trash |
| Scope — `share:create` | Create, extend, and revoke share links, and grant to other users |
| Scope — `account:read` | Read your profile, quota, and token list |
| Scope — `account:admin` | Create tokens, invite users, and change settings |
| Create button | Create token |
| Created heading | Token created |
| Created body | Shown once, right now. Store it in whatever your agent reads secrets from. |
| Created MCP block heading | Ready to paste into your MCP host |
| Created exit | Done |
| Revoke heading *(dynamic)* | Revoke {name}? |
| Revoke body | The agent using it stops working on its next request. Everything it posted stays, still attributed to it. This cannot be undone — a new token is a new secret. |
| Revoke button | Revoke token |
| Scope change confirm *(dynamic)* | Give {name} the ability to create share links? |

### 12.5.19 — Passkeys and sessions (11.19)

| Element | String |
| --- | --- |
| Page title | Security |
| Passkeys heading | Passkeys |
| Add button | Add a passkey |
| Passkey row *(dynamic)* | {name} — added {date} · last used {relative} |
| Backup state | syncs across your devices · this device only |
| Passkey actions | Rename · Revoke |
| One-passkey advisory | You have one passkey. If you lose it, the only ways back in are your recovery code or access to the server. — Add another |
| Last passkey refusal | This is your only passkey and it cannot be revoked. Register another one first. |
| Revoke passkey heading *(dynamic)* | Revoke {name}? |
| Revoke passkey body *(dynamic)* | It stops working immediately and the {count} sessions created with it are signed out. This cannot be undone; the authenticator can be registered again as a new passkey. |
| Revoke passkey, own session | You are signed in with this passkey, so you will be signed out. |
| Sessions heading | Sessions |
| Session row *(dynamic)* | {userAgent} · {ip} · started {date} · last seen {relative} · via {passkeyName} |
| This device marker | This device |
| Sign out everywhere | Sign out everywhere |
| Sign out everywhere confirm | Every session is signed out, including this one. Your passkeys and tokens are unaffected. |
| Recovery card heading | Recovery code |
| Recovery card, exists *(dynamic)* | One outstanding code, generated {date}. |
| Recovery card, none | No recovery code. Generate one now — it is the only way back if every passkey is gone and you cannot reach the server. |
| Generate button | Generate a new code |
| Generate confirm | The current code stops working immediately and the new one is shown once. |
| Recovery-session notice | This session came from a recovery code and can only register a passkey. |

### 12.5.20 — Security overview (11.20)

| Element | String |
| --- | --- |
| Page title | Security overview |
| Card 1 heading | Reachable without signing in |
| Card 1 empty | Nothing of yours is reachable without a sign-in. |
| Card 1 row *(dynamic)* | {name} — expires {expiry} ({relative}) |
| Card 2 heading | Recent sign-ins |
| Card 3 heading | Anomalies |
| Card 3 empty | Nothing unusual in the last 7 days. |
| Card 4 heading | Tokens |
| Card 4 body *(dynamic)* | {live} live · {sharing} can create share links |
| Anomaly — link rate *(dynamic)* | {token} created {count} share links in an hour. |
| Anomaly — first link *(dynamic)* | {token} created its first share link. |
| Anomaly — bulk post *(dynamic)* | {token} posted {bytes} in an hour. |
| Anomaly — bulk create *(dynamic)* | {token} created {count} artifacts in an hour. |
| Anomaly — bulk trash *(dynamic)* | {token} moved {count} artifacts to the trash in an hour. |
| Anomaly — new IP *(dynamic)* | {token} was used from an address it has not been seen at before. |
| Anomaly — recovery code | A recovery code was used to sign in. |
| Anomaly — counter regression *(dynamic)* | Passkey {name} reported an unexpected use count, which can mean it has been copied. |
| Anomaly action | Revoke this token |
| Panic button | Revoke all share links |
| Panic heading | Revoke every share link on your account? |
| Panic body *(dynamic)* | {count} live links stop working immediately and everyone currently viewing one is signed out. This cannot be undone. Your artifacts and grants are untouched. |
| Panic confirm label | Type revoke all to confirm |
| Instance toggle | My account · This instance |

### 12.5.21 — Settings (11.21)

| Element | String |
| --- | --- |
| Page title | Settings |
| Profile heading | Profile |
| Display name | Display name |
| Email | Email — changed by the operator |
| Handle | Handle — permanent |
| Sharing heading | Sharing |
| Default TTL | Default share-link duration |
| Default TTL helper | The preset marked "your default" when you create a link. |
| Notify on share | Email me when a share link is created |
| Notify on share helper | Including links created by an agent holding `share:create`. |
| Notify on expiring | Email me 24 hours before a link expires |
| Standing sharing note | Every share link expires. There is no setting for that. — Why |
| Versions heading | Versions |
| Retention fields | Keep the last · Keep for · Keep pinned versions · Never go below |
| Retention helper | Pruning runs overnight, not when you save this. |
| Retention preview *(dynamic)* | This would prune {count} versions across {artifacts} artifacts on the next nightly run. |
| Staleness heading | Staleness |
| Stale days | Count an artifact stale after |
| Stale helper | Nothing is ever deleted for being stale. It only appears in a list. |
| Notifications heading | Notifications |
| Notification rows | Storage warnings · A token was created · Unusual activity |
| Always-on row | A recovery code was used · A passkey reported an unexpected use count |
| Always-on reason | Always on. These two mean someone may be getting into your account. |
| Display heading | Display |
| Time zone | Show times in |
| Time zone options | UTC · This browser's time zone |
| Saved indicator | Saved |
| Save failed | That did not save. The old value is back. |

### 12.5.22 — Users and invites (11.22)

| Element | String |
| --- | --- |
| Page title | Users |
| Users column headers | Handle · Name · Email · Artifacts · Storage · Last seen |
| Invite button | Invite someone |
| Invites heading | Pending invites |
| Invites column headers | Email · Handle · Invited by · Expires |
| Only-you body | You are the only account. Share has no sign-up — people get accounts because you invite them. |
| Invite heading | Invite someone |
| Invite fields | Email address · Handle |
| Invite preview *(dynamic)* | Their space will be share.c52.com/~{handle}. |
| Invite helper | The handle is claimed now and cannot be changed later. Invites are good for 7 days. |
| Invite button | Send invite |
| Invite error — reserved | That handle is reserved. |
| Invite error — taken | That handle is already claimed. |
| Invite rate limited *(dynamic)* | 10 invites a day is the ceiling. Try again in {hours} hours. |
| Invite actions | Resend · Revoke |
| Invite expired note | Expired. Revoke it and send a new one. |
| Disable heading *(dynamic)* | Disable {handle}? |
| Disable body | Their sessions and every token they hold are revoked immediately. Their artifacts stay. Live share links on their artifacts keep working until they expire. |
| Disable checkbox | Revoke their share links too |
| Disable button | Disable user |
| Disabled row note | Disabled. Sessions and tokens revoked; artifacts retained. |
| No-delete note | There is no delete-a-user action here. Removing a user and their artifacts for good is `sharectl delete-user`, on the server. |

### 12.5.23 — Audit log (11.23)

| Element | String |
| --- | --- |
| Page title | Audit log |
| Filters | Action · Actor · Token · Date range · Search |
| Shortcut | Sharing only |
| Column headers | Time · Action · Actor · Target · Address |
| Expander | Details |
| System actor | system |
| Export button | Export as NDJSON |
| Export note | Exports the current filter, streamed. |
| Deleted target note | This target has been deleted. The name shown is what it was called at the time. |
| Empty for filters | No events match these filters. |
| Instance toggle | My events · This instance |
| Instance strip | Showing every user's events on this instance. |
| Pagination | Newer · Older |

### 12.5.24 — Staleness (11.24)

| Element | String |
| --- | --- |
| Page title | Not opened recently |
| Header *(dynamic)* | {count} artifacts you have not opened in {days} days · {bytes} |
| Window link | Change the window |
| Column addition | Last opened |
| Never viewed | never opened |
| Footnote | Pinned artifacts, and anything with a live share link or grant, are never listed here. |
| Nothing stale *(dynamic)* | Everything you own has been opened in the last {days} days. |
| Bulk bar *(dynamic)* | {count} selected · {bytes} |
| Bulk button | Move selected to trash |
| Bulk confirm *(dynamic)* | Move {count} artifacts ({bytes}) to the trash? They stay restorable for 30 days. Their share links and grants are revoked now and are not restored on restore. |
| Bulk progress *(dynamic)* | {done} of {count} moved |
| Bulk partial failure *(dynamic)* | {done} moved. {failed} could not be: {names}. |
| Keep action | Keep |
| Keep toast *(dynamic)* | {name} pinned. Pinned artifacts never appear here. |

### 12.5.25 — Storage and quota (11.25)

| Element | String |
| --- | --- |
| Page title | Storage |
| Meter *(dynamic)* | {used} of {quota} · {percent} |
| Artifact count *(dynamic)* | {count} artifacts |
| 80% note | Above 80%. Storage warnings are emailed at most once a day. |
| 95% note | Above 95%. Posting fails at 100%. |
| 100% note | Out of storage. Posting is refused. Reading, sharing, and deleting still work, so you can always dig out. |
| Largest heading | Largest artifacts |
| Free-space heading | What would free space |
| Free-space rows *(dynamic)* | Trash — {bytes} · Not opened in {days} days — {bytes} · Old versions — about {bytes} |
| Free-space actions | Open trash · Review · Retention settings |
| Dedup footnote | Identical files are stored once for the whole instance, and each user is charged for every file their artifacts reference. Your figure is what your artifacts reference, which is why it will not match a simple sum of what is on disk. |
| Operator note | If this figure looks wrong, `sharectl recompute-quota` recounts it from the manifests. |
| Root disk row *(dynamic)* | Instance disk: {free} free of {total} · last backup {date} |

### 12.5.26 — Device authorization (11.26)

| Element | String |
| --- | --- |
| Page title | Authorize an agent |
| Intro | Enter the code your agent printed. |
| Field label | Code |
| Field placeholder | XXXX-XXXX |
| Lookup button | Continue |
| Approval heading *(dynamic)* | Give {agentName} a token? |
| Approval rows | Requested from · Started · Scopes |
| Approval scopes | Read and download your artifacts · Post, overwrite, rename, tag, and move to the trash |
| Approval hard line | This token will not be able to create share links. |
| Approval buttons | Approve · Deny |
| Unknown code | That code is not valid. It may have expired — codes last 10 minutes. Run the command again for a new one. |
| Already approved | That code has already been used. |
| Approved heading | Approved |
| Approved body *(dynamic)* | {agentName} has a token. Return to your terminal — the token is not shown here. |
| Approved action | Manage this token |
| Denied heading | Denied |
| Denied body | No token was issued. The agent will report that the request was refused. |
| Rate limited *(dynamic)* | Too many authorization attempts. Try again in {minutes} minutes. |

### 12.5.27 — Help and agent setup (11.27)

| Element | String |
| --- | --- |
| Page title | Help |
| Nav sections | Quickstart · Posting artifacts · Privacy and sharing · Share links and grants · Versions, trash, and getting things back · Search · Connecting agents · CLI reference · Passkeys and recovery · Users and invites · Storage and quotas |
| Agent page title | Connecting agents |
| No-token callout | You have no tokens yet. An agent needs one to post here. — Create a token |
| Copy control | Copy |
| Copy confirmation | Copied |
| Token placeholder note | Replace `shr_YOUR_TOKEN` with a real token. Share never fills a real token into these blocks. |
| Linked topics heading | Three things people ask |
| Linked topics | Why search cannot read your files · Why every share link expires · What happens when an agent overwrites something you shared |

### 12.5.28 — Instance status (11.28)

| Element | String |
| --- | --- |
| Page title | Instance status |
| Tiles | Version · Uptime · Disk · Last backup · Queues |
| Subsystem headers | Check · State · Detail |
| Subsystems | Database · Redis · File storage · Worker · Migrations |
| All green | Everything is responding. |
| Degraded *(dynamic)* | {check} is not healthy. |
| Disk warning *(dynamic)* | Disk is {percent} full. |
| Backup stale *(dynamic)* | Last successful backup: {date}. |
| Worker behind | The worker is behind. View counts and precompression lag; nothing is lost. |
| Read-only note | This screen is read-only. Restarts, flushes, and destructive operations are `sharectl` commands on the server. |
| Non-root view | Version, uptime, and your own storage. Everything else is visible to the operator. |

### 12.5.29 Global patterns

**App shell**

| Element | String |
| --- | --- |
| Sidebar groups | Library · Agents |
| Sidebar items | Artifacts · Shared with me · Trash · API tokens · Audit log |
| Storage meter *(dynamic)* | {used} of {quota} |
| User menu | Settings · Security · Security overview · Users · Instance status · Help · Sign out |
| Anomaly dot tooltip | Something unusual happened in the last 7 days. |

**Sharing-state indicator**

| State | Label | Detail |
| --- | --- | --- |
| Private | Private | Only you — or, where space allows: Only you and anyone you grant |
| Granted *(dynamic)* | Shared with {count} people | {handles} |
| Link *(dynamic)* | Link active | expires {expiry} — with ({relative}) where the container is wide enough |
| Icon-only accessible name *(dynamic)* | Link active, expires {expiryLongForm}, password required | — |

**Toasts and clipboard**

| Event | String |
| --- | --- |
| Generic copy | Copied |
| Artifact URL copied | URL copied. This is the signed-in address — it will not work for anyone else. |
| Path copied | Path copied |
| SHA-256 copied | SHA-256 copied |
| Undo affordance | Undo |
| Undo expired | That can no longer be undone here. — Open trash |
| Optimistic revert *(dynamic)* | That change did not save and has been put back. {message} |
| Error toast suffix *(dynamic)* | {message} · {code} — Copy request ID |

**Errors and connection**

| Element | String |
| --- | --- |
| Region error retry | Retry |
| Route 404 heading | Not found |
| Route 404 body | This artifact does not exist, or it is not yours. |
| Route 403 heading | Not available |
| Route 403 body | This part of Share is not available to your account. |
| Connection lost | Cannot reach share.c52.com. Retrying. — Retry now |
| Connection restored | Reconnected. |
| Maintenance in app | share.c52.com is not responding. It may be restarting. — Instance status |

**Confirmation dialogs**

| Element | String |
| --- | --- |
| Cancel | Cancel |
| Type-to-confirm mismatch | That does not match. |
| Irreversible marker | This cannot be undone. |

**Keyboard reference sheet (`?`)**

| Element | String |
| --- | --- |
| Heading | Keyboard shortcuts |
| Rows | Command palette · Focus search · Go to artifacts · Go to shared · Go to trash · Go to tokens · Upload · Close · Move selection · Open · Open in a new tab · This sheet |
| Footnote | Nothing destructive has a shortcut. Deleting always takes a menu and a confirmation. |

---

## 12.6 Warning and advisory catalogue

Advisories are never blocking. Over the API they arrive in `warnings[]` as
`{ "code": "...", "message": "..." }` with the exact message below. In the CLI they print to
stderr as `warning: <message>`. In the dashboard they appear where the "Shown" column says, in
the informational treatment unless marked amber.

| Code | Message | Shown | What to do |
| --- | --- | --- | --- |
| `no_entry_point` | No file answers at this artifact's root, so visitors see a file listing. Set an entry file to change that. | Post response; artifact detail beside the kind line; Files tab banner | Pick an entry file on the Files tab, or post again with `entryPath`. Takes effect without reposting. |
| `shadowing_name` | An artifact named {other} already exists, and this name is a prefix of it. Paths under /{name}/ now resolve inside this artifact first. | Post response; upload screen; artifact detail | Rename one of the two if the addresses matter. Nothing breaks if they do not overlap. |
| `ttl_with_live_links` | This artifact has {count} live share links. When it expires, it moves to the trash and those links stop working. | Set TTL dialog before confirming (amber); `PATCH` response | Shorten the TTL, extend nothing, or revoke the links deliberately rather than letting them die with the artifact. |
| `secret_file_found` | {path} looks like a credential file. It was not posted. | CLI, before upload (amber); browser upload, as a refusal | Remove it from the directory, or exclude it. The CLI needs `--force-secrets` to send it; the browser will not send it at all. |
| `low_quota` | You are using {percent} of your {quota} storage. Posting fails at 100%. | Post response above 80%; dashboard banner (amber); storage screen | Empty the trash, review artifacts you have not opened, or tighten version retention. |
| `link_expiring` | This share link expires {expiry} ({relative}). | Sharing panel and artifact detail inside 48 hours (amber); dashboard banner | Extend it, or let it end. Extension adds to the current expiry. |
| `artifact_expiring` | This artifact expires {expiry} ({relative}) and moves to the trash. | Artifact detail strip (amber); dashboard banner | Choose **Keep this artifact** to clear the TTL, or change it. |
| `phishing_shape` | This artifact contains a password field in a form that submits to another site. Share does not block it, and you are the only person being told. | Post response; artifact detail (amber); create-link summary | If it is a mockup, ignore it. If it is not, do not share it — a link like this can get the whole domain flagged. |
| `framing_disabled` | This artifact asked to allow framing. That is ignored for password-protected links, because a framed password gate is a way to steal the password. | Create-link summary; post response | Nothing, unless the artifact needs to be embedded, in which case share it without a password. |
| `large_video` | This video is {bytes}. Share does not transcode anything, so it plays only where the browser supports its format. H.264 audio and video in an MP4 container plays everywhere. | Post response for video over 500 MB; upload screen | Nothing required. Re-encode before posting if recipients may be on older browsers. |
| `untitled_artifact` | This artifact has no title, so it shows its name everywhere. Search can only see names, titles, descriptions, and tags. | Post response; artifact detail | Add a title and tags. Share will never generate one from the contents. |
| `generated_name` | No name was supplied, so this artifact is at {name}. Generated names are fine for scratch output and hard to find later. | Post response; CLI output; artifact detail for the first 7 days | Rename it if you will come back to it. Renaming does not break share links. |
| `no_second_passkey` | You have one passkey. If you lose it, the only ways back in are your recovery code or access to the server. | Security screen (amber); first-run checklist; after registering the first passkey | Register a second passkey on another device. |
| `unrecoverable_link_url` | The full URL was only shown when this link was created. Share stores a hash of it and cannot show it again. | Sharing panel, on any link not created in this browser session | Create a new link if you need to send it again, then revoke the old one. |

Two scope warnings are not advisories in `warnings[]` — they are inline confirmations on 11.18,
and they read:

> **`share:create`** — This token will be able to make your artifacts reachable by anyone with a
> URL, without asking you. You will be emailed each time it does. Leave this off unless the agent
> genuinely needs it.

> **`artifacts:delete`** — This token will be able to delete artifacts permanently, skipping the
> trash. Without it, the worst it can do is fill the trash, which you can undo.

---

## 12.7 Recipient-facing pages (R1–R7)

These pages are seen by clients and counterparties. They are plain, they do not brand, and they
give away nothing about whether an artifact exists or who owns it. Every one carries the
hostname `share.c52.com` as plain text at the top and nothing else that could identify the
sender.

### R1 — Share-link password gate (401)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading | This link needs a password. |
| Field label | Password |
| Button | Continue |
| Wrong password | That password is not correct. |
| Rate limited heading | Too many attempts. |
| Rate limited body *(dynamic)* | Try again in {minutes} minutes. |
| `<title>` | share.c52.com |

Nothing else appears on this page: no artifact name, no title, no file type, no size, no sender,
no expiry, no attempt counter, and no link anywhere else in the product.

### R2 — Landing for a non-HTML artifact (200)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Title line *(dynamic)* | {title} — omitted entirely when the owner set no title |
| Metadata line *(dynamic)* | {kind} · {fileCount} files · {bytes} |
| Metadata line, single file *(dynamic)* | {kind} · {bytes} |
| Primary button | View |
| Secondary button | Download |
| Unrenderable body *(dynamic)* | This is a {contentType} file. |
| `<title>` *(dynamic)* | {title} — otherwise share.c52.com |

No copy-URL control, no sharing controls, no sign-in prompt, and no invitation to make an
account.

### R3 — Link expired or revoked (410)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading | This link is no longer active. |
| Body | Ask whoever sent it for a new one. |
| `<title>` | share.c52.com |

One state only. Expired, revoked, burned through its view limit, and deleted are deliberately
indistinguishable. No artifact name, no owner, no date, no reason, and no controls.

### R4 — Not found (404)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading | Not found. |
| Body | Nothing is available at this address. |
| `<title>` | share.c52.com |

Byte-identical for every cause: a name that never existed, an artifact that is not yours, an
expired TTL, something in the trash, and a missing file inside an artifact you can see all
produce exactly this. No sign-in link — offering one would tell a scanner that signing in might
help.

### R5 — Rate limited (429)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading | Too many requests. |
| Body *(dynamic)* | Try again in {minutes} minutes. |
| Body, under a minute | Try again in a moment. |
| `<title>` | share.c52.com |

The bucket name never appears here. It is in `detail.bucket` on API responses, where an agent
can act on it.

### R6 — Maintenance (503)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading | share.c52.com is not available right now. |
| Body | It is probably restarting. Try again shortly. |
| `<title>` | share.c52.com |

No timestamp, no estimate, and no auto-refresh: this is a static file that cannot know when the
service came back, and an unattended tab reloading a downed instance is exactly the traffic an
operator does not need mid-incident.

### R7 — Artifact file listing (200)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading *(dynamic)* | {title} — otherwise {name}; through a share link, {title} or nothing |
| Metadata line *(dynamic)* | {fileCount} files · {bytes} |
| Column order | path, content type, size — as plain text, no header row |

Every path is a relative link, so it resolves under whichever address is in the bar, including
`/s/{token}/`. Sorted by path with directories grouped. No sorting controls, no search, no
download-all, and no owner handle — through a share link the heading never reveals a name the
recipient was not given.

---

## 12.8 Error message catalogue

Every `code` defined in Parts 4–10, with the sentence that ships in `error.message`. These
sentences are one sentence each, safe to print to a terminal, free of paths and credentials, and
they are what the dashboard shows when it has nothing more specific (§11.29.10). The CLI column
is filled only where the terminal phrasing differs; otherwise the CLI prints
`error: <code>: <message>` with the same sentence.

### 12.8.1 Authentication and identity (Part 4)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `invalid_token` | 401 | That API token is not valid. | No valid token. Run `share login`, or set SHARE_TOKEN. |
| `invalid_credential` | 401 | That passkey is not registered here. | — |
| `credential_counter_regressed` | 401 | This passkey reported an unexpected use count, which can mean it has been copied; sign-in was refused and the account owner has been emailed. | — |
| `webauthn_verification_failed` | 401 | That sign-in could not be verified. | — |
| `session_expired` | 401 | Your session has ended. Sign in again. | — |
| `recipient_auth_required` | 401 | This link needs a password. | — |
| `recipient_auth_failed` | 401 | That password is not correct. | — |
| `insufficient_scope` | 403 | This token does not have the {scope} scope. | This token cannot do that: it needs {scope}. Add it on the API tokens screen. |
| `csrf_failed` | 403 | That request could not be verified. Reload the page and try again. | — |
| `wrong_credential_class` | 403 | That credential cannot be used here — share links open artifacts, not the API. | — |
| `invite_expired` | 410 | This invite has expired. Ask whoever invited you for a new one. | — |
| `authorization_pending` | 428 | Waiting for someone to approve this request in the dashboard. | Waiting for approval… |

### 12.8.2 Artifacts, uploads, and naming (Part 5)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `file_hash_mismatch` | 400 | The uploaded bytes do not match the digest they were declared with. | Upload of {path} did not match its checksum. Retrying is safe. |
| `file_size_mismatch` | 400 | The uploaded file is a different size than declared. | Upload of {path} was a different size than declared. Retrying is safe. |
| `upload_signature_invalid` | 403 | That upload link has expired or been altered. | Upload link expired. Re-run the post; files already sent are kept. |
| `not_your_artifact` | 403 | That artifact belongs to another user's space. | — |
| `artifact_not_found` | 404 | No artifact named {name} in your space. | — |
| `version_not_found` | 404 | That version does not exist. | — |
| `file_not_found` | 404 | That file is not in this version. | — |
| `name_taken` | 409 | The name {name} is already in use, possibly by something in your trash. | The name {name} is taken. Restore it, rename it, or empty the trash. |
| `files_missing` | 409 | Some declared files have not been uploaded yet. | {count} files still uploading. |
| `upload_session_closed` | 409 | That upload has already been committed or abandoned. | — |
| `upload_session_expired` | 409 | That upload session has expired. Start it again — the files already sent are still on the server. | Upload session expired. Re-running is cheap: nothing needs re-uploading. |
| `idempotency_key_reused` | 409 | That idempotency key was already used with a different request. | — |
| `quota_exceeded` | 413 | This post would use {projected} of your {quota} storage limit. | Out of storage: {projected} needed, {quota} allowed. Empty your trash or delete something. |
| `artifact_too_large` | 413 | This version is {size}, over the {limit} limit for one artifact version. | — |
| `file_too_large` | 413 | {path} is {size}, over the {limit} limit for one file. | — |
| `too_many_files` | 413 | This version has {count} files, over the limit of {limit}. | — |
| `invalid_name` | 422 | {name} is not a valid artifact name — use lowercase letters, digits, dots, underscores, hyphens, and slashes, starting with a letter or digit. | — |
| `name_reserved` | 422 | {name} is reserved by Share and cannot be used as an artifact name. | — |
| `invalid_path` | 422 | The file path {path} cannot be used. | — |
| `dotfile_rejected` | 422 | Files and folders starting with a dot cannot be posted: {path}. | {path} starts with a dot and was refused. Exclude it. |
| `path_case_collision` | 422 | Two files differ only by capitalization: {a} and {b}. Rename one. | — |
| `invalid_archive` | 422 | That archive contains a symlink, a device file, or a path that escapes the archive. | — |
| `archive_ratio_exceeded` | 422 | That archive expands too far to be accepted. | — |
| `use_share_endpoint` | 422 | Sharing is not changed here — use the share-link endpoints. | Use `share link` to change sharing. |
| `too_many_uploads` | 429 | Too many uploads running on this session at once. | Slowing down: too many parallel uploads. Try `--concurrency 4`. |

### 12.8.3 Serving (Part 6)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `not_found` | 404 | Nothing is available at this address. | — |
| `link_expired` | 410 | This link is no longer active. | This link is no longer active. |

`not_found` is returned identically for an unknown name, an artifact that is not yours, an
expired TTL, a trashed artifact, and a missing file inside a visible artifact. No variant of this
message exists.

### 12.8.4 Sharing (Part 7)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `insufficient_scope` | 403 | This token cannot create share links — it needs the share:create scope. | This token cannot create share links. Create it in the dashboard, or add share:create to the token. |
| `not_your_artifact` | 403 | That artifact belongs to another user's space. | — |
| `link_not_found` | 404 | No such share link, or it has already been revoked. | — |
| `grant_not_found` | 404 | No such grant. | — |
| `user_not_found` | 404 | No user with the handle {handle} on this instance. | — |
| `grant_exists` | 409 | That artifact is already shared with {handle}. | — |
| `cannot_grant_to_self` | 409 | That is your own account. | — |
| `ttl_too_long` | 422 | Share links on this instance last at most {maxTtl}. | — |
| `password_too_short` | 422 | A link password needs at least 8 characters. | — |
| `artifact_trashed` | 422 | That artifact is in the trash and cannot be shared until it is restored. | — |

### 12.8.5 Versions, trash, and search (Part 8)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `version_is_live` | 409 | The live version cannot be deleted. | — |
| `version_deleted` | 409 | That version has been deleted and cannot be previewed or restored. | — |
| `artifact_not_trashed` | 409 | That artifact is not in the trash. | — |
| `name_taken` | 409 | Another artifact now uses the name {name}. Restore it under a different name. | The name {name} is in use. Restore with `--name <new>`. |
| `invalid_ttl` | 422 | {value} is not a valid duration or is in the past. | — |
| `invalid_filter` | 422 | {parameter} is not a filter Share supports. | — |
| `restore_files_missing` | 422 | A file this version needs has been removed from disk, so it cannot be restored. | — |

### 12.8.6 Limits and instance state (Part 10)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `rate_limited` | 429 | Too many requests. Try again in {minutes} minutes. | Rate limited on {bucket}. Retrying in {seconds}s. |
| `disk_full` | 507 | This instance is out of disk space, so posting is refused. Reading and sharing still work. | Server is out of disk. Posting refused; the operator has been notified. |

### 12.8.7 Rules that apply to every message

- No message names a filesystem path on the server, a database identifier, a token, a password,
  or an internal hostname. `{path}` is always the path the caller supplied.
- No message says "please", "sorry", or "unexpected".
- A 404 never explains why. `artifact_not_found` is returned over the API to a caller who is
  authenticated into their own space; every unauthenticated or cross-space miss is `not_found`.
- The dashboard never invents friendlier text for an unknown code: it prints `error.message`.
- Every error response carries `requestId`, and every error surface offers to copy it.

---

## 12.9 Email templates

Plain text, sent from the instance's configured address. Every email is addressed to one person
and none of them contain tracking, images, or an unsubscribe link that is not a real settings
link. Times are absolute UTC with the relative form in parentheses, matching the dashboard.

Every share-link email states the artifact, the absolute expiry, and carries a one-click revoke
URL. That is the point of them: the owner should be able to end an unwanted disclosure from
their phone, in bed, without signing in to look for it first.

---

**`link_created`** — a share link was created

> **Subject:** Share link created for {name}
>
> A share link was created for {name} ({title}).
>
> Created by: {actorName}
> Expires:    {expiry} ({relative})
> Password:   {set / not set}
> Label:      {label / none}
> Link:       {url}
>
> Anyone holding that URL can view this artifact until it expires, without signing in.
>
> Revoke it now: {revokeUrl}
> Manage sharing: {shareUrl}
>
> You are getting this because share-link notifications are on. Turn them off: {settingsUrl}

---

**`link_expiring`** — 24 hours before a link expires

> **Subject:** Share link for {name} expires tomorrow
>
> The share link "{label}" for {name} expires {expiry} ({relative}).
>
> After that, anyone opening it sees only that the link is no longer active.
>
> Extend by 14 days: {extendUrl}
> Choose another duration: {shareUrl}
> Revoke it now: {revokeUrl}

---

**`link_ended`** — a link expired or was revoked

> **Subject:** Share link for {name} has ended
>
> The share link "{label}" for {name} is no longer active as of {endedAt}.
>
> Reason: {expired / revoked by {actorName} / view limit reached}
> Views while it was live: {count}
>
> {name} is now {private / still reachable through {count} other live links}.
>
> Create a new link: {shareUrl}

---

**`artifact_expiring`** — an artifact with live shares expires in 24 hours

> **Subject:** {name} expires tomorrow and its links will stop working
>
> {name} has an expiry set for {expiry} ({relative}). When it passes, the artifact moves to your
> trash and its {count} live share links stop working. It stays restorable for 30 days.
>
> Keep it and clear the expiry: {keepUrl}
> Change the expiry: {artifactUrl}

---

**`quota_warning`** — 80% or 95% of quota

> **Subject:** Storage is {percent} full
>
> You are using {used} of your {quota} storage limit.
>
> At 100%, posting is refused. Reading, sharing, and deleting keep working, so you can always
> dig out.
>
> What would free space:
>   Trash                          {trashBytes}
>   Not opened in {days} days      {staleBytes}
>   Old versions (estimate)        {versionBytes}
>
> Manage storage: {storageUrl}
>
> These warnings are sent at most once a day.

---

**`token_created`** — an API token was created

> **Subject:** API token created: {tokenName}
>
> A new API token was created on your account.
>
> Name:    {tokenName}
> Prefix:  {displayPrefix}
> Scopes:  {scopes}
> Created: {createdAt} by {actorName}
>
> {This token cannot create share links. / This token CAN create share links, which means it can
> make your artifacts reachable by anyone with a URL.}
>
> If this was not you, revoke it now: {revokeUrl}

---

**`token_first_link`** — a token created its first-ever share link

> **Subject:** {tokenName} created its first share link
>
> The agent token {tokenName} has created a share link for the first time.
>
> Artifact: {name}
> Expires:  {expiry} ({relative})
> Link:     {url}
>
> You are told about this once per token, because the first time an agent puts something within
> reach of the internet is worth noticing.
>
> Revoke this link: {revokeUrl}
> Review this token's scopes: {tokenUrl}

---

**`anomaly_link_rate`** — unusual share-link creation rate

> **Subject:** {tokenName} created {count} share links in an hour
>
> {tokenName} created {count} share links between {from} and {to}. The threshold for this notice
> is 5 an hour, and the hard ceiling is 20.
>
> Artifacts affected: {names}
>
> Nothing was blocked beyond the hourly ceiling.
>
> Revoke every share link on your account: {panicUrl}
> Revoke this token: {revokeTokenUrl}
> See the audit log for this token: {auditUrl}

---

**`anomaly_trash_rate`** — unusual trash rate

> **Subject:** {tokenName} moved {count} artifacts to the trash in an hour
>
> {tokenName} moved {count} artifacts to the trash between {from} and {to}.
>
> Nothing is lost. Trashed artifacts stay restorable for 30 days, and this token cannot delete
> anything permanently.
>
> Review the trash: {trashUrl}
> Revoke this token: {revokeTokenUrl}

---

**`recovery_used`** — a recovery code was used

> **Subject:** A recovery code was used on your account
>
> A recovery code was used to sign in at {time}, from {ip}.
>
> That session can do exactly two things: list your passkeys and register a new one. It ends
> after 30 minutes. Every other recovery code is now invalid, and a new one was issued to
> whoever used it.
>
> If this was you, nothing more is needed.
>
> If it was not, sign in with a passkey and revoke every session and passkey you do not
> recognize: {securityUrl}
>
> This notice cannot be turned off.

---

**`counter_regression`** — passkey signature counter went backwards

> **Subject:** A passkey on your account reported an unexpected use count
>
> The passkey "{passkeyName}" was used at {time} from {ip} and reported a lower use count than
> Share last recorded. That can mean the credential has been copied, and it can also happen with
> some authenticators after a restore.
>
> The sign-in was refused. Nothing was revoked automatically.
>
> Sign in with a different passkey and revoke this one: {securityUrl}
>
> This notice cannot be turned off.

---

**`auth_failures`** — repeated authentication failures from one address

> **Subject:** Repeated failed sign-ins from {ip}
>
> {count} failed authentication attempts came from {ip} in the last hour. Nothing succeeded.
>
> Share has no password to guess and no reset flow to abuse, so this is usually noise from a
> scanner. It is worth a look if the address is one you recognize.
>
> Recent sign-in activity: {securityOverviewUrl}
>
> At most one of these is sent per hour.

---

**`backup_failed`** — instance backup failed (root user)

> **Subject:** Backup failed on share.c52.com
>
> The backup job failed at {time}.
>
> Last successful backup: {lastSuccess} ({relative})
> Error: {shortError}
>
> Artifact bytes on this instance are not backed up anywhere else until this succeeds.
>
> Check the instance status: {statusUrl}
> On the server: `sharectl backup --verbose`

---

**`disk_warning`** — instance disk over 85% (root user)

> **Subject:** Disk is {percent} full on share.c52.com
>
> {free} free of {total}.
>
> At 100% Share refuses new posts with disk_full and keeps serving what is already there.
>
> Largest contributors: trash across all users {trashBytes}, unreferenced files awaiting
> collection {orphanBytes}.
>
> Instance status: {statusUrl}
> On the server: `sharectl collect --now`

---

**`invite`** — an invitation to join the instance

> **Subject:** {inviterName} invited you to Share at share.c52.com
>
> {inviterName} has created an account for you on share.c52.com, a private place where finished
> work gets kept and handed out.
>
> Your handle will be {handle}, and your space will be share.c52.com/~{handle}.
>
> Accept the invite: {inviteUrl}
>
> This link is good until {expiry} ({relative}).
>
> There is no password to choose. You will register a passkey — your device, your phone, or your
> password manager — and get a recovery code to store somewhere safe. Nothing you post is
> reachable by anyone else unless you create a share link for it.

---

**`device_authorization`** — an agent asked for a token

> **Subject:** {agentName} is asking for access to your account
>
> An agent identifying itself as {agentName} started a device authorization at {time} from {ip}.
>
> It is asking for a token that can read and post artifacts in your space. It will not be able to
> create share links.
>
> Approve or deny: {authorizeUrl}
> Code: {userCode}
>
> The request expires in 10 minutes. If this was not you, do nothing — an unapproved request
> issues no token.

---

## 12.10 FAQ

### Getting started

**What is an artifact?**
One finished thing at one address: a PDF, a rendered page, an image, a video, or a bundle of
files that belong together. It has a name, a URL, a version history, one sharing state, and one
entry in the trash if you delete it.

**Do I have to use an agent?**
No. **Upload** in the top bar takes a file or a whole folder, keeps the folder's structure, and
gives you the same artifact an agent would have posted. The CLI works the same way from a
terminal. The MCP endpoint is the path the documentation leads with because it is the one with
nothing to install, not because the others are second class.

**Where does my artifact live?**
At `share.c52.com/{name}` if you are the root user, and `share.c52.com/~{handle}/{name}`
otherwise. That address is stable: post to the same name next week and the URL does not change.

**Why is there no sign-up page?**
Because accounts exist only because the operator created them. If you need an account, ask the
person running the instance to invite you.

### Privacy and sharing

**Is my content encrypted?**
On disk, by full-disk encryption on the server, and in backups, which are encrypted before they
leave the machine. Not application-layer encrypted — the bytes have to be readable by the server
to be served to a browser, so anyone with root on the box or physical access to an unlocked disk
can read them. That is stated plainly rather than buried: the protection against the hosting
provider is disk encryption, and the protection against everyone else is that there is no way in
without a passkey or a link.

**Can someone guess a share link?**
No, in the sense that matters. A share token is 128 bits of randomness from a cryptographic
generator, base58-encoded to 22 characters. There is no listing, no directory, no enumeration
endpoint, and no way to ask whether a token exists other than trying it, which is rate limited.
The realistic risk is not guessing — it is forwarding, which is why every link expires.

**What happens when a link expires?**
Anyone opening it sees one page: "This link is no longer active." No artifact name, no owner, no
date, no reason. Every recipient session on that link is deleted, so someone with the page
already open loses access on their next request. Expired, revoked, burned through a view limit,
and deleted are indistinguishable from outside. Your artifact is untouched — only that one link
ended.

**Can I make a link that never expires?**
No. Not through the dashboard, not through the API, and not through a configuration flag. If
something needs to be readable indefinitely by a specific person who has an account here, grant
it to them instead — grants do not expire and there is no URL to forward.

**Why can't my agent share things?**
Because posting and publishing are different decisions and only one of them should be automatic.
An agent token gets `artifacts:read` and `artifacts:write`, never `share:create`. It can post
and overwrite all day and cannot make any of it reachable from the internet. Asked to share, it
fails with `insufficient_scope`, names the scope, and should hand you a dashboard link. You can
grant `share:create` deliberately if an agent genuinely needs it; you will be emailed every time
it uses it.

**Does Share read my files?**
No. Not for search, not for titles, not for summaries, not for thumbnails, not for classifying,
not for guessing a video's dimensions. There is no code path that opens the contents of an
artifact for any purpose other than serving those exact bytes to someone authorized to receive
them. The cost is that you cannot search inside your files. The benefit is that there is no
extracted index of your clients' numbers sitting anywhere.

**Can the operator see my artifacts?**
The operator has root on the machine, so yes, in the sense that anyone with root on any server
can read what is on it. What they cannot get from the database is who viewed what: view records
hold a salted daily hash that cannot be recomputed after the day rolls over. And there is no API
by which any account, root included, lists or reads inside another user's space.

**Do search engines index this?**
No. Every response carries `X-Robots-Tag: noindex, nofollow`, and `robots.txt` denies everything
with no per-artifact override. An indexed share link would defeat link entropy entirely.

**What can a recipient see about me?**
The hostname. Not your handle, not the artifact's name if you reached them through a share link,
not your email, not how many other artifacts you have, and not whether the link is about to
expire. The password gate, in particular, names nothing at all.

### Posting and organizing

**What happens if I post to a name that already exists?**
You get a new version at the same URL. Title, description, tags, TTL, pinned state, share links,
and grants all survive; only the files change. The previous version stays complete and
restorable, and unchanged files are not re-uploaded.

**What if I delete something an agent needed?**
Deleting moves it to the trash, where it sits for 30 days. During that time its URL returns 404
and the API reports `artifact_not_found`, so an agent will fail rather than get stale content —
restore it and everything works again. What restoring does not bring back is its share links and
grants: trashing revoked them, and undoing a deletion should not silently re-open access. If the
agent needs a specific old version rather than the whole artifact, restore the version instead,
which creates a new version rather than rewinding history.

**Can I get an old version back?**
Yes. Every post keeps the previous version, the default retention is the last 20 or 365 days
(never fewer than 3), and pinned versions are never pruned. Restoring one creates a new version
with the old files, so nothing is lost either way.

**Why can't I search inside my documents?**
Because nothing reads them. Put the words you would search for into the name, title,
description, and tags at the moment you post. Matching is trigram-based, so partial words and
typos still find things.

**Why did my artifact show a file listing instead of my page?**
No file answered at its root. Share looks for the `entryPath` you supplied, then `/index.html`,
then a single HTML file, then a single file of any kind. If none applies you get a listing and a
`no_entry_point` warning. Set an entry file on the Files tab — it takes effect immediately,
without posting again.

**Can I use folders?**
Slashes in names give you the same effect: `q3/market-report` is one artifact whose address has
a slash in it. There are no folder objects to create, move, or delete.

**How much does version history cost me?**
Almost nothing. Identical files are stored once for the whole instance, so twenty versions of a
page whose CSS never changes hold one copy of that CSS. You are charged for what your artifacts
reference, which is why your storage figure will not match a naive sum of file sizes.

### Agents

**How do I connect an agent?**
Create a token, paste one JSON block into your MCP host's configuration, restart it. The
connecting-agents page has ready-made blocks for Claude Code, Cursor, Codex, and generic hosts,
each with this instance's hostname already filled in.

**Can I use this from CI?**
Yes, and it is a documented pattern: put a token in the runner's secret store as `SHARE_TOKEN`,
use `--yes` so a prompt in a non-TTY is an error rather than a guess, and post with
`share post ./out --name preview-$BRANCH --ttl 30d` so every branch gets a stable private URL
that cleans itself up. Do not use `--link` from CI. A pipeline that can create share links is a
pipeline whose compromise creates share links.

**What is the worst a compromised agent token can do?**
Fill your space with junk and fill your trash. It can post, overwrite, and trash, all of which
are reversible: overwrites keep versions, trashing is undoable for 30 days. It cannot delete
permanently without `artifacts:delete`, cannot create a share link without `share:create`, and
cannot touch any space but yours — there is no parameter anywhere in the API that names a
different owner. Every action it takes is audited with its token ID and source address, and
unusual rates raise an email within fifteen minutes.

**Do agents count against my rate limits?**
Yes, per token and per user. The one worth knowing is share-link creation: 20 an hour per user,
which is far above human use and far below what a compromised agent would want. Exhausting it
sends you an email as well as returning 429.

**Can an agent read the artifacts it posted?**
Yes, with `artifacts:read`: `share_read_file` and the files endpoint return contents to a token,
which is also the only way to read the bytes of a password-protected artifact without the
password. Nothing about that involves indexing — a specific file is fetched on request.

### Running it

**What if I lose my passkeys?**
Three layers, in order. A second passkey on another device makes it a non-event, which is why
setup pushes it. Failing that, your recovery code gives you one 30-minute session that can do
exactly one useful thing: register a new passkey. Failing that, the instance is a machine you
control, and `sharectl grant-session --email you@… --minutes 30` on the server prints a one-time
sign-in URL. There is no recovery-by-email-link, because that would reintroduce exactly the
bypass that removing passwords eliminated.

**What happens if I go over quota?**
Posting fails with `quota_exceeded`, returned before any bytes move, with your current,
projected, and limit figures. Reading, downloading, sharing, and deleting keep working. Empty the
trash first — it holds full artifacts and is charged in full.

**Can I add other people?**
The root user can invite them. Each gets their own space, their own quota, and their own tokens.
There are no teams, roles, or shared folders: cross-space access is per-artifact grants and
nothing else.

**What if the server goes down?**
You get a static maintenance page with no timestamp and no auto-refresh. Nothing is lost;
in-flight uploads may need re-running, which is cheap because the files already sent are still
on the server. This is a single-server system by design, and no high availability is claimed.

**Something looks wrong. What do I do first?**
Open the security overview. The first card answers the question that matters — everything of
yours currently reachable without a sign-in, with its expiry. If the answer is wrong, **Revoke
all share links** ends every one of them at once, and revoking the token involved is one click
from the anomaly row.
