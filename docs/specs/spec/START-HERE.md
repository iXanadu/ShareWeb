# Start here

> Historical briefing. It is not the on-ramp. New developers start at the
> repo [README](../../../README.md). Open work is [BACKLOG.md](../../../BACKLOG.md).

You are building **Share**: a self-hosted place where an owner's AI agents post finished files
over an API and get back a stable URL, and the owner hands those files to other people with links
that expire. It runs on one VM. Nothing reads the contents of a file, ever.

That is the whole product. Everything in this folder serves it.

## Read these three first, in this order

1. **`01-overview.md`** — the privacy model and the nine numbered guarantees, P1–P9. Every one of
   them shows up later as a schema constraint or a test, so they are not a manifesto.
2. **`USE-CASES.md`** — nineteen flows end to end, each with a line saying what must be true when
   it finishes. That line is the acceptance criterion.
3. **`16-roadmap.md`** — four phases with testable exit criteria. Phase 1 is genuinely shippable:
   an agent posts, the owner opens it from a phone.

Twenty minutes, everyone, before any code. Then read the parts your phase touches.

## The one rule about which document wins

> **The spec owns presence and behaviour. The design owns appearance.** If the disputed thing is a
> value — a colour, a size, a weight, a space, a duration — the design wins. If it is a rule about
> what exists, when it appears, or what it does, the spec wins.

`README.md` has the folder map and the rest of this. Where the spec constrains appearance for a
reason that is not aesthetic — a sharing state must be legible without colour, a recipient page
must not be identifiable by its stylesheet — it says so in Part 13 as a requirement, and the design
satisfies it however it likes.

## What this folder has been through

The draft specified the product twice: Part 11 described every screen's layout in prose, and Part
13 was a 2,100-line design system specifying the same layouts down to the hex value, for a project
that already had a visual system. They disagreed in about a dozen places.

Both were re-cut. Part 11 keeps behaviour and lost its layout prose; Part 13 went from 2,130 lines
to the visual requirements the product genuinely imposes. Then Parts 2–10, 14 and 15 were audited
against each other — see `PLUMBING-AUDIT.md` — and came out well. The five defects that audit found
are **already fixed in the files you have**; the audit is still worth reading, because §7 says what
to hand whom and §6 says what was specifically looked for and not found.

Two things follow from this history:

- **`DECISIONS.md` is the live document.** Thirteen entries, each stating a conflict, its
  resolution, and what the resolution cost. When you find an ambiguity — and you will —
  §1.9 applies: resolve toward the interpretation that exposes less and adds no configuration
  surface, then add an entry. Do not resolve one silently.
- **Do not rewrite Parts 2–10.** They are better than the Part 13 episode suggests. The access
  model has four cases and no bypass; the privacy guarantees hold at the schema level, not by
  convention.

## The five things that will shape how this feels to build

**1 · Posting is not publishing.** A fresh post is always private. Sharing is a separate call with
a separate scope, and agent tokens do not hold it by default. The product says this in three
places (§9.6) because it is the assumption an agent gets wrong.

**2 · Widening access takes a dialog; narrowing it takes a click.** Creating a share link is a
deliberate multi-step flow with a read-back and a terminal success state (§11.13). Revoking is one
click and a confirm. Never normalise that asymmetry away — it is the product's spine.

**3 · Everything an agent does is reversible and attributed.** Versions make overwrites
recoverable, trash makes deletes recoverable, and every write carries a token ID and a source IP.
This is the only reason full agent autonomy is acceptable (§8.1). If a change makes something
irreversible or unattributed, it is a design change, not an implementation detail.

**4 · A thing you cannot see is indistinguishable from a thing that never existed.** Same body,
same headers, comparable timing (P1, §6.5.2). This is why `/internal/authorize` returns only
`200`, `404`, `429` or `503` and never a `401`.

**5 · Nothing reads a file.** `kind` comes from the manifest's shape. Search is trigrams over
metadata. There is no thumbnail, poster frame, transcode, or probe anywhere. The cost is real —
you cannot find a phrase inside a PDF — and it is the trade this instance is making on purpose.

