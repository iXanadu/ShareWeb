# Part 13 — Visual requirements

This part used to be a design system. It is not one any more, and it should never have been one:
the project it was written for already had a visual system, and a specification that authors a
second one produces exactly the contradictions catalogued in `DECISIONS.md`.

**The visual system is Broadsheet.** Colour values, type, spacing, dimensions, radii, elevation,
component anatomy and motion are decided in the design work and are authoritative there. This part
does not restate them and must never restate them — a value written twice is a value that drifts.

What remains here is the short list of things the *product* requires of its appearance for reasons
that are not aesthetic. These are requirements, not treatments. The design satisfies each one
however it likes, and Part 14 tests them.

**Where the design work lives.** `Foundations.dc.html` at the project root names every value this
part refuses to name, section by section, numbered to the clauses below. `Screens.dc.html` holds the eleven Phase 1 screens at 1440×900, every
string verbatim from Part 12. `recipient/` holds R1–R7 as ten complete HTML documents, ready to serve, with the shared style block and its constraints
explained in `recipient/README.md`. Five decisions the design had to make are recorded as D-14 to D-18 — including the seven
marked departures from Broadsheet's component layer, which are the only ones sanctioned.

Screen references use the canonical numbering in `inventory.md`.

---

## 13.1 The three sharing states

§7.8 derives exactly one of these for every artifact at every moment. They are the most important
distinction in the product and the reason this part still exists.

| State | Derived when | Word |
| --- | --- | --- |
| `private` | No live links, no live grants | **Private** |
| `granted` | Live grants, no live links | **Shared with *n* people** |
| `shared` | At least one live link | **Link active** |

Requirements on their appearance:

1. **Three visually distinct treatments**, distinguishable at a glance and across a room, without
   reading a sentence.
2. **Distinguishable without colour.** Each state carries its own shape or glyph as well as its own
   colour, and each carries its word. A greyscale screenshot, a printout, and a photograph of a
   laptop in sunlight must all still answer "who can reach this".
3. **Distinguishable under protan, deutan and tritan deficiency.** The three must differ in
   lightness and in warm-versus-cool, not only in hue. Green-versus-red does not survive this and is
   not used for state anywhere in the product.
4. **`private` must not read as success.** It is the default and the quiet state; it must not look
   like "deployed OK".
5. **`shared` must not read as an error.** A live link is a deliberate act by its owner, not a
   fault. Red is reserved for destructive actions and failures and never appears on a sharing-state
   indicator.
6. **`shared` is the attention-getting one.** Of the three it is the one that warrants a second
   look, and its treatment says so.
7. **One component, one appearance, everywhere.** The list, the detail header, search results, the
   viewer, shared-with-me, the trash, and the create-link summary all render the same thing.
   Inconsistency between two of them is a privacy bug, not a polish bug.

Its warm treatment is exclusive to it. See 13.3.

## 13.2 Never colour alone

Every state renders as **colour, icon and word** — all three. The word is never dropped to save
space.

One reduction is permitted: an icon-only variant, in a container genuinely too narrow for the
word, which requires an accessible label, a tooltip, and the same fact rendered as text elsewhere
in the same row.

Modifier chips — a link expiring within 48 hours, a link carrying a password, an expired link, a
trashed artifact — are modifiers rather than states, and on narrow viewports they may collapse into
the plain-text expiry line the row already carries (D-03). **The state badge itself never
collapses, at any width.** Density is a preference; this is a guarantee.

## 13.3 Warm colour means one thing

The warm treatment used by `shared` and its expiring modifier appears nowhere else in the product.
Advisory and warning banners do not use it. Errors and destructive actions use the product's red.

The draft shared a hue family between "link active" and "warning" on the grounds that both mean
"wants your attention". That reasoning does not survive a warning banner sitting directly above a
link-active badge, so it is withdrawn (D-02). One warm colour, one meaning: **someone holding a URL
can reach this.**

## 13.4 Identifiers are literal

