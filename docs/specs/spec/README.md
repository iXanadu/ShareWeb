# Share — specification folder

This folder is what goes to the developers. It is a re-cut of the sixteen-part draft, not a
rewrite: the content is the same content, moved so that no two documents own the same decision.

## Why it was re-cut

The draft specified the product twice. Part 11 described every screen's layout in prose and
ASCII diagrams; Part 13 was a complete 2,100-line design system specifying the same layouts down
to the hex value. They disagreed in about a dozen places, and neither was the obvious winner,
because neither should have been writing those sentences alone.

Worse, Part 13 invented a design system for a project that already had one. Broadsheet is the
house visual system. A specification is not the place to author a competing one.

So the boundary moved:

- **This folder owns behaviour.** What screens exist, what is on them, where the data comes from,
  what states they have, what each control does, what every error means, and what the product
  requires of its own appearance in order to be safe.
- **The design work owns appearance.** Colour values, type, spacing, dimensions, component
  anatomy, motion. That lives in the design project on Broadsheet, and it is authoritative there.

Nothing was deleted for the sake of brevity. What left Part 11 and Part 13 left because it was
being decided in two places at once.

## Precedence

One rule, and it applies to every disagreement anyone finds:

> **The spec is authoritative on presence and behaviour. The design is authoritative on
> appearance.** If the disputed thing is a value — a colour, a size, a weight, a space, a radius,
> a duration — the design wins. If it is a rule about what exists, when it appears, or what it
> does, the spec wins.

Where the spec must constrain appearance for a reason that is not aesthetic — the sharing state
must be legible without colour, a recipient page must not be identifiable by its stylesheet — it
says so in Part 13 as a requirement, and the design satisfies it however it likes.

Part 16 already worked this way for phase membership. Same rule, wider scope.

## What is in here

| File | Status | Owner |
| --- | --- | --- |
| `01-overview.md` | Unchanged | Everyone |
| `USE-CASES.md` | **New** — the document the draft did not have | Everyone |
| `START-HERE.md` | **New** — the handoff brief. First thing anyone reads | Everyone |
| `PLUMBING-AUDIT.md` | **New** — Parts 2–10, 14, 15 audited; its fixes are applied | Everyone |
| `02-architecture.md` | Audited, fixes applied | Backend, ops |
| `03-data-model.md` | Audited, fixes applied | Backend |
| `04-identity.md` | Audited, fixes applied | Backend, frontend |
| `05-artifacts-api.md` | Audited, fixes applied | Backend, agents |
| `06-urls-serving.md` | Audited, fixes applied | Backend |
| `07-sharing.md` | Audited, fixes applied | Backend, frontend |
| `08-versions-trash-search.md` | Audited, clean | Backend |
| `09-agent-surface.md` | Audited, clean | Agents |
| `10-limits-audit.md` | Audited, fixes applied | Backend, ops |
| `11-screens.md` | **Re-cut** — behaviour, data, and states; layout prose removed | Frontend, design |
| `12-copy.md` | Unchanged. Copy is specification | Frontend |
| `13-design-system.md` | **Re-cut** — from 2,130 lines to the requirements only | Design |
| `14-testing.md` | Audited. §14.24 is required reading beside Parts 2–10 | All |
| `15-ops.md` | Audited, clean | Ops |
| `16-roadmap.md` | Unchanged | Everyone |
| `inventory.md` | Unchanged. Screen numbering is still the join key | Everyone |
| `DECISIONS.md` | **New** — the resolutions, per §1.9 | Everyone |

The audit is done and its fixes are in. Parts 2–10 came out well — the access model has no hole, the privacy guarantees
hold at the schema level, and Part 14 §14.24 had already found and resolved nineteen
contradictions before anyone asked. `PLUMBING-AUDIT.md` carries the five things that will bite, the
seven resolutions that were only half-applied, and the one real gap: **the dashboard's own API is
not specified anywhere**, so Part 11 currently defines it by implication. That wants a new Part 5A
before the first sprint.

**One document still to write, and it belongs to the build team.** `05a-dashboard-api.md` — the
endpoints and shapes the dashboard calls, written alongside the code. Audit §2 lists them; §5.13 of
Part 5 states the four that are constrained rather than free.

## Reading order

**Everyone starts at `START-HERE.md`** — what the product is, the five things that shape how it
feels to build, the first week, and what is deliberately out of scope.

**A developer starting the build** reads `01-overview.md` for the privacy model, `USE-CASES.md`
to know what they are building, `16-roadmap.md` for what to build first, then the parts their
phase touches.

**A frontend developer** reads `11-screens.md` for behaviour and `12-copy.md` for words, and takes
appearance from the design output. Where the two seem to disagree, the precedence rule above
settles it without a conversation.

**Anyone who finds an ambiguity** applies §1.9 and records it in `DECISIONS.md`. That rule was
right in the draft and it is still right.