## Your first week

Phase 1, from §16.2. In dependency order:

1. **The install and the schema.** Part 15's playbook, Part 3's migration. Get
   `/internal/ready` green before anything else exists.
2. **`/internal/authorize` and the Caddyfile.** §2.4 and §6.5. This is the riskiest part of the
   whole project and everything else sits on it. `can_view` is four lines; keep it four lines.
3. **Passkeys.** §4.2–4.4, with a real software authenticator in the tests from day one. Never
   assert sign-in by inserting a session row (§14.2.7).
4. **The three-phase post.** Part 5. `seq` is assigned at commit under a row lock, not at declare.
5. **Trash and restore.** §8.4, including the asymmetry: restoring does not bring share links back.
6. **Then the screens** — 11.1, 11.3, 11.5, 11.6, 11.7, 11.8, 11.15, 11.18, 11.19, 11.26, 11.27.

**Phase 1 cannot ship without T-PRIV-01.** Serving artifacts on a public hostname before
indistinguishability holds is the one failure this product cannot recover from.

## The design work, and where it sits

Part 13 states what the product requires of its appearance and names no values, so that no value is
written twice. The values are in two places outside this folder, both ready to use:

- **`Foundations.dc.html`** — the sharing-state badges with their exact fills, borders, inks and
  glyphs in both themes, the greyscale and colour-deficiency proofs, the identifier treatment, the
  colour roles, the type scale, the density metrics, and the component anatomy for buttons, focus,
  the artifact row and the create-link dialog. Every section is numbered to the Part 13 clause it
  satisfies.
- **`recipient/`** — R1–R7 as ten complete HTML documents you can serve unchanged. Read
  `recipient/README.md` first: the style block is byte-identical across all ten, and that is a
  security requirement (13.8.1), not a tidiness one. It is one template constant. Do not prune it
  per page and do not let a build step reorder it for one route.

- **`Screens.dc.html`** — the eleven screens item 6 builds (11.1, 11.3, 11.5, 11.6, 11.7, 11.8,
  11.15, 11.18, 11.19, 11.26, 11.27) at 1440×900, cross-linked, every string verbatim from Part 12.
  Phase 2's screens are not drawn; the create-link dialog's anatomy is settled in `Foundations`
  because it is the product's spine.

## The one document still to write, and it is yours

**`05a-dashboard-api.md`.** Parts 4–10 specify the agent-facing API exhaustively and the
dashboard-facing one barely — nine endpoints and four response shapes that Part 11 currently
defines only by implication. `PLUMBING-AUDIT.md` §2 lists them all.

Write it as you build it. But read **§5.13 first**: four of those shapes are constrained, because a
screen's honesty depends on what they return — the `settings` keys and their defaults, what
`GET /status` must report, what a share-link list must carry, and what an activity entry may never
contain. Those are requirements. Everything around them is yours.

## How you will know you are done

`14-testing.md`, and its release gate as written:

> Every `T-PRIV-*` and every `@security` test passes, coverage thresholds are met, and the manual
> checklist is signed off with a date and a name.

Two things in that part are worth internalising early because they are cheap now and expensive
later. **The negative-case rule** (§14.1.3): every endpoint carries three mandatory negative tests
— unauthorised, malformed, and wrong-actor-class. And **§14.24**: nineteen ambiguities found while
writing the tests, each resolved with its reasoning. Read it beside Parts 2–10, not after them, or
you will re-derive several of them yourself.

## What is deliberately not in scope

Not a phase, not a flag, not a future consideration:

- Permanent share links. `expires_at` is `NOT NULL` with a `CHECK`, and there is no config escape.
- Anonymous posting. This is the thing the instance exists to not have.
- Running code on the server. Share serves static artifacts. No runtime, no build step, no API
  proxying — which is why there is no SSRF surface to defend.
- Content-derived anything: no generated titles, summaries, thumbnails, or classifications.
- Custom domains, a second region, public sign-up, or a permission matrix. Spaces are hard
  boundaries and there are no roles.

If a requirement seems to need one of these, that is the signal to stop and ask rather than
implement.