Artifact names, share-link prefixes, IDs, hashes and file paths are monospace, selectable, always
paired with a copy control, and never prettified, title-cased, truncated by CSS, or replaced by a
friendly label.

This follows from P5. The product never infers anything from a file's contents, so the real
identifier is all there is, and the design's job is to make it comfortable to read rather than to
hide it behind one we invented.

An artifact with no `title` shows its `name` in the title position, in the same weight, with no
placeholder and no guess.

## 13.5 An operator's console, not a marketing site

Density is a feature. This is a tool someone may look at for eight hours; the target is a screen
that does not become tiring or shouty.

Not present anywhere in the chrome: hero sections, illustrations, decorative imagery, photography,
gradients, glass, decorative icons, animated numbers. The design owns every dimension and every
value; this clause only says what the product is not.

## 13.6 The chrome must never compete with the artifact

Everything in this product exists to frame content whose colours, type and contrast are not ours
and cannot be predicted — somebody's rendered PDF, a photograph, a video, another agent's HTML.

- The shell is monochrome; colour on screen carries state.
- The viewer (11.9) reduces chrome to a single bar over a neutral mat.
- No chrome colour, border or shadow sits immediately against rendered artifact content.
- **No dashboard style ever reaches an artifact.** Bundles render in an isolated iframe with no
  inherited stylesheet.

## 13.7 Both themes

Light and dark are both required, and every rule in this part holds in both. A viewer's explicit
choice beats their operating system's preference. `body` always paints its background and text
colour explicitly, because a recipient-facing page inherits nothing from us.

## 13.8 The recipient-facing pages

R1–R7 are complete HTML documents with **inline CSS, no JavaScript, no external requests, and no
dashboard chrome**. Beyond that, three requirements are security requirements rather than style
ones:

1. **The style block is byte-identical across R1–R7.** Page identity must not be inferrable from
   CSS differences. This is what makes R4's blanket 404 (P1) hold against an attacker comparing
   responses.
2. **No webfont, and no external asset of any kind.** A blocked font must not change the page.
   R6 in particular is a static file that must render with Postgres, Redis and the API all gone.
3. **Legible at 320px wide, at 200% zoom, and with author styles disabled.** Which follows from
   each page being a heading, a paragraph, and at most a form.

None of these pages links to the dashboard, names the instance's owner, or reveals an artifact's
name to a visitor not already authorised to see it.

## 13.9 Accessibility floor

WCAG 2.2 AA, with the product-specific requirements in §11.30 — which are behavioural and stay
there. Contrast: text at 4.5:1, large text and UI boundaries at 3:1, focus rings at 3:1 against
both the element and its background. Keyboard focus is always visibly styled and never left to the
browser's default.

## 13.10 Where the rest of this part went

For anyone who read the draft and is looking for something specific:

| Draft content | Now |
| --- | --- |
| Colour tokens, ramps, dark-mode generation | `Foundations.dc.html` § colour roles; D-14, D-17 |
| Type scale, font pairing | `Foundations.dc.html` § type and density |
| Spacing, radii, elevation | `Foundations.dc.html` § type and density |
| Component anatomy — buttons, tags, fields, cards, tables, dialogs | `Foundations.dc.html` § component anatomy |
| Sharing-state indicator's exact colours, glyphs and variants | 13.1–13.3 as requirements; the treatment is `Foundations.dc.html` § the three sharing states |
| Density figures, row heights, dialog widths, sidebar and bar dimensions | `Foundations.dc.html` § type and density |
| `design/tokens.json` and the generation pipeline | Not a spec concern |
| The three sharing states' meanings and derivation | 13.1, and §7.8 |
| "Never colour alone" | 13.2 |
| "Identifiers are literal" | 13.4 |
| The recipient pages' inline-CSS constraints | 13.8 |

If something is missing from both this part and the design work, §1.9 applies: resolve toward the
interpretation that exposes less and adds no configuration surface, and record it in
`DECISIONS.md`.
