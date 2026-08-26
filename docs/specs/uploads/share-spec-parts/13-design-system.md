# Part 13 — Design System: Tokens, Type, Components

This part is the visual contract. Part 11 says which screens exist; Part 12 says what words
appear on them; this part says what everything looks like, down to the hex value. Two agents
rendering the same Part 11 screen from these tokens should produce the same screen.

Nothing here is advisory. An implementer who needs a token that does not exist adds it to
`design/tokens.json` (§13.11.2) and records the addition per §1.9 — they do not inline a raw
value.

Screen references use the canonical numbering in `inventory.md`: dashboard screens are 11.1–11.28,
recipient-facing and error pages are R1–R7.

---

## 13.1 Design principles

**D1. Sharing state is the loudest thing on the screen.**
On any surface that represents an artifact, *"who can reach this right now?"* must be legible
in under a second, from across a room, without reading a sentence. The sharing-state indicator
(§13.6.8) is deliberately the most over-specified component in this document because it appears
in at least a dozen places, and any inconsistency between two of them is a privacy bug, not a
polish bug. It owns a colour set, an icon set, a word set, and its own placement rules. Nothing
else may borrow that language: no other badge is teal, no other badge is amber-gold in `solid`,
and no other component uses the lock / users / link-2 triad.

**D2. This is an operator's console, not a marketing site.**
Density is a feature. The default table row is 40px and 32px is one click away. There are no
hero sections, no illustrations, no gradients, no glass, no photography, no decorative icons,
and no animated numbers. Borders are 1px hairlines; shadows exist only to say that something
floats above the page. The reference points are a well-made admin console and a good terminal.
The target is a screen someone can look at for eight hours without it becoming tiring or
shouty.

**D3. The artifact is the content; the chrome must never compete with it.**
Everything in this system exists to frame a rendered PDF, a photograph, a video, or somebody
else's HTML — content whose colours, type, and contrast are not ours and cannot be predicted.
So the shell is monochrome, colour on screen always carries state, and the viewer (§13.5.4)
reduces the chrome to a single 48px bar over a neutral mat. No chrome colour, border, or shadow
may sit within 8px of rendered artifact content, and no dashboard style ever leaks into an
artifact frame — bundles render in an isolated `iframe` with no inherited stylesheet.

**D4. Never colour alone.**
Every state renders as **colour + icon + word**, all three, in that order. Private is a teal
chip with a lock and the word "Private". The word is never dropped to save space; if the space
is not there, the layout is wrong. The one permitted reduction is the `dot` variant of the
sharing-state indicator (§13.6.8.5), which requires an `aria-label`, a tooltip, and the same
fact rendered as text elsewhere in the same row. This rule serves colour-vision deficiency,
greyscale printing, screenshots pasted into a chat window, and a laptop screen in sunlight.

**D5. Widening is a dialog; narrowing is a click.**
A control's interaction weight is proportional to how much it could expose. Creating a share
link takes a dialog, an explicit expiry, a deliberate password choice, and a button that names
the act. Revoking one is a single click with no confirmation — the safe direction is never
obstructed. Destructive-but-not-widening acts (delete an artifact, revoke every token, remove a
user) get the typed-confirmation dialog in §13.6.27. This asymmetry must not be normalised away
in the name of consistency.

**D6. Identifiers are literal.**
Artifact names, share tokens, IDs, hashes, and paths are monospace, selectable, always paired
with a copy control, and never prettified, title-cased, CSS-truncated, or replaced by a friendly
label. Per P5 (§1.6.3) this product never infers anything from a file's contents; the design
system's job is to make the real identifier comfortable to read, not to hide it behind one we
invented.

---

## 13.2 Colour tokens

### 13.2.1 Structure

Three layers, in this order, and no other:

1. **Bare `:root`** carries the complete light palette. Every token is defined here once, with a
   real value. No token gets its only definition inside a media query.
2. **`@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { … } }`** redefines
   *only the tokens whose value changes*. The `:not()` guard excludes a viewer who has explicitly
   chosen light.
3. **`:root[data-theme="dark"]`** repeats the same overrides byte-for-byte, so an explicit dark
   choice wins on a light OS. Both dark blocks are generated from one source object (§13.11.2)
   and cannot drift.

`body` always paints `background: var(--bg-canvas)` and `color: var(--text-primary)` explicitly —
never transparent, because a recipient-facing page inherits nothing from us. `<html>` carries
`color-scheme: light dark` so native form controls and scrollbars follow.

### 13.2.2 The three sharing states

These are the three most important colours in the product. §7.8 derives exactly one of them for
every artifact at every moment.

| State | Derived when | Hue | Why this hue |
| --- | --- | --- | --- |
| **Private** | No live links, no live grants | **Teal** | Cool, closed, quiet. The default, and the state that should feel like *nothing is happening*. Deliberately not green — it must never read as "success" or "deployed OK". |
| **Shared with people** | Live grants, no live links | **Indigo-violet** | Cool but populated. A grant is a named human with an account; the colour is calm because there is no bearer token loose in the world, but it is not the same as private, because someone else can see this. |
| **Link active** | At least one live link | **Amber-gold** | Warm, forward, attention-getting. Not red — a live link is not an error, it is a deliberate act by the owner. But it is the state that warrants a second look, so it shares a hue family with `warning`. |

That last sharing is intentional and load-bearing: **amber in Share means "reachable by someone
holding a URL, or otherwise wants your attention."** A warning banner and a link-active badge
being the same family is the semantic, not a collision. Red is reserved for destructive actions
and errors, and never appears on a sharing-state indicator.

Teal / indigo-violet / amber survives protan, deutan, and tritan deficiency because the three
differ in *lightness* and in *warm-versus-cool* as well as in hue: under a deuteranope
simulation the tints read as light-grey-cool, light-blue-cool, and light-warm respectively, and
the foregrounds read as dark-cool, very-dark-cool, and dark-warm. Green-versus-red would not
survive this and is not used for state anywhere in the product. Even so, none of the three is
ever used alone (D4).

### 13.2.3 Modifiers, and the states that are not sharing states

Four further families exist. None of them is a *fourth* sharing state — each is a modifier or a
lifecycle condition rendered as a sibling chip beside the state badge.

| Family | What it marks | Hue | Adjacency rule |
| --- | --- | --- | --- |
| `--state-expiring` | A live link with ≤48h remaining | Orange | Only ever beside the link-active badge |
| `--state-password` | A link that carries a password | Plum | Only ever beside the link-active badge |
| `--state-expired` | A link past its expiry, or an expired-link result page | Slate, dashed border | Replaces the expiry chip; never beside `granted` |
| `--state-trashed` | An artifact in the trash | Warm stone | Replaces the state badge entirely (§13.6.8.4) |

`--state-password` (plum) and `--share-granted` (indigo-violet) are the closest pair in this
palette under protanopia. They are prevented from converging by a hard rule: **the password chip
renders only adjacent to the link-active badge, never adjacent to the granted badge**, so the two
never appear as peers in the same row. The sharing panel (11.12) shows grants and links in
separate sections with their own headings for the same reason.

### 13.2.4 Token definitions

```css
:root {
  /* ---------- Surfaces ---------- */
  --bg-canvas:   #F4F5F7;  /* app background, behind everything */
  --bg-surface:  #FFFFFF;  /* cards, tables, panels, sidebar */
  --bg-raised:   #FFFFFF;  /* menus, dialogs, drawers, popovers (+ shadow) */
  --bg-sunken:   #ECEEF2;  /* code blocks, wells, disabled fields, skeletons */
  --bg-hover:    #F0F2F5;  /* neutral row / menu-item hover */
  --bg-active:   #E4E7ED;  /* pressed, or a held-open trigger */
  --bg-selected: #E8EFFC;  /* selected row, active nav item */
  --bg-overlay:  rgba(15, 19, 26, 0.45);   /* dialog and drawer scrim */
  --bg-viewer:   #E9EBEF;  /* the mat behind a rendered artifact (§13.5.4) */

  /* ---------- Text ---------- */
  --text-primary:   #13171E;  /* body, headings, table cells */
  --text-secondary: #474E5F;  /* labels, secondary cells, sidebar items */
  --text-tertiary:  #646C7C;  /* metadata, table headers, helper text, em dash */
  --text-disabled:  #8A92A2;  /* disabled control text only */
  --text-inverse:   #FFFFFF;  /* on --neutral-solid and on any *-solid fill */
  --text-link:      #1D5FD1;

  /* ---------- Borders ---------- */
  --border-subtle: #E5E7EC;  /* table row rules, section dividers */
  --border-default:#D4D8E0;  /* card and panel edges */
  --border-strong: #7E8697;  /* control boundaries: input, select, checkbox, toggle */
  --border-focus:  #1D5FD1;

  /* ---------- Neutral solid (primary button, tooltip) ---------- */
  --neutral-solid:        #1E2330;
  --neutral-solid-hover:  #2B3241;
  --neutral-solid-active: #0D1117;
  --neutral-solid-text:   #FFFFFF;

  /* ---------- SHARING STATE: private ---------- */
  --share-private-bg:       #E3F2F0;
  --share-private-border:   #A3D4CE;
  --share-private-fg:       #08574F;
  --share-private-solid:    #0A6960;
  --share-private-on-solid: #FFFFFF;

  /* ---------- SHARING STATE: shared with people (grant) ---------- */
  --share-granted-bg:       #ECEBFB;
  --share-granted-border:   #C3BFF0;
  --share-granted-fg:       #3A2E9C;
  --share-granted-solid:    #4A3BC0;
  --share-granted-on-solid: #FFFFFF;

  /* ---------- SHARING STATE: link active ---------- */
  --share-link-bg:       #FCF2DF;
  --share-link-border:   #EED29A;
  --share-link-fg:       #784D05;
  --share-link-solid:    #955F08;
  --share-link-on-solid: #FFFFFF;

  /* ---------- SHARING STATE: unknown (never assume private) ---------- */
  --share-unknown-bg:     #ECEEF2;
  --share-unknown-border: #D4D8E0;
  --share-unknown-fg:     #474E5F;

  /* ---------- Modifier: expiring soon (≤48h) ---------- */
  --state-expiring-bg:       #FDEDE2;
  --state-expiring-border:   #F0C29E;
  --state-expiring-fg:       #883B05;
  --state-expiring-solid:    #A54806;
  --state-expiring-on-solid: #FFFFFF;

  /* ---------- Modifier: password-protected ---------- */
  --state-password-bg:       #F7EAFA;
  --state-password-border:   #DFBCE9;
  --state-password-fg:       #6A2482;
  --state-password-solid:    #7E2C99;
  --state-password-on-solid: #FFFFFF;

  /* ---------- Lifecycle: expired link ---------- */
  --state-expired-bg:     #ECEEF2;
  --state-expired-border: #B9C0CC;   /* rendered 1px dashed */
  --state-expired-fg:     #4A5262;

  /* ---------- Lifecycle: trashed artifact ---------- */
  --state-trashed-bg:     #F1EEEA;
  --state-trashed-border: #D9D2C9;
  --state-trashed-fg:     #57503F;

  /* ---------- Semantic: info ---------- */
  --state-info-bg:       #EAF1FD;
  --state-info-border:   #B9D0F6;
  --state-info-fg:       #14428F;
  --state-info-solid:    #1D5FD1;
  --state-info-on-solid: #FFFFFF;

  /* ---------- Semantic: success ---------- */
  --state-success-bg:       #E6F5EB;
  --state-success-border:   #A7D8BA;
  --state-success-fg:       #0E5A31;
  --state-success-solid:    #14713D;
  --state-success-on-solid: #FFFFFF;

  /* ---------- Semantic: warning (same family as link-active, by design) ---------- */
  --state-warning-bg:       #FCF2DF;
  --state-warning-border:   #EED29A;
  --state-warning-fg:       #784D05;
  --state-warning-solid:    #955F08;
  --state-warning-on-solid: #FFFFFF;

  /* ---------- Semantic: danger ---------- */
  --state-danger-bg:       #FDECEA;
  --state-danger-border:   #F5BFB9;
  --state-danger-fg:       #97231B;
  --state-danger-solid:    #BB2E24;
  --state-danger-hover:    #A6271E;
  --state-danger-on-solid: #FFFFFF;

  /* ---------- Charts (storage, views — 11.25, 11.7) ---------- */
  --chart-1: #1D5FD1;  --chart-2: #0A6960;  --chart-3: #955F08;
  --chart-4: #7E2C99;  --chart-5: #3A2E9C;  --chart-6: #14713D;
  --chart-grid: #E5E7EC;
  --chart-axis: #646C7C;

  /* ---------- Focus ---------- */
  --focus-ring-color:  #1D5FD1;
  --focus-ring-width:  2px;
  --focus-ring-offset: 2px;

  /* ---------- Elevation (light) ---------- */
  --shadow-xs: 0 1px 2px rgba(15, 19, 26, 0.06);
  --shadow-sm: 0 1px 3px rgba(15, 19, 26, 0.08), 0 1px 2px rgba(15, 19, 26, 0.04);
  --shadow-md: 0 4px 12px rgba(15, 19, 26, 0.10), 0 1px 3px rgba(15, 19, 26, 0.06);
  --shadow-lg: 0 16px 40px rgba(15, 19, 26, 0.16), 0 2px 8px rgba(15, 19, 26, 0.08);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg-canvas:   #0D1015;
    --bg-surface:  #141920;
    --bg-raised:   #1A2029;
    --bg-sunken:   #090C11;
    --bg-hover:    #1D242E;
    --bg-active:   #262F3B;
    --bg-selected: #152848;
    --bg-overlay:  rgba(3, 5, 9, 0.68);
    --bg-viewer:   #090C11;

    --text-primary:   #E8EBF0;
    --text-secondary: #A6AFBE;
    --text-tertiary:  #818B9B;
    --text-disabled:  #5E6878;
    --text-inverse:   #0D1015;
    --text-link:      #77A8F5;

    --border-subtle:  #222A35;
    --border-default: #2E3946;
    --border-strong:  #626E7F;
    --border-focus:   #77A8F5;

    --neutral-solid:        #E8EBF0;
    --neutral-solid-hover:  #FFFFFF;
    --neutral-solid-active: #C8CFD9;
    --neutral-solid-text:   #0D1015;

    --share-private-bg: #0A2523;  --share-private-border: #1A4941;
    --share-private-fg: #5CC9BB;  --share-private-solid:  #29A092;
    --share-private-on-solid: #051F1C;

    --share-granted-bg: #1A1740;  --share-granted-border: #322C6E;
    --share-granted-fg: #ADA5F5;  --share-granted-solid:  #7A6BE0;
    --share-granted-on-solid: #0C0A22;

    --share-link-bg: #2B2008;     --share-link-border: #564019;
    --share-link-fg: #EFB85B;     --share-link-solid:  #D59A2D;
    --share-link-on-solid: #231905;

    --share-unknown-bg: #1D242E;  --share-unknown-border: #2E3946;
    --share-unknown-fg: #A6AFBE;

    --state-expiring-bg: #321909; --state-expiring-border: #5B3016;
    --state-expiring-fg: #F2A16D; --state-expiring-solid:  #DF793B;
    --state-expiring-on-solid: #291105;

    --state-password-bg: #2A1035; --state-password-border: #4C2160;
    --state-password-fg: #DC9BF0; --state-password-solid:  #BC63D6;
    --state-password-on-solid: #1A0620;

    --state-expired-bg: #1D242E;  --state-expired-border: #3A4553;
    --state-expired-fg: #98A2B2;

    --state-trashed-bg: #1F1D19;  --state-trashed-border: #3A362E;
    --state-trashed-fg: #B5AC9A;

    --state-info-bg: #12233F;     --state-info-border: #2A4570;
    --state-info-fg: #8FB8F8;     --state-info-solid:  #3B7DE0;
    --state-info-on-solid: #08111F;

    --state-success-bg: #0E2A1A;  --state-success-border: #205033;
    --state-success-fg: #6DD397;  --state-success-solid:  #35A868;
    --state-success-on-solid: #062012;

    --state-warning-bg: #2B2008;  --state-warning-border: #564019;
    --state-warning-fg: #EFB85B;  --state-warning-solid:  #D59A2D;
    --state-warning-on-solid: #231905;

    --state-danger-bg: #331715;   --state-danger-border: #5E2723;
    --state-danger-fg: #F58F86;   --state-danger-solid:  #E5534B;
    --state-danger-hover: #F26A62;
    --state-danger-on-solid: #2A0C0A;

    --chart-1: #77A8F5;  --chart-2: #5CC9BB;  --chart-3: #EFB85B;
    --chart-4: #DC9BF0;  --chart-5: #ADA5F5;  --chart-6: #6DD397;
    --chart-grid: #222A35;
    --chart-axis: #818B9B;

    --focus-ring-color: #77A8F5;

    --shadow-xs: none;
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.40);
    --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.50);
    --shadow-lg: 0 16px 40px rgba(0, 0, 0, 0.60);
  }
}

/* Byte-identical to the media block above, so an explicit dark choice wins on a light OS.
   Both blocks are emitted from one source object by `npm run tokens` (§13.11.2). */
:root[data-theme="dark"] {
  --bg-canvas: #0D1015;  --bg-surface: #141920;  --bg-raised: #1A2029;
  --bg-sunken: #090C11;  --bg-hover:   #1D242E;  --bg-active: #262F3B;
  --bg-selected: #152848; --bg-overlay: rgba(3, 5, 9, 0.68); --bg-viewer: #090C11;

  --text-primary: #E8EBF0;  --text-secondary: #A6AFBE;  --text-tertiary: #818B9B;
  --text-disabled: #5E6878; --text-inverse:   #0D1015;  --text-link:     #77A8F5;

  --border-subtle: #222A35; --border-default: #2E3946;
  --border-strong: #626E7F; --border-focus:   #77A8F5;

  --neutral-solid: #E8EBF0;        --neutral-solid-hover: #FFFFFF;
  --neutral-solid-active: #C8CFD9; --neutral-solid-text:  #0D1015;

  --share-private-bg: #0A2523;  --share-private-border: #1A4941;
  --share-private-fg: #5CC9BB;  --share-private-solid:  #29A092;
  --share-private-on-solid: #051F1C;

  --share-granted-bg: #1A1740;  --share-granted-border: #322C6E;
  --share-granted-fg: #ADA5F5;  --share-granted-solid:  #7A6BE0;
  --share-granted-on-solid: #0C0A22;

  --share-link-bg: #2B2008;     --share-link-border: #564019;
  --share-link-fg: #EFB85B;     --share-link-solid:  #D59A2D;
  --share-link-on-solid: #231905;

  --share-unknown-bg: #1D242E;  --share-unknown-border: #2E3946;
  --share-unknown-fg: #A6AFBE;

  --state-expiring-bg: #321909; --state-expiring-border: #5B3016;
  --state-expiring-fg: #F2A16D; --state-expiring-solid:  #DF793B;
  --state-expiring-on-solid: #291105;

  --state-password-bg: #2A1035; --state-password-border: #4C2160;
  --state-password-fg: #DC9BF0; --state-password-solid:  #BC63D6;
  --state-password-on-solid: #1A0620;

  --state-expired-bg: #1D242E;  --state-expired-border: #3A4553;
  --state-expired-fg: #98A2B2;

  --state-trashed-bg: #1F1D19;  --state-trashed-border: #3A362E;
  --state-trashed-fg: #B5AC9A;

  --state-info-bg: #12233F;     --state-info-border: #2A4570;
  --state-info-fg: #8FB8F8;     --state-info-solid:  #3B7DE0;
  --state-info-on-solid: #08111F;

  --state-success-bg: #0E2A1A;  --state-success-border: #205033;
  --state-success-fg: #6DD397;  --state-success-solid:  #35A868;
  --state-success-on-solid: #062012;

  --state-warning-bg: #2B2008;  --state-warning-border: #564019;
  --state-warning-fg: #EFB85B;  --state-warning-solid:  #D59A2D;
  --state-warning-on-solid: #231905;

  --state-danger-bg: #331715;   --state-danger-border: #5E2723;
  --state-danger-fg: #F58F86;   --state-danger-solid:  #E5534B;
  --state-danger-hover: #F26A62; --state-danger-on-solid: #2A0C0A;

  --chart-1: #77A8F5;  --chart-2: #5CC9BB;  --chart-3: #EFB85B;
  --chart-4: #DC9BF0;  --chart-5: #ADA5F5;  --chart-6: #6DD397;
  --chart-grid: #222A35; --chart-axis: #818B9B;

  --focus-ring-color: #77A8F5;

  --shadow-xs: none;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.40);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.50);
  --shadow-lg: 0 16px 40px rgba(0, 0, 0, 0.60);
}
```

Elevation in dark theme is primarily a background step (`--bg-surface` → `--bg-raised`) plus a
much tighter shadow, because a large soft shadow is invisible on a dark canvas.

### 13.2.5 Contrast audit

Measured with the WCAG 2.1 relative-luminance formula, sRGB, no antialiasing assumptions.
**AA body** = 4.5:1. **AA large** (≥18.66px regular or ≥14px bold) = 3:1. **AA non-text**
(control boundaries, focus rings, meaningful icons, solid state fills) = 3:1.

**Light theme — text**

| Foreground | on `--bg-surface` | on `--bg-canvas` | on `--bg-sunken` | Verdict |
| --- | --- | --- | --- | --- |
| `--text-primary` #13171E | 17.96 | 16.47 | 15.47 | AAA |
| `--text-secondary` #474E5F | 8.32 | 7.63 | 7.17 | AAA |
| `--text-tertiary` #646C7C | 5.28 | 4.84 | 4.54 | **AA body on all three** |
| `--text-link` #1D5FD1 | 5.82 | 5.33 | 5.01 | AA |
| `--text-disabled` #8A92A2 | 3.13 | 2.87 | 2.69 | Exempt (WCAG 1.4.3 disabled-control exception); still ≥3:1 on surface |

**Light theme — state families.** `fg on tint` is the badge, chip, and banner case. `fg on
surface` is the icon-only and inline-text case. `on-solid on solid` is the filled badge and
filled button case. `solid on surface` establishes that a solid fill is itself a valid non-text
indicator.

| Family | fg on own tint | fg on surface | on-solid on solid | solid on surface | Verdict |
| --- | --- | --- | --- | --- | --- |
| `share-private` | 7.33 | 8.45 | 6.56 | 6.56 | AA all |
| `share-granted` | 8.70 | 10.24 | 7.84 | 7.84 | AA all |
| `share-link` | 6.60 | 7.34 | 5.36 | 5.36 | AA all |
| `share-unknown` | 7.17 | 8.32 | — | — | AA all |
| `state-expiring` | 6.88 | 7.85 | 5.95 | 5.95 | AA all |
| `state-password` | 8.28 | 9.60 | 7.76 | 7.76 | AA all |
| `state-expired` | 6.76 | 7.85 | — | — | AA all |
| `state-trashed` | 6.92 | 8.00 | — | — | AA all |
| `state-info` | 8.39 | 9.52 | 5.82 | 5.82 | AA all |
| `state-success` | 7.37 | 8.32 | 6.07 | 6.07 | AA all |
| `state-warning` | 6.60 | 7.34 | 5.36 | 5.36 | AA all |
| `state-danger` | 7.14 | 8.16 | 5.95 | 5.95 | AA all |
| `neutral-solid` | — | — | 15.69 | — | AAA |

**Dark theme — text**

| Foreground | canvas | surface | raised | sunken | Verdict |
| --- | --- | --- | --- | --- | --- |
| `--text-primary` #E8EBF0 | 15.95 | 14.77 | 13.70 | 16.39 | AAA |
| `--text-secondary` #A6AFBE | 8.62 | 7.98 | 7.40 | 8.86 | AAA |
| `--text-tertiary` #818B9B | 5.53 | 5.13 | 4.76 | 5.69 | **AA body on all four** |
| `--text-link` #77A8F5 | 7.90 | 7.32 | 6.79 | 8.12 | AAA |
| `--text-disabled` #5E6878 | 3.38 | 3.13 | 2.91 | 3.48 | Exempt |

**Dark theme — state families**

| Family | fg on own tint | fg on surface | on-solid on solid | solid on surface | Verdict |
| --- | --- | --- | --- | --- | --- |
| `share-private` | 8.09 | 8.85 | 5.36 | 5.50 | AA all |
| `share-granted` | 7.64 | 7.97 | 4.63 | 4.21 | AA all |
| `share-link` | 8.89 | 9.82 | 7.00 | 7.14 | AA all |
| `share-unknown` | 7.07 | 7.98 | — | — | AA all |
| `state-expiring` | 7.89 | 8.49 | 5.89 | 5.83 | AA all |
| `state-password` | 8.16 | 8.40 | 5.40 | 4.95 | AA all |
| `state-expired` | 6.06 | 6.85 | — | — | AA all |
| `state-trashed` | 7.48 | 7.84 | — | — | AA all |
| `state-info` | 7.76 | 8.72 | 4.68 | 4.37 | AA all |
| `state-success` | 8.36 | 9.60 | 5.68 | 5.84 | AA all |
| `state-warning` | 8.89 | 9.82 | 7.00 | 7.14 | AA all |
| `state-danger` | 7.19 | 7.70 | 4.91 | 4.77 | AA all |
| `neutral-solid` | — | — | 15.95 | — | AAA |

**Non-text.** `--border-strong` is the only border token permitted on a control boundary and
measures **3.66** (light, on surface) / **3.41** (dark, on surface) — AA non-text in both.
`--border-default` (1.43 light / 1.50 dark) and `--border-subtle` (1.24 / 1.22) are decorative
and may be used only where the component is *also* distinguished by a background change.
`--focus-ring-color` measures **5.82** against light surface and **7.32** against dark surface.
`--state-expired-border` measures 1.83 / 1.81 and is therefore always paired with the dashed
stroke *and* the tint, never used as a lone control boundary.

Two rules follow and are non-negotiable:

1. **An input's border is always `--border-strong`.** Never `--border-default`.
2. **`--border-default` is never the only thing distinguishing an interactive control from the
   page.**

Every value above is asserted in Part 14 by a token-level contrast test that reads
`tokens.json` and fails CI on regression, so a future colour change cannot quietly drop a pair
below threshold.

---

## 13.3 Typography

### 13.3.1 Stacks

```css
:root {
  --font-sans:
    "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, "Noto Sans", sans-serif,
    "Apple Color Emoji", "Segoe UI Emoji";

  --font-mono:
    "JetBrains Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo,
    Consolas, "Liberation Mono", "Courier New", monospace;
}
```

**Inter** is the optional face, **self-hosted** from `/assets/fonts/inter-{400,500,600}.woff2`
with `font-display: swap`, subset to Latin + Latin-Ext, roughly 42 KB total. **JetBrains Mono**
is likewise optional and self-hosted (400, 500), roughly 30 KB. Its slashed zero and its
unambiguous `1` / `l` / `I` are the entire reason for choosing it: this product asks people to
read 22-character base58 share tokens and SHA-256 prefixes and decide whether two of them match.

**No Share surface ever references a font CDN.** Not `fonts.googleapis.com`, not
`fonts.gstatic.com`, not a self-hosted file on another origin. A font request from a
recipient-facing page (R1–R7) would tell a third party that a specific viewer, at a specific
time, opened a specific person's private link — precisely the leak this product exists to
close. The dashboard follows the same rule rather than maintaining two, because one rule
everywhere is easier to keep than two.

If either face fails to load, the system stack renders at close metrics and nothing shifts by
more than one line-height. Recipient-facing pages use **the system stack only** and never link a
font file at all (§13.11.4).

Enable `--font-features: "cv05" 1, "ss01" 1, "tnum" 1;` in numeric contexts only.
`font-variant-numeric: tabular-nums` is **mandatory** in every table cell containing a number,
every byte size, every duration, every count, and every timestamp.

### 13.3.2 Scale

Root is 16px. Sizes are given in px for clarity and authored in rem.

| Token | Size | Line height | Weight | Tracking | Used for |
| --- | --- | --- | --- | --- | --- |
| `--type-display` | 28px / 1.75rem | 34px (1.21) | 600 | -0.02em | Sign-in (11.1–11.2), passkey registration (11.3), invite acceptance (11.4), the empty-instance state, the R3 expired-link headline. Nowhere else. |
| `--type-h1` | 22px / 1.375rem | 28px (1.27) | 600 | -0.015em | The screen title in the page header. Exactly one per screen. |
| `--type-h2` | 18px / 1.125rem | 24px (1.33) | 600 | -0.01em | Section headings, dialog and drawer titles, card titles when the card is a page section. |
| `--type-h3` | 15px / 0.9375rem | 20px (1.33) | 600 | 0 | Card headers, form group legends, the viewer's filename, table group headers, stacked-row titles. |
| `--type-body` | 14px / 0.875rem | 20px (1.43) | 400 | 0 | **Default.** All UI text, table cells, form values, menu items, button labels. |
| `--type-body-lg` | 15px / 0.9375rem | 24px (1.6) | 400 | 0 | Help and agent-setup prose (11.27) and the body of banners. |
| `--type-sm` | 13px / 0.8125rem | 18px (1.38) | 400 | 0 | Helper text, field errors, secondary table cells, timestamps, breadcrumbs, captions. |
| `--type-xs` | 12px / 0.75rem | 16px (1.33) | 500 | 0.005em | Table column headers, badge and chip labels, tooltip body, avatar initials. |
| `--type-2xs` | 11px / 0.6875rem | 14px (1.27) | 500 | 0.01em | Chart axis labels and sparkline captions only. Never for anything anyone must act on. |

Weights available: **400 regular, 500 medium, 600 semibold**. There is no 700 and no italic
anywhere in the product chrome. (Help prose may use italic for the single purpose of marking a
term on first use.) Emphasis inside body text is 500 — never 600, never italic.

Table column headers are `--type-xs`, weight 500, `--text-tertiary`, **sentence case, not
uppercase**. Uppercase headers cost legibility at 12px and buy nothing at this density.

### 13.3.3 Monospace scale

| Token | Size | Line height | Weight | Used for |
| --- | --- | --- | --- | --- |
| `--type-mono` | 13px | 20px | 400 | Inline identifiers in body context: artifact names, paths, IDs, URLs. |
| `--type-mono-sm` | 12px | 18px | 400 | Identifiers inside chips, table cells at compact density, breadcrumb segments, file-tree rows. |
| `--type-mono-code` | 13px | 20px | 400 | Code blocks (§13.6.19), the agent-setup snippets, the manifest view. |
| `--type-mono-lg` | 18px | 24px | 500 | A share token or generated password in a "shown once" copy field (§13.6.20.3), and the artifact name in the 11.7 page header. |

### 13.3.4 The monospace rule

**Artifact names, share tokens, and IDs are ALWAYS monospace. There is no exception, including
inside headings**, where they render at the heading's size in `--font-mono` at weight 500.

Monospace, always:

- **Artifact names** — `postcal`, `q3/market-report` — in the list, in the header, in a
  breadcrumb, in a dialog sentence, in a toast, in an email.
- **Share tokens and share URLs** — `9fq2n4kwPz3mXr7bTvQ8dL`, `share.c52.com/s/9fq2n4kw…`.
- **Generated and owner-supplied link passwords** — `civil-marmot-71`.
- All prefixed IDs from §3: `art_`, `ver_`, `fil_`, `lnk_`, `grt_`, `tok_`, `usr_`, `pky_`,
  `ses_`, `aud_`.
- **API tokens** and their `shr_` prefix, including the masked form `shr_…4f2a`.
- SHA-256 file hashes and their 7-character display prefixes.
- File and directory paths, including in the file tree and the file listing (R7).
- Handles (`~sarah`) and every URL in the product.
- MIME types, HTTP methods, status codes, header names, error codes (`link_expired`), scope
  names (`share:create`), and duration strings (`14d`).

Proportional, always: artifact **titles**, person names, tag labels, descriptions, link labels,
prose, error sentences, dates and times, counts, byte sizes in tables.

The reason is falsifiability. Someone checking that the token in an email matches the one in the
dashboard needs a character-by-character scan, and a proportional font makes `rn` and `m` the
same shape. This product asks people to trust identifiers, so it has to make them readable.

A name and its title frequently sit together. The name leads, monospace, `--text-primary`; the
title follows on the same line at `--type-sm` `--text-tertiary`, proportional, truncated with
CSS if it must be:

```
postcal   Q4 posting calendar
```

Never the other way round. The name is the address; the title is a courtesy.

---

## 13.4 Spacing, sizing, radius, elevation

### 13.4.1 Spacing scale

Base unit **4px**. Every margin, padding, and gap in the product is one of these values.

```css
--space-0:   0;
--space-px:  1px;
--space-05:  2px;
--space-1:   4px;
--space-15:  6px;
--space-2:   8px;
--space-3:  12px;
--space-4:  16px;
--space-5:  20px;
--space-6:  24px;
--space-8:  32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
--space-20: 80px;
```

**The rhythm rule:** all vertical spacing is a multiple of 4px. The only permitted
non-multiples are 1px borders, the 2px focus offset, and the 6px step (`--space-15`), which
exists solely for horizontal padding inside small controls and for the gap between an icon and
its label. If a layout seems to need 14px or 18px, the layout is wrong; pick 12px, 16px, or
20px.

| Context | Value |
| --- | --- |
| Icon → label gap | `--space-15` (6px) |
| Between related controls in a row | `--space-2` (8px) |
| Between a sharing-state badge and its sibling chips | `--space-15` (6px) |
| Form field → its helper or error text | `--space-15` (6px) |
| Between form fields | `--space-4` (16px) |
| Between form groups | `--space-6` (24px) |
| Card padding | `--space-4` (16px); `--space-6` when the card is a page section |
| Dialog and drawer padding | `--space-6` (24px) |
| Between page sections | `--space-8` (32px) |
| Page gutter (desktop) | `--space-6` (24px) |
| Viewer mat inset around artifact content | `--space-6` (24px), `--space-4` below 768px |

### 13.4.2 Control heights

| Token | Height | Font | Horizontal padding | Used by |
| --- | --- | --- | --- | --- |
| `--control-xs` | 24px | `--type-xs` | 8px | Chips, badges, table row actions, tag inputs |
| `--control-sm` | 28px | `--type-sm` | 10px | Toolbar buttons, filters, compact-density inputs, pagination, viewer bar controls |
| `--control-md` | 32px | `--type-body` | 12px | **Default.** Buttons, inputs, selects, dropdown triggers |
| `--control-lg` | 40px | `--type-body` | 16px | The primary action on sign-in, the confirm in the create-link dialog (11.13), the R1 unlock button, mobile controls |

Icon-only buttons are square at their control height: 24 / 28 / 32 / 40. Minimum touch target
below 768px is 44×44 — small controls keep their visual size and gain invisible padding through
a `::before` overlay.

Row heights: **table row 40px** (comfortable, the default), **32px** (compact), **56px** for
list rows carrying a thumbnail plus two lines (the artifact list at 11.5 on narrow viewports).
Sidebar nav item 32px. Menu item 32px. Tab 36px. File-tree row 28px.

### 13.4.3 Radii

```css
--radius-xs:   3px;    /* checkbox, inline code */
--radius-sm:   4px;    /* badges, chips, code blocks, thumbnails, table inner corners */
--radius-md:   6px;    /* DEFAULT: buttons, inputs, selects, menu items */
--radius-lg:   8px;    /* cards, panels, banners, toasts, dropdown surfaces */
--radius-xl:  12px;    /* dialogs, drawers (leading edge only) */
--radius-full: 9999px; /* avatars, toggle track and thumb, the state dot */
```

Badges use `--radius-sm`, never `--radius-full`. A pill-shaped status badge reads as consumer
UI; a 4px chip reads as data.

### 13.4.4 Elevation

Four levels. Declared on bare `:root` in §13.2.4 with the dark overrides in the same block.

| Level | Applied to |
| --- | --- |
| flat — no shadow, 1px `--border-default` | Cards, tables, panels, the sidebar, the viewer bar |
| `--shadow-sm` | Sticky table header once scrolled, sticky page header |
| `--shadow-md` | Dropdown menus, popovers, tooltips, toasts, the command palette |
| `--shadow-lg` | Dialogs, drawers |

Cards have no shadow at rest and never gain one on hover. Hover on an interactive card changes
`--bg-surface` → `--bg-hover` and `--border-default` → `--border-strong`. Nothing in this
product lifts, scales, or floats on hover.

### 13.4.5 Z-index scale

```css
--z-base: 0;      --z-sticky: 10;   --z-sidebar: 20;   --z-viewer-bar: 30;
--z-dropdown: 100; --z-tooltip: 200; --z-drawer: 300;
--z-overlay: 400;  --z-dialog: 401;  --z-toast: 500;
```

Nothing in the product uses a z-index outside this scale. An artifact rendered in an `iframe`
sits at `--z-base` and can never raise itself above the viewer bar, because the `iframe` is
sandboxed and its stacking context is the frame, not the page.

---

## 13.5 Layout

### 13.5.1 The app shell

```
┌──────────────────────────────────────────────────────────────────────┐
│  Top bar  52px                                                       │
├──────────────┬───────────────────────────────────────────────────────┤
│              │  Page header                                          │
│  Sidebar     │  h1 (mono name) + sharing state + actions             │
│  240px       │───────────────────────────────────────────────────────│
│              │  Content region                                       │
│              │  max-width 1240px (data) / 720px (prose, forms)       │
│              │  gutter 24px                                          │
└──────────────┴───────────────────────────────────────────────────────┘
```

| Element | Spec |
| --- | --- |
| Sidebar | 240px expanded, 56px icon rail collapsed. `--bg-surface`, 1px right border `--border-subtle`. Collapse state persists in `localStorage` under `share.sidebar`. |
| Top bar | 52px. `--bg-surface`, 1px bottom border `--border-subtle`, sticky at `--z-sticky`. Contains, left to right: the space switcher (own space / shared with me), the search trigger with a `⌘K` hint, an upload button, the theme control, help, and the avatar menu. |
| Page header | Not a separate bar; it sits inside the content region with 24px top padding. Contains the `--type-h1` title, the sharing-state indicator when the screen represents one artifact, and up to three actions right-aligned. |
| Content max-width | **1240px** for tables, the artifact list, the files tab, storage, audit. **720px** for help prose, settings forms, and any single-column form. Centred with `margin-inline: auto` past the max. |
| Page gutter | 24px ≥1024px; 16px 640–1023px; 12px <640px. |
| Footer | None. Instance version and a link to 11.28 live in the sidebar foot at `--type-sm` `--text-tertiary`. |

Sidebar groups, top to bottom: **artifacts** (Artifacts, Shared with me, Trash), **account**
(Tokens, Security, Storage, Settings), and, for the root user only, **instance** (Users, Audit,
Status). The active item uses `--bg-selected`, `--text-primary`, and a 2px inset left bar in
`--text-link`.

The sidebar carries no per-artifact state indicators and no counts other than a trash count,
because a permanently visible tally of live links would become wallpaper. Links needing
attention surface as the expiring-soon banner on 11.5 instead (§13.6.16).

### 13.5.2 Breakpoints

```css
--bp-sm:  640px;  --bp-md:  768px;  --bp-lg: 1024px;
--bp-xl: 1280px;  --bp-2xl: 1536px;
```

| Breakpoint | What changes |
| --- | --- |
| **≥1536px** | The content region stays at its max-width; extra space becomes gutter. Nothing stretches. The viewer is the sole exception and always fills the viewport. |
| **≥1280px** | The files tab (11.8) shows the file tree (240px) and the preview side by side. The sharing panel (11.12) shows links and grants in two columns. |
| **1024–1279px** | The file tree collapses to a toggle. The sharing panel stacks to one column. Tables drop their `priority=3` columns (marked per table in Part 11). |
| **768–1023px** | The sidebar becomes an overlay drawer behind a hamburger in the top bar; content takes the full width. Page-header actions beyond the first collapse into an overflow `⋯` menu. Tables drop `priority=2` columns. |
| **640–767px** | Tables become stacked rows (§13.5.3). Dialogs go to `calc(100vw - 32px)`. Tabs become horizontally scrollable with edge fades. The viewer bar loses its filename and keeps its controls. |
| **<640px** | Dialogs become full-screen sheets with a sticky footer. Drawers become bottom sheets at 90vh. The command palette is full-screen. Two-column forms become one column. The viewer's page gutter drops to 0 and the artifact fills the width. |

The dashboard is fully usable at 375px. It is not *optimised* for phones — this is an
operator's tool — but every action, including creating and revoking a share link, must be
reachable there, because the moment someone needs to kill a link is rarely the moment they are
at a desk.

### 13.5.3 Table density and column rules

**Density** is a per-user preference persisted in `localStorage` under `share.density`, with
values `comfortable` (default, 40px rows, `--type-body`) and `compact` (32px rows, `--type-sm`,
identifiers drop to `--type-mono-sm`, thumbnails drop from 32px to 20px). The control is a
two-state segmented control in the table toolbar, not buried in settings. Density never changes
which columns are present — only heights and font sizes.

Column rules, applied to every table in the product:

1. **Column 1 is identity** — the artifact name (monospace) with its title beneath or beside it,
   preceded by a 32px kind thumbnail (§13.6.28). Sticky-left at ≥1024px. Never truncated below
   200px of content; if space is short, other columns truncate first.
2. **Column 2 is the sharing-state indicator** on every table whose rows are artifacts. It never
   truncates, never collapses into an overflow menu, and never drops at any breakpoint. If the
   viewport cannot fit columns 1 and 2 together, the table becomes stacked rows rather than
   dropping the state.
3. **Numeric columns are right-aligned** with `tabular-nums`. Text columns are left-aligned.
   There is no centre alignment in any table in this product.
4. **Timestamps are the last data column**, `--type-sm`, `--text-tertiary`.
5. **Row actions** are a trailing 40px column holding one `⋯` icon button, revealed on row hover
   and on keyboard focus, and always present on coarse pointers (`@media (pointer: coarse)`).
6. Row hover is `--bg-hover`. The whole row is a link target when the row has a canonical
   destination, with the anchor wrapping column 1 and a full-row `::after` hit area.
7. **No zebra striping.** Rows are separated by a 1px `--border-subtle` rule.

**Stacked rows** (<768px): each row becomes a card at `--radius-lg` with the kind thumbnail and
the monospace name as its title at `--type-h3`, **the sharing-state indicator directly beneath
the title**, the title text and remaining columns as `label: value` pairs at `--type-sm`, and
the `⋯` menu at the card's top-right.

### 13.5.4 The viewer: full-bleed layout

Screen 11.9 renders an artifact. It is the only screen in the product that abandons the app
shell, and it does so because of D3: the artifact is the content, and a sidebar next to
somebody's carefully composed report is the design system talking over it.

```
┌──────────────────────────────────────────────────────────────────────┐
│ ← postcal · index.html      [🔒 Private]        ⤓  ⧉  ⋯      ✕      │  48px viewer bar
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                    ┌────────────────────────────┐                    │
│                    │                            │                    │  --bg-viewer mat
│                    │     rendered artifact      │                    │
│                    │                            │                    │
│                    └────────────────────────────┘                    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

| Element | Spec |
| --- | --- |
| Viewer bar | 48px, `--bg-surface`, 1px bottom `--border-subtle`, `--z-viewer-bar`, never translucent and never overlaying content. Left: a 28px ghost back button, the monospace artifact name, a `·` separator, and the current filename at `--type-sm` `--text-tertiary`. Centre: the sharing-state indicator at `sm` / `subtle`. Right: download, open-in-new-tab, `⋯`, and close, all 28px ghost icon buttons. |
| Mat | `--bg-viewer` fills the remaining viewport. The artifact is centred with 24px inset. The mat is the only surface in the product that is neither canvas nor surface, and it exists so a white PDF page and a transparent PNG both have an edge. |
| Kind: `page`, `bundle` | Rendered in an `<iframe sandbox="allow-scripts allow-forms allow-popups allow-downloads" referrerpolicy="no-referrer">` filling the mat edge to edge with **no inset and no radius** — a bundle is a whole page and must not look framed. No dashboard stylesheet is injected. |
| Kind: `document` (PDF) | The browser's native PDF viewer in an `<object>`, centred, `max-width: 1000px`, full mat height. No custom PDF chrome, no page thumbnails, no in-house renderer. |
| Kind: `image` | Centred, `max-width: min(100%, natural width)`, `max-height: 100%`, `object-fit: contain`, `--radius-sm`, `--shadow-sm`. Click toggles between fit-to-window and 100%; the cursor becomes `zoom-in` / `zoom-out`. A checkerboard is **not** used behind transparency — the mat is enough, and a checkerboard is chrome competing with content. |
| Kind: `video` | A native `<video controls preload="metadata" playsinline>` centred at `max-width: 1280px`. No custom player, no autoplay, no generated poster frame — Share never opens the file (P5), so there is no thumbnail to generate. |
| Kind: `file` | No viewer. The mat holds a centred empty-state-shaped block: the kind icon, the filename in monospace, the byte size, and one `primary` Download button. |
| Chrome timeout | The viewer bar is **always visible**. It does not auto-hide, fade on idle, or reveal on mouse-move. Somebody reading a document for ten minutes should never have to hunt for the way out, and an auto-hiding bar that carries the sharing state would hide the sharing state. |

Keyboard: `Escape` returns to the artifact detail screen, `←` / `→` move between files in a
bundle when the file tree is open, `f` toggles browser fullscreen, `d` downloads. All four are
listed in the `⋯` menu so they are discoverable.

The recipient-facing equivalents (R2, R7) reuse the mat and the kind rules exactly, with a
viewer bar reduced to the artifact's title if one is set, a download button, and nothing else —
no name, no handle, no state indicator, per §7.6.

---

## 13.6 Component specifications

Every component below shares these state definitions unless it overrides them explicitly:

| State | Rule |
| --- | --- |
| **hover** | Background and border step one level (`--bg-surface` → `--bg-hover`, `--border-default` → `--border-strong`). Nothing scales, lifts, or gains a shadow. |
| **active** (pressed) | One further background step (`--bg-active`). No transform. |
| **focus** | `outline: var(--focus-ring-width) solid var(--focus-ring-color); outline-offset: var(--focus-ring-offset);` applied through `:focus-visible` only. `outline: none` without an equally visible replacement is a spec violation. |
| **disabled** | `opacity: 1` — never faded — with `background: var(--bg-sunken)`, `color: var(--text-disabled)`, `border-color: var(--border-default)`, `cursor: not-allowed`, `aria-disabled="true"`. Disabled controls stay focusable so a screen reader can find them; they do not respond to activation. |
| **loading** | The control keeps its exact width, measured before the swap. The label is replaced by a 14px spinner plus the present-tense verb ("Creating link…"). `aria-busy="true"`, non-interactive. Never a layout shift. |

### 13.6.1 Button

**Anatomy:** `[leading icon 16px] [label] [trailing icon 16px]`, 6px gaps, centred. Icons are
optional. A button never carries both a leading and a trailing icon, except the split-button
trigger.

| Variant | Rest | Hover | Active | Use |
| --- | --- | --- | --- | --- |
| `primary` | bg `--neutral-solid`, text `--neutral-solid-text`, no border | bg `--neutral-solid-hover` | bg `--neutral-solid-active` | The one main action per view. At most one per page header and one per dialog footer. |
| `secondary` | bg `--bg-surface`, text `--text-primary`, 1px `--border-strong` | bg `--bg-hover` | bg `--bg-active` | Everything else. The default choice. |
| `ghost` | transparent, text `--text-secondary`, no border | bg `--bg-hover`, text `--text-primary` | bg `--bg-active` | Icon buttons, toolbar actions, row actions, dialog dismiss, viewer-bar controls. |
| `danger` | bg `--state-danger-solid`, text `--state-danger-on-solid` | bg `--state-danger-hover` | 90% luminance of hover | Only the confirming action of a destructive dialog and the danger-zone buttons on 11.21. Never in a toolbar. |
| `danger-ghost` | transparent, text `--state-danger-fg` | bg `--state-danger-bg` | — | The menu item or row action that *opens* a destructive dialog. |

There is no brand-coloured primary button. The create-link dialog's confirm (11.13) is
`primary` — graphite — with a leading `link-2` icon. **Amber lives in the badge and in the
warning banner inside that dialog, never in the button**, so amber never becomes a
click-target colour and never competes with the state it is supposed to describe.

**Revoke** is a `secondary` button, not a `danger` one, everywhere it appears. Killing a live
link is the safe direction (D5) and must not be dressed as dangerous; treating it as scary is
how links stay alive longer than they should.

**Sizes:** `sm` 28px, `md` 32px (default), `lg` 40px. Radius `--radius-md`. Font `--type-body`
weight 500 — not 600; buttons are not headings.

**Split button** ("Share ▾" on 11.7): a `primary` segment, a 1px divider in
`rgba(255,255,255,0.24)`, then a 28px chevron segment opening a dropdown.

**Full-width** only in dialogs below 640px, on the sign-in screens, and on R1.

### 13.6.2 Input

**Anatomy:** `[label] [input [leading icon] [value] [trailing affix or action]] [helper or error]`

Label: `--type-sm`, weight 500, `--text-secondary`, 6px above the field. Required fields carry
no asterisk; optional fields are labelled `(optional)` — most fields here are required, and
marking the minority is quieter.

| State | Spec |
| --- | --- |
| default | 32px tall, bg `--bg-surface`, 1px `--border-strong`, `--radius-md`, padding-inline 10px, `--type-body`, `--text-primary` |
| placeholder | `--text-tertiary`. Placeholders are examples, never instructions, and never repeat the label. |
| hover | border `--text-tertiary` |
| focus | border `--border-focus` plus the focus ring |
| disabled | bg `--bg-sunken`, text `--text-disabled` |
| read-only | bg `--bg-sunken`, border `--border-default`, text `--text-primary`, selectable, always with a copy control |
| invalid | border `--state-danger-solid`, `aria-invalid="true"`, `aria-describedby` pointing at the error id |
| loading | a trailing 14px spinner replacing any trailing affix |

**Affixes** render inside the field in `--font-mono` `--text-tertiary`, separated by a 1px
`--border-subtle` divider with 10px padding. The name field on 11.21 and 11.17 uses a leading
affix of `share.c52.com/` so the address being built is visible as it is typed.

**Monospace inputs:** any input whose value is an identifier — artifact name, tag, handle,
token label, password, recovery code, path — uses `--font-mono` with `autocapitalize="off"`,
`autocorrect="off"`, `spellcheck="false"`.

**Password input** (R1, and the custom-password field in 11.13): `type="password"` with a
trailing 24px ghost `eye` / `eye-off` toggle whose `aria-label` is "Show password" /
"Hide password". The toggle is a real `<button type="button">` so it never submits the form. On
R1, where there is no JavaScript, the toggle is **omitted entirely** rather than rendered
inert.

**Recovery-code entry** (11.2): six 40×48px cells, `--type-mono-lg`, centred, auto-advancing,
paste-aware, `autocomplete="one-time-code"`. It degrades to one plain text input when
JavaScript does not run; the split-cell form is the progressive enhancement.

### 13.6.3 Select

Native `<select>` everywhere except multi-select and the space switcher. Styled to match Input
exactly — 32px, `--border-strong`, `--radius-md`, `appearance: none` — with a 16px
`chevron-down` in `--text-tertiary` 10px from the right edge. Options render at OS default.

A custom listbox is used only where options need an icon or a description: the TTL picker in
11.13, the kind filter on 11.5, and the space switcher. Surface `--bg-raised`, `--radius-lg`,
`--shadow-md`, 4px padding, items 32px with a 16px leading icon and a trailing `check` on the
selected item, `max-height: 320px` then scroll.

**The TTL picker never offers a "never" option.** Its values are `30m`, `24h`, `7d`, `14d`
(default), `30d`, `90d`, `180d`, rendered as `14 days — expires 7 Sep 2026, 18:04` so the
consequence is visible before the choice is made. There is no custom-date input and no
"permanent" affordance anywhere in the UI, because P4 has no exception and a disabled option
labelled "Never" would suggest one exists.

### 13.6.4 Textarea

Same tokens as Input. `min-height: 72px` (3 rows), padding `8px 10px`, `line-height: 20px`,
`resize: vertical`, auto-growing to 240px then scrolling. A character counter — `--type-xs`,
`--text-tertiary`, bottom-right, *outside* the field — appears only on fields with a hard limit
(the link `label` field, 120 characters; the artifact `description` field, 500) and only past
80% of it. At 100% it turns `--state-danger-fg`.

### 13.6.5 Checkbox and radio

A 16×16px control — `--radius-xs` for a checkbox, `--radius-full` for a radio — 1px
`--border-strong` on `--bg-surface`. Checked: background `--neutral-solid`, mark
`--neutral-solid-text` (a 10px `check`, or a 6px dot for a radio). Indeterminate: an 8×2px bar.
Hover: border `--text-tertiary`. Focus: the ring on the control itself.

Label `--type-body` `--text-primary`, 8px gap, clickable, `align-items: flex-start` so a
multi-line label aligns to its first line. Helper text sits beneath at `--type-sm`
`--text-tertiary`, indented to the label's left edge.

**Checkboxes never carry semantic colour.** There is no green checkbox and no amber checkbox in
this product.

### 13.6.6 Toggle

Track 32×18px at `--radius-full`; thumb a 14px circle at `--radius-full`, 2px inset,
`--shadow-xs`. Off: track `--border-strong`. On: track `--neutral-solid`. Disabled: track
`--border-default`. Transition: thumb `transform` 120ms `--ease-standard`, track
`background-color` 120ms.

**Toggles are for preferences that take effect immediately and are individually reversible** —
email notifications, "notify me when a link is created", theme, density, pinning an artifact.

**A toggle never changes an artifact's sharing state.** Not to create a link, not to revoke
one, not to add a password, not to grant to a user. Those are objects you create, list, and
revoke (§1.7, principle 2) and they get dialogs and buttons with verbs. A toggle wired to
`POST /links` is a spec violation, and reviewers should treat one as they would a missing
authorisation check.

### 13.6.7 Badge

A **badge** is a read-only state label. A **chip** is a badge that can be dismissed or that
filters (§13.6.22).

Anatomy: `[icon 12px] [label]`, 4px gap, height 20px (`sm`) or 24px (`md`), padding-inline 6px
(sm) / 8px (md), `--radius-sm`, `--type-xs` weight 500. Never `--radius-full`.

| Variant | Spec |
| --- | --- |
| `subtle` | bg `--{family}-bg`, 1px `--{family}-border`, text `--{family}-fg`. **The default everywhere.** |
| `solid` | bg `--{family}-solid`, no border, text `--{family}-on-solid`. Reserved for the sharing-state indicator in a page header and inside the create-link dialog's result state. |
| `outline` | transparent, 1px `--border-default`, text `--text-secondary`. Counts, version numbers, `v3`, `+2 more`. |

### 13.6.8 The sharing-state indicator

This is the most important component in the product. It appears on at least twelve surfaces and
must be pixel-identical on all of them. It is implemented **once**, exported once, and may not
be re-implemented inline anywhere — a second implementation is how two screens end up
disagreeing about who can see something.

#### 13.6.8.1 Values

There are exactly **four** values: the three derived states from §7.8, plus `unknown`. There is
no fifth.

| Value | API `visibility` | Family | Icon (Lucide) | Label — verbatim |
| --- | --- | --- | --- | --- |
| `private` | `private` | `--share-private-*` | `lock` | `Private` |
| `granted` | `granted` | `--share-granted-*` | `users` | `Shared with 3 people` — always the count, pluralised (`Shared with 1 person`) |
| `link` | `shared` | `--share-link-*` | `link-2` | `Link active` — or `2 links active` when more than one |
| `unknown` | *absent, stale, or failed* | `--share-unknown-*` | `circle-help` | `Unknown` |

The label is never abbreviated, never swapped for another word, and never localised into a
synonym. It is never "Public", "Live", "Published", "Open", "Draft", "Internal", "Visible", or
"Off". Per §12.2 those words do not exist in this product: nothing here is *public*, because
even a live link is a capability held by whoever has it, not an open door, and calling it
public would misdescribe the guarantee.

When `granted` and `link` are both true, **`link` wins** (§7.8) — a live bearer token is the
widest thing true about the artifact, and the owner should see the widest thing first. The
grant count then moves into the indicator's `aria-label` and into the artifact's sharing panel;
it is never dropped silently.

#### 13.6.8.2 The mandatory `unknown` state

`unknown` renders whenever the sharing state has not loaded, when the request that would have
supplied it failed, when a list was served from a stale cache, or when the client holds a
record whose `visibility` field is missing or unrecognised.

**The indicator never optimistically renders `Private`.** Guessing "Private" for an artifact
that in fact has a live link is the single worst failure this component can produce: it is a
silent, confident, wrong claim about who can see somebody's client work. Absence of data is
therefore shown as absence of data, in grey, with a question-mark icon and the word "Unknown".

Consequences, all mandatory:

- `unknown` is **never a skeleton**. While the row is loading the indicator renders `unknown` at
  the correct size, so the layout never shifts and no false state is ever shown even for one
  frame.
- `unknown` **suppresses every action that depends on state.** The "Create link" button, the
  "Revoke" button, and the share split-button render disabled with the tooltip "Sharing state
  unavailable. Reload to continue."
- `unknown` **suppresses the sibling chips.** No expiry chip, no password chip — we do not know
  whether there is a link, so we cannot claim anything about its expiry.
- A component that receives no `visibility` prop at all **throws in development and renders
  `unknown` in production**. It must not default to `private` in its prop defaults, and Part 14
  asserts this with a test that mounts the component with an empty object.
- A rendering of `unknown` that lasts more than 10 seconds swaps its tooltip to include a
  "Try again" affordance in the containing view's toolbar, not in the indicator, which is never
  interactive.

#### 13.6.8.3 Anatomy

```
┌──────────────────────────────────────────────────────────────────┐
│ [🔒 Private]                                                     │  private
│ [👥 Shared with 3 people]                                        │  granted
│ [🔗 Link active] [🔑 Password] [⏱ Expires 7 Sep 2026, 18:04]     │  link, protected
│ [🔗 Link active] [⏱ Expires 26 Aug 2026, 09:00]                  │  link, expiring soon
│ [❓ Unknown]                                                      │  unknown
└──────────────────────────────────────────────────────────────────┘
   state badge        password chip        expiry chip
   (always)           (only with a link)   (only with a link)
```

The **state badge** is the component. The **password chip** and **expiry chip** are siblings
rendered by the same wrapper, in that fixed order, with a 6px gap. The wrapper is a single
`<span role="group">` whose `aria-label` carries the whole fact as one sentence:

```
aria-label="Sharing: link active, password protected, expires 7 September 2026 at 18:04 BST.
            Also shared with 3 people."
```

The wrapper **never wraps to a second line inside a table cell**. Under width pressure it drops
the password chip first and the expiry chip second — **never the state badge** — and every
dropped fact remains in the `aria-label`, in the row's `⋯` menu, and on the artifact's detail
screen.

#### 13.6.8.4 Trashed artifacts

An artifact in the trash renders `--state-trashed-*` with the `trash-2` icon and the label
`In trash`, **replacing the state badge entirely** rather than sitting beside it. This is
correct because §7.10 makes a trashed artifact unshareable (`422 artifact_trashed`), every live
link on it is revoked at delete time, and its previous state is no longer a fact about the
present. The trash screen (11.15) shows a `restore-until` date beside it, not an expiry chip.

#### 13.6.8.5 Sizes and variants

| Size | Badge height | Icon | Text | Where |
| --- | --- | --- | --- | --- |
| `sm` | 20px | 12px | `--type-xs` | Table cells, command-palette results, audit rows, the viewer bar, compact lists |
| `md` | 24px | 14px | `--type-xs` | Card corners, drawer headers, dialog bodies, stacked rows |
| `lg` | 28px | 16px | `--type-sm` weight 500 | The artifact detail page header (11.7) only |

| Variant | Rule |
| --- | --- |
| `subtle` | The default. Every table, card, list, menu, and toast. |
| `solid` | Exactly two places: the artifact detail page header (11.7) at `lg`, and the result state in the create-link dialog (11.13) after the link exists. It exists so that the one screen dedicated to a single artifact states its sharing with maximum force. |
| `dot` | An 8px `--radius-full` dot in `--{family}-solid`, no visible label. Permitted only where a labelled badge cannot fit **and** the same fact appears as text in the same row — currently only the collapsed sidebar's pinned-artifact rail and the compact-density command-palette result list. Requires an `aria-label` and a tooltip. Nowhere else, ever. |

#### 13.6.8.6 Placement

| Surface | Position | Size / variant |
| --- | --- | --- |
| 11.5 Artifact list | Column 2, always present, never drops | `sm` / `subtle` |
| 11.5 Expiring-soon banner | Inline in the banner body, per listed artifact | `sm` / `subtle` |
| 11.6 Empty state / first run | Not shown — there are no artifacts yet | — |
| 11.7 Artifact detail header | Immediately right of the `--type-h1` monospace name, 12px gap, optically centred to the title's cap height | `lg` / `solid` |
| 11.8 Files tab toolbar | Right-aligned, beside the download-all button | `sm` / `subtle` |
| 11.9 Viewer bar | Centre of the bar | `sm` / `subtle` |
| 11.10 Versions tab | Header only, never per version — versions do not have sharing states, the artifact does | `sm` / `subtle` |
| 11.11 Version preview | Header, with an `info` banner noting that links always serve the current version (§7.2) | `sm` / `subtle` |
| 11.12 Sharing panel | At the top of the panel, above the links section | `md` / `subtle` |
| 11.13 Create-link dialog | Twice: the current state at the top of the body, and the resulting state in the success footer | `md` / `subtle`, then `md` / `solid` |
| 11.14 Shared with me | Per row, showing the state **as the grantee sees it**: always `granted`, with the owner's handle beside it | `sm` / `subtle` |
| 11.15 Trash | Per row, always the `In trash` treatment (§13.6.8.4) | `sm` / `subtle` |
| 11.16 Search and command palette | Trailing edge of each artifact result | `sm` / `subtle` |
| 11.23 Audit log | On rows whose event is `link.create`, `link.revoke`, `link.expired`, `grant.create`, `grant.revoke`, showing the **resulting** state | `sm` / `subtle` |
| 11.24 Staleness | Per row | `sm` / `subtle` |
| Toasts | In the toast body whenever the toast reports a sharing change | `sm` / `subtle` |

It never appears inside a dropdown menu item, inside a tooltip as the sole carrier of the fact,
inside a breadcrumb, or on any recipient-facing page (R1–R7) — a recipient must learn nothing
about how else an artifact is shared (§7.6).

#### 13.6.8.7 Behaviour

- **Not interactive.** Not a button, not a link, no `cursor: pointer`; clicking it does nothing.
  The action lives in a nearby button whose label is a verb ("Create link", "Revoke link",
  "Share with a user").
- **On change**, the badge cross-fades over 180ms and its row or header flashes `--bg-selected`
  for 600ms. Under `prefers-reduced-motion: reduce` the flash becomes a 2px left border in
  `--focus-ring-color` held for 3 seconds.
- **Announcement.** `role="status"` with `aria-live="polite"` *only* on the screens where the
  user has just made the change themselves — 11.12, 11.13, and the 11.7 header. In tables it is
  static, so a background refresh never spams a screen reader.
- **Print.** `@media print` forces `subtle`, keeps the 1px border, renders the icon as a real
  inline SVG rather than a background image, and prints the tint as a light grey when the
  printer is monochrome. A printed artifact list must still distinguish the four states without
  colour, which it does through icon and word.
- **Screenshot resilience.** Because the label is always present, a screenshot of any row pasted
  into a chat window carries the complete fact with no legend. This is the actual reason the
  word is never dropped.

### 13.6.9 Expiry chip

Rendered only when the state is `link`. Never on `private`, `granted`, `unknown`, or `In trash`.

| Condition | Family | Icon | Text |
| --- | --- | --- | --- |
| More than 48h remaining | `--share-unknown-*` (neutral) | `timer` | `Expires 7 Sep 2026, 18:04` |
| 48h or less remaining | `--state-expiring-*` | `timer` | `Expires 26 Aug 2026, 09:00` |
| Past expiry, pre-sweep (§7.5) | `--state-expired-*`, 1px **dashed** border | `timer-off` | `Expired 24 Aug 2026, 09:00` |
| Several links with different expiries | neutral, or expiring if any is within 48h | `timer` | The **soonest** expiry, with `+2 more` as an `outline` badge |

The neutral treatment above 48 hours is deliberate. A link with 60 days left is not an alarm,
and colouring every expiry orange would destroy the signal that matters — which is that
something is about to stop working, or has.

The chip text is **always the absolute datetime** (§13.9.2). The relative form ("in 6 days")
lives only in the tooltip and the `aria-label`, never in the chip, because a chip gets
screenshotted and a relative time does not survive being moved through time.

There is no `No expiry` variant, no infinity icon, and no code path that renders one. Every link
has a non-null expiry by P4; a UI capable of drawing a permanent link implies one can exist.

### 13.6.10 Table

Container: `--bg-surface`, 1px `--border-default`, `--radius-lg`, `overflow: hidden`, with an
inner `overflow-x: auto` region so a wide table scrolls inside its own card and the page body
never scrolls horizontally.

Header row 36px, `--bg-surface`, 1px `--border-default` bottom, sticky within the scroll
container and gaining `--shadow-sm` once scrolled. Cells `--type-xs` weight 500
`--text-tertiary`, sentence case. Sortable headers carry a trailing 12px `chevron-up` /
`chevron-down` plus `aria-sort`; an unsorted header shows its chevron at 40% opacity on hover
only.

Body cells: padding-inline 12px (16px on the first and last), vertically centred, `--type-body`,
1px `--border-subtle` bottom except on the last row.

Selection: a 40px leading checkbox column on tables that support bulk actions (artifacts,
versions, tokens, trash). Selecting swaps the toolbar for a selection toolbar reading
`3 selected`. **Bulk revoke is permitted; bulk link creation is not** — widening happens one
artifact at a time (D5), so there is no multi-select path to a share link anywhere in the
product.

Loading renders the header plus five skeleton rows at the current density, with each row's
sharing-state cell rendering `unknown` rather than a skeleton (§13.6.8.2). Empty keeps the
container border and centres the empty state (§13.6.23) with 48px of vertical padding.

### 13.6.11 Card

`--bg-surface`, 1px `--border-default`, `--radius-lg`, padding 16px — 24px when the card is a
page section. Optional header: `--type-h3` title, optional `--type-sm` `--text-tertiary`
description, optional right-aligned action, separated from the body by 16px or by a full-bleed
1px `--border-subtle` rule when the body is a list or a table.

Interactive cards (artifact cards on narrow viewports) gain `cursor: pointer`, hover
`--bg-hover` plus `--border-strong`, and a focus ring on the card itself. They do not lift,
scale, or gain a shadow.

**Stat tile** (11.25 storage, 11.7 view counts): 16px padding, `--type-xs` `--text-tertiary`
label, `--type-display` value with `tabular-nums`, optional `--type-sm` delta. Deltas never
animate and values never count up.

**Link card** (11.12): the one card variant carrying state colour. A 3px left border in
`--share-link-solid` when the link is live, `--state-expiring-solid` within 48 hours, and
`--state-expired-border` (dashed) once expired. Body: the share URL in a copy field, the label,
the expiry chip, the password chip if set, the view count, and a `secondary` Revoke button. The
token itself is shown truncated (§13.9.6) and the copy control copies it whole.

### 13.6.12 Tabs

Underline tabs, never pills. A 36px row with a full-width 1px `--border-subtle` bottom border.
Tab: padding-inline 12px, `--type-body` weight 500, `--text-secondary`; hover `--text-primary`;
selected `--text-primary` with a 2px `--neutral-solid` bar flush to the bottom border. An
optional trailing count is an `outline` badge.

Tabs are peer views of one object — Overview, Files, Versions, Sharing — never navigation
between unrelated screens, never nested, and always reflected in the URL so a tab is linkable
and survives a reload. Below 768px the row scrolls horizontally with 24px edge fades, scroll
snapping per tab, and the selected tab scrolled into view on mount.

### 13.6.13 Dialog

Overlay `--bg-overlay` at `--z-overlay`. Panel: `--bg-raised`, `--radius-xl`, `--shadow-lg`,
`--z-dialog`, centred, `width: min(560px, calc(100vw - 32px))`,
`max-height: calc(100vh - 96px)` with the body scrolling and the header and footer pinned.

| Region | Spec |
| --- | --- |
| Header | 24px padding, `--type-h2` title, optional `--type-sm` `--text-tertiary` description, a 32px ghost `x` at top-right |
| Body | 24px padding-inline, 0 top (the header supplies it), 24px bottom when there is no footer |
| Footer | 24px padding, 1px top `--border-subtle` when the body scrolls, actions right-aligned with an 8px gap, secondary before primary |

Widths: `sm` 400px (confirmations), `md` 560px (default, create-link), `lg` 720px (version
compare, file preview in a dialog).

Behaviour: focus trapped; initial focus on the first interactive element, or on the text input
in a destructive dialog; `Escape` closes unless a submit is in flight; overlay click closes
**only** non-destructive, non-widening dialogs; body scroll locked; `aria-modal="true"` with
`aria-labelledby` pointing at the title. Two dialogs are never open at once — a second step
replaces the first dialog's body, as the create-link dialog does when it moves from form to
result.

### 13.6.14 Drawer

Right-anchored, `width: min(480px, 100vw)`, full height, `--bg-raised`, `--shadow-lg`,
`--radius-xl` on the leading corners only, `--z-drawer`, with the same overlay as a dialog.
Header, body, and footer are identical to Dialog. Below 640px it becomes a 90vh bottom sheet
with `--radius-xl` top corners and a 32×4px `--border-strong` grab handle.

Drawers inspect a row without losing the table: audit event detail (11.23), session detail
(11.19), file entry detail (11.8), version detail (11.10). **Dialogs are for acts.** If the
panel's purpose is a decision, it is a dialog; if its purpose is to look at something, it is a
drawer.

### 13.6.15 Dropdown menu

Surface `--bg-raised`, 1px `--border-default`, `--radius-lg`, `--shadow-md`, `--z-dropdown`,
4px padding, `min-width: 180px`, `max-width: 320px`, `max-height: 400px` then scrolling.
Aligned to the trigger's edge with a 4px offset, flipping on collision.

Items: 32px, padding-inline 8px, `--radius-md`, `--type-body` `--text-primary`, optional 16px
leading icon in `--text-tertiary` with an 8px gap, optional trailing `--type-xs`
`--text-tertiary` shortcut hint. Hover and keyboard highlight are both `--bg-hover`; there is no
separate focus ring inside a menu. Destructive items use `danger-ghost` colours below a 1px
`--border-subtle` divider with 4px margin. Section labels: `--type-xs` weight 500
`--text-tertiary`, 24px, not interactive. Checkable items reserve a 16px leading slot for a
`check`.

A row's `⋯` menu on 11.5 carries, in order: Open, Copy URL, Create link, Manage sharing,
Download, Copy to my space (grantee rows only), a divider, then Move to trash in
`danger-ghost`. **The sharing-state indicator never appears inside a menu item** — a menu is a
list of verbs.

### 13.6.16 Banner / callout

A full-width block inside the content region: `--radius-lg`, 1px `--{family}-border`, background
`--{family}-bg`, padding 12px 16px, with a 3px left border in `--{family}-solid`.

Anatomy: `[16px icon in --{family}-fg] [title (--type-body, 500, --text-primary) + body (--type-body-lg, --text-secondary)] [actions] [optional dismiss x]`

| Variant | Family | Icon | Use |
| --- | --- | --- | --- |
| `info` | `--state-info-*` | `info` | Neutral context: "Links always serve the current version", the grantee notice on 11.14, the version-preview notice on 11.11. |
| `success` | `--state-success-*` | `circle-check` | Rare. The completion of a multi-step flow — passkey registered, instance restored. |
| `warning` | `--state-warning-*` | `triangle-alert` | Every `warnings[]` code from §12.6, the expiring-soon banner on 11.5, the "this token can create share links" notice on 11.18, the over-80%-quota notice on 11.25. |
| `danger` | `--state-danger-*` | `octagon-alert` | Form-level errors, quota exceeded, a failed upload, the danger-zone header on 11.21. |

Only `info` and `success` banners are dismissible; `warning` and `danger` persist until their
cause is resolved. Dismissal is remembered per banner id in `localStorage`, never across
accounts.

**The expiring-soon banner (11.5) is never dismissible.** It lists every artifact with a link
expiring within 48 hours, each row carrying the artifact name in monospace, its sharing-state
indicator at `sm`, the absolute expiry, and an Extend action. It is the one banner allowed to
appear above the page header rather than below it.

### 13.6.17 Toast

Bottom-right stack — bottom-centre below 640px — 16px from the viewport edge, 8px gap,
`--z-toast`, at most 3 visible with older ones collapsing into `+2 more`. Panel: `--bg-raised`,
1px `--border-default`, `--radius-lg`, `--shadow-md`, padding 12px 14px,
`width: min(400px, calc(100vw - 32px))`.

Anatomy: `[16px status icon] [title (--type-body, 500) + optional body (--type-sm, --text-tertiary)] [optional action link] [12px x]`.
The icon takes the semantic family's colour; the panel background does **not** — toasts are
always `--bg-raised`, with `danger` alone adding a 3px `--state-danger-solid` left border.

Durations: success 4s, info 5s, warning 7s, danger **never auto-dismisses**. Hover or focus
pauses the timer. A toast reporting a sharing change carries the sharing-state indicator in its
body and lasts 7s in either direction.

Toasts confirm; they never carry information available nowhere else. **A toast never carries a
share URL, a share token, or a generated password** — those go into a dialog with a copy control
and the shown-once treatment (§13.6.20.3), because a toast disappears and these values cannot be
retrieved again.

Revoking a link shows a toast with a 10-second `Undo` action, which re-creates a link with the
same TTL and label but **a new token**, and the toast body says so: "A new link was created. The
old URL stays dead."

### 13.6.18 File tree

A 240px panel, `--bg-surface`, 1px right border `--border-subtle`, `overflow: auto`. Used on the
files tab (11.8), in the viewer for bundles (11.9), and on R7.

Rows: 28px, padding-inline 8px, 16px indent per depth level applied as `padding-left` so the hit
area spans the full width. Anatomy:
`[12px chevron-right / chevron-down, folders only] [16px kind icon] [name]`, gaps 4px then 6px.
The name is `--type-mono-sm` `--text-primary`, middle-truncated in code (§13.9.6) with the full
path in a `title`. Folders sort before files, then case-insensitive lexical.

The entry-point file (`entryPath`, §5.5) carries a trailing 12px `corner-down-right` icon in
`--text-tertiary` and the tooltip "Served at the artifact root", so it is obvious which file
answers when someone opens the bare URL.

States: hover `--bg-hover`; selected `--bg-selected` with a 2px inset left bar in `--text-link`;
inset focus ring. Full `tree` role with roving `tabindex`, arrow-key navigation (`Left`
collapses or moves to the parent, `Right` expands or moves to the first child), and prefix
type-ahead. Expansion state persists per artifact in `sessionStorage`. Trees over 1,000 nodes
virtualise and show a `--type-sm` `--text-tertiary` footer with the total count and total size.

### 13.6.19 Code block

Container: `--bg-sunken`, 1px `--border-subtle`, `--radius-sm`, `overflow-x: auto`. Content
`--type-mono-code`, `--text-primary`, padding 12px 14px, `tab-size: 2`.

Optional header bar: 32px, `--bg-surface`, 1px `--border-subtle` bottom, with a `--type-xs`
`--text-tertiary` filename or language label at the left and a copy control at the right.

Optional line numbers: `--text-disabled`, `--type-mono-sm`, right-aligned in a 40px gutter with
a 1px `--border-subtle` edge and `user-select: none`, so a copy never picks them up.

Syntax highlighting uses these token colours and no others, in both themes: keyword
`--chart-4`, string `--chart-6`, number `--chart-3`, comment `--text-tertiary`, function
`--chart-1`, punctuation `--text-secondary`. It applies to help-page snippets and the file
viewer only, never to audit output, which stays monochrome.

The agent-setup page (11.27) is the heaviest user of this component: the MCP endpoint block, the
`share post` CLI example, and the `curl` example. Each carries a copy control, and **each
renders any token as the literal placeholder `shr_YOUR_TOKEN`** — a real token is never
interpolated into a sample a screenshot might capture.

Inline code: `--font-mono` at 0.92em of the surrounding size, `--bg-sunken`, 1px
`--border-subtle`, `--radius-xs`, padding 1px 4px.

### 13.6.20 Copy-to-clipboard control

Two ordinary forms and one special one. All three are mandatory wherever an identifier is
displayed.

#### 13.6.20.1 Icon button

A 24px ghost button with a 14px `copy` icon in `--text-tertiary`, hover `--text-primary` plus
`--bg-hover`. On success the icon swaps to `check` in `--state-success-fg` for 1,600ms, and
`aria-live="polite"` announces "Copied". **No toast** — a toast for a copy is noise.

#### 13.6.20.2 Copy field

A read-only Input holding the value in `--font-mono`, with the copy icon button inside its
trailing edge. Used for share URLs, artifact URLs, API tokens, and recovery codes. Clicking
anywhere in the field selects the whole value.

Rules for both forms: the control always copies the **full, untruncated** value even when the
display is abbreviated (§13.9.6); its `aria-label` names what is copied — "Copy share URL", not
"Copy"; and when `navigator.clipboard` is unavailable it falls back to selecting the text and
showing the platform shortcut in a tooltip rather than disappearing.

#### 13.6.20.3 The "shown once" treatment

Three values in this product are returned exactly once and can never be retrieved again: a
**generated link password** (§7.3), an **API token** on creation (§4), and a **recovery code**
(§4.5). They get a distinct, deliberately heavier treatment, and the treatment is identical in
all three places.

```
┌────────────────────────────────────────────────────────────┐
│  🔑  Password — shown once                                 │  --type-h3 + 16px key-round
│                                                            │
│  ┌──────────────────────────────────────────────┐          │
│  │  civil-marmot-71                        [⧉]  │          │  --type-mono-lg, 48px tall
│  └──────────────────────────────────────────────┘          │
│                                                            │
│  ⚠  This is the only time this password is shown.          │  warning banner, not dismissible
│     Copy it now. If you lose it, create a new link.        │
│                                                            │
│  ☐  I have copied the password                             │  checkbox gating the close
└────────────────────────────────────────────────────────────┘
```

| Rule | Detail |
| --- | --- |
| Field | 48px tall (not 32px), `--type-mono-lg`, `--bg-sunken`, 1px `--border-strong`, `--radius-md`, value selectable, whole value selected on click. |
| Banner | A non-dismissible `warning` banner **inside** the dialog body, above the acknowledgement. |
| Acknowledgement | A checkbox labelled "I have copied the password" / "…the token" / "…the recovery code". The dialog's close button and its `x` are **disabled until it is ticked**. `Escape` is also suppressed. This is the only dialog in the product that traps the user, and it does so because closing it destroys information. |
| After close | The value is removed from the client store, not merely hidden. Re-opening the artifact shows `Password set` with no value and no reveal affordance, because the server cannot produce it either (§7.4). |
| Never | Not in a toast, not in a URL, not in a `title` attribute, not in the page title, not in an `aria-live` announcement of the raw characters, and not written to `localStorage` or `sessionStorage`. |
| Copy button | Copies the value and swaps to `check`, but does **not** tick the acknowledgement — the user confirms they have it somewhere, and a clipboard is not somewhere. |

The share URL itself is not shown-once — it is retrievable from the sharing panel for the life
of the link — so it uses an ordinary copy field. Only the password is one-time. The create-link
dialog therefore shows both, adjacent, with the URL above and the password in the shown-once
block below, and the copy control on each labelled distinctly ("Copy share URL", "Copy
password") so a screen-reader user never has to guess which one they just copied.

### 13.6.21 Breadcrumb

`--type-sm` `--text-tertiary`, separated by a 14px `chevron-right` in `--text-disabled` with 6px
gaps. Path segments and artifact names render in `--type-mono-sm` — the monospace rule applies
here too. The last segment is `--text-primary`, not a link, and carries `aria-current="page"`.
Links underline on hover only.

Breadcrumbs never wrap. When the trail overflows, middle segments collapse into a `⋯` ghost
button opening a dropdown; the first segment and the last two always survive.

Used in the file browser (11.8), the viewer for nested bundle paths (11.9), R7, and the help
pages (11.27). The artifact detail screen uses the sidebar plus a page title instead.

### 13.6.22 Tag chip

Tags are the only user-supplied metadata this product stores about an artifact besides the title
and description, and search leans on them (§8.5), so they get real affordance rather than being
buried.

A chip at 24px, `--radius-sm`, `--bg-sunken`, 1px `--border-default`, `--type-xs` weight 500
`--text-secondary`, with a 12px `tag` icon and a 6px gap. **Tag labels are proportional, not
monospace** — a tag is a word, not an identifier.

| Context | Behaviour |
| --- | --- |
| Read-only (table cell, detail header) | Up to 3 chips, then an `outline` `+2` badge whose tooltip lists the rest. |
| Filter (11.5 toolbar, 11.16) | Clickable. Active filters gain `--bg-selected` and 1px `--border-focus`, and carry a trailing 12px `x` in a 16px hit area. |
| Editing (11.7, 11.17) | A token input: chips inside a field, `Enter` or `,` commits, `Backspace` on an empty input removes the last chip, and a combobox suggests existing tags. The §3 constraint (lowercase, digits, space, hyphen, underscore, ≤40 chars, ≤20 tags) is enforced live, with a `--type-sm` error beneath rather than silent truncation. |

Tags never carry semantic colour and are never auto-assigned — nothing in this product infers a
tag from content (P5).

### 13.6.23 Empty state

A centred column, `max-width: 420px`, 48px vertical padding, 12px gaps.

Anatomy: `[32px icon inside a 56px --bg-sunken --radius-full circle, icon in --text-tertiary]`,
`[heading --type-h3 --text-primary]`, `[body --type-sm --text-tertiary, at most 2 sentences]`,
`[one primary action]`, `[optional --type-sm link into 11.27]`.

No illustrations. The icon is the concept's own icon from §13.7 — `package` for an empty
artifact list, `users` for an empty Shared-with-me, `trash-2` for an empty trash, `scroll-text`
for an empty audit log, `link-2` for an artifact with no share links.

Three cases, never conflated:

| Case | Treatment |
| --- | --- |
| **Nothing yet** | The full empty state with a primary action. Copy from §12.5. On 11.6 this becomes the first-run checklist instead. |
| **Nothing matches the filter** | A compact variant: no icon circle, `--type-sm` text, and a ghost "Clear filters" button. |
| **Failed to load** | A `danger` banner inside the container plus a "Try again" `secondary` button. **Never the empty state** — "you have no artifacts" and "we could not fetch your artifacts" must never look alike, because the first is calm and the second means something is wrong. |

### 13.6.24 Skeleton

`--bg-sunken` blocks at `--radius-sm`, sized to the real content's box so nothing shifts when
data arrives. Text skeletons are 12px tall for `--type-sm` and 14px for `--type-body`, with a
paragraph's last line at 60% width. A shimmer sweeps left to right over 1,400ms as a
`background-position` animation on a 200%-wide `--bg-sunken → --bg-hover → --bg-sunken` gradient.

Skeletons appear only after 200ms of loading — a faster response shows nothing, avoiding a
flash — cap at 5 rows in tables, and are **never used for the sharing-state indicator**
(§13.6.8.2) or for a kind thumbnail, which renders its placeholder immediately. Under
`prefers-reduced-motion: reduce` the shimmer is dropped for a flat `--bg-sunken`.

### 13.6.25 Progress bar

Track 4px tall (6px in dialogs), `--bg-sunken`, `--radius-full`. Fill `--neutral-solid`,
`--radius-full`, `transition: width 240ms var(--ease-standard)`.

**Determinate** for uploads (11.17): the value is bytes uploaded over bytes to upload across the
whole post, with a `--type-sm` `--text-tertiary` caption beneath —
`14 of 47 files · 8.2 MB of 24 MB` — and `role="progressbar"` with `aria-valuenow` /
`aria-valuemin` / `aria-valuemax`.

**Indeterminate** is a 30%-wide fill sweeping the track over 1,200ms, used only for steps with
no measurable progress (bundle expansion, hashing). Under reduced motion it becomes a static 30%
fill with the state named in the caption.

A 2px page-level indeterminate bar under the top bar marks route transitions over 300ms, in
`--text-link` rather than `--neutral-solid`, so navigation reads differently from work.

**Quota meter** (11.25, and the sidebar foot at ≥90%): the same track at 8px, fill
`--neutral-solid` below 80%, `--state-warning-solid` at 80–94%, `--state-danger-solid` at ≥95%,
with the caption `412 GB of 500 GB used · 88%`. The colour change is accompanied by a matching
banner, never by colour alone.

### 13.6.26 Pagination (cursor-based)

Share's list endpoints are cursor-paginated (§5.7). **There are no page numbers, no "page 3 of
12", no jump-to-page, and no total-page count anywhere in the product**, because the API cannot
produce them without a count query this instance does not run.

Two forms:

**Load more** — the default for tables and lists. A full-width `secondary` `--control-md` button
beneath the table labelled `Load more`, with a `--type-sm` `--text-tertiary` caption above it:
`Showing 50 artifacts`. Loading swaps the label for a spinner and `Loading…`. When the cursor is
exhausted the button becomes a `--type-sm` `--text-tertiary` line: `End of list · 137 artifacts`.
New rows append with no scroll jump and no entrance animation.

**Newer / Older** — for timelines where position matters: the audit log (11.23) and the view
history on 11.7. A right-aligned pair of `secondary` `sm` buttons, `[chevron-left] Newer` and
`Older [chevron-right]`, with the window's range between them at `--type-sm` `--text-tertiary`
(`24 Aug, 09:00 – 24 Aug, 15:04`). Each is disabled when its cursor is null.

Page size is 50 and is not user-configurable. Cursors live in the URL query string, so a
paginated view is linkable and survives a reload.

### 13.6.27 Destructive-confirmation dialog

A `sm` (400px) dialog variant used for every irreversible act.

```
┌──────────────────────────────────────────────┐
│ ⚠  Delete this artifact permanently?      ✕  │  header: 16px octagon-alert in
│                                              │  --state-danger-fg + --type-h2
│  This removes postcal, its 6 versions, and   │  body: --type-body, names the
│  its files. Anyone holding a link to it will │  object and the consequence,
│  get "not found" immediately. This cannot be │  at most 3 sentences
│  undone.                                     │
│                                              │
│  Type the artifact name to confirm           │  label --type-sm
│  ┌────────────────────────────────────────┐  │
│  │ postcal                                │  │  monospace Input
│  └────────────────────────────────────────┘  │
│                                              │
│                 [ Cancel ] [ Delete forever ]│  footer: secondary + danger
└──────────────────────────────────────────────┘
```

| Rule | Detail |
| --- | --- |
| Typed confirmation | Required for: permanently deleting an artifact from the trash, emptying the trash, deleting a version, revoking every API token at once, removing a user, and deleting an account. The user types the object's **name or handle** exactly — case-sensitive, whitespace-trimmed. Paste is allowed. |
| Confirm button | `danger` variant, disabled until the typed value matches exactly, labelled with a verb plus the object noun (`Delete forever`, `Empty trash`, `Remove user`). Never `Confirm`, `OK`, or `Yes`. |
| Cancel | `secondary`, listed first, always focusable. The text input takes initial focus so the flow is deliberate without being obstructive. |
| Escape / overlay | `Escape` closes. The overlay does **not** close on click. |
| Consequence sentence | Mandatory, and it must name what stops working for other people. For anything with live links, it says so explicitly and states the number: "2 live links will stop working." |
| What does NOT use this | **Moving an artifact to the trash** — reversible for 30 days, so it is one click with an undo toast. **Revoking a link** — one click, no dialog, undo toast (§13.6.17). **Revoking a grant** — one click. Narrowing access is never obstructed (D5). |

The create-link dialog (11.13) is this dialog's mirror image: the same weight, the opposite
colour. A `warning` banner naming what a link means, a required TTL select defaulting to 14
days, a password choice, an optional label, and a footer showing the resulting sharing-state
indicator in `solid` beside the share URL. Confirm is `primary`, labelled `Create link`.

### 13.6.28 Artifact thumbnail and kind placeholder

**Share never opens an artifact's files** (P5, G8). There is no thumbnailing, no first-page
render, no video poster frame, no image downscale, and no colour extraction. Every artifact is
represented by its **kind icon** on a neutral tile, and nothing else. This is a privacy
guarantee expressed as a design decision, and no future "just for images" exception is
permitted — the moment one kind gets a content-derived preview, the guarantee is gone and the
UI stops being a truthful description of what the server does.

Tile: square, `--radius-sm`, `--bg-sunken`, 1px `--border-subtle`, with the kind icon centred in
`--text-tertiary`. Sizes 20px (compact rows, icon 12px), 32px (default table rows, icon 16px),
48px (stacked-row cards and the 11.7 header, icon 24px), 64px (the viewer's `file` fallback,
icon 32px).

| Kind | Icon | Tile note |
| --- | --- | --- |
| `bundle` | `folder-open` | The only kind whose tile carries a `--type-2xs` file count at the bottom-right, e.g. `4` |
| `page` | `file-code-2` | |
| `document` | `file-text` | |
| `image` | `image` | |
| `video` | `file-video` | |
| `file` | `file` | The fallback; also used when `kind` is missing |

The tile never carries state colour, never animates, and is never a link on its own — the row or
card around it is the target. On R2 the same tile appears at 64px above the download button,
because the recipient also has no preview, for the same reason.

### 13.6.29 Avatar

Square at `--radius-full`, sizes 20 / 24 / 32 / 40px. The content is 1–2 initials at `--type-xs`
weight 500 (≤24px) or `--type-sm` weight 500 (above), on a tint derived by hashing the user id
into one of the six `--chart-*` families, with the text in the matching foreground. Never a
gradient, never a photograph — Share stores no avatars and fetches no Gravatar, which would be
an outbound request describing who uses this instance.

Non-human actors render an icon instead of initials, which matters most in the audit log where
distinguishing "the owner did this" from "an agent token did this" from "the expiry sweep did
this" is the whole point:

| Actor | Icon |
| --- | --- |
| API token (`actor_type='token'`) | `key-square` |
| System (`actor_type='system'`) | `server-cog` |
| Recipient via a share link | `link-2` |

Groups overlap by 8px with a 2px `--bg-surface` ring on each, capped at 4 plus a `+3` counter
chip. Used on the grants list (11.12) and the users screen (11.22).

### 13.6.30 Tooltip

`--neutral-solid` background, `--neutral-solid-text` text, `--type-xs`, padding 6px 8px,
`--radius-md`, `--shadow-md`, `max-width: 280px`, `--z-tooltip`. No arrow. Offset 6px from the
trigger, flipping on collision.

Delay: 400ms to open on hover, 0ms on keyboard focus, 100ms to close. Grouped triggers share a
150ms skip-delay so moving along a toolbar does not re-wait.

Tooltips are **never interactive** and contain no links or buttons. They never carry information
available nowhere else (D4) — an icon-only button's tooltip duplicates its `aria-label`, it does
not extend it. Attached with `aria-describedby`. Coarse pointers get no tooltips at all, so
every icon-only control must be reachable another way there.

The one permitted content extension is the relative-time hint on an absolute timestamp
(§13.9.2), because the absolute form is present in the DOM and the tooltip only restates it in a
second form.

---

## 13.7 Iconography

**Set: [Lucide](https://lucide.dev), version 0.4x, ISC licence.** Consumed as `lucide-react`
with per-icon imports so the bundle carries only what is used. Chosen for its consistent 24×24
stroke grid, a licence permitting redistribution with no in-UI attribution, and coverage of
every concept below without a single custom drawing. Recipient-facing pages inline the two or
three SVG paths they need directly into the template (§13.11.4) rather than loading the library.

| Property | Value |
| --- | --- |
| Grid | 24×24 viewBox, always |
| Rendered sizes | 12px (badges, chips, tree chevrons), 14px (inline with `--type-sm`, copy controls), **16px (default** — buttons, menu items, inputs, table cells), 20px (page-header actions, banner icons), 24px (48px thumbnails), 32px (empty states, 64px thumbnails) |
| Stroke width | `2` at 12–14px, **`1.75` at 16–20px**, `1.5` at 24–32px. Set explicitly per size; never left at the library default across every size. |
| Colour | `currentColor`, always. An icon never carries its own hex value. |
| Caps / joins | `round` / `round` — the Lucide default, unchanged |
| Alignment | Optically centred. Icons in a text row use `flex-shrink: 0` and `vertical-align: -0.125em` when inline. |
| Accessibility | `aria-hidden="true"` whenever a text label is adjacent. An icon-only control carries `aria-label` on the **control**, not on the icon. |

No other icon set may be introduced. The only non-Lucide SVG in the product is the Share
wordmark in `/assets/brand/`.

### 13.7.1 Concept → icon map

| Concept | Lucide icon | Notes |
| --- | --- | --- |
| **private** (state) | `lock` | Also the icon of the *revoke everything* action — the verb wears the state it produces. |
| **shared with people** (state) | `users` | Plural, always. A single grant still uses `users`, never `user`, so the state icon is stable at every count. |
| **link active** (state) | `link-2` | Never `globe`, never `share-2`. `globe` would imply the artifact is on the open internet; it is not, it is behind a 128-bit capability. |
| **unknown** (state) | `circle-help` | Only ever in `--share-unknown-*`. |
| **expiring soon** | `timer` | The same icon above and below 48h; only the colour family changes. |
| **expired** | `timer-off` | Also the R3 page's single icon. |
| **password** | `key-round` | The link modifier chip, the R1 gate, and the shown-once password block. |
| **artifact** (generic) | `package` | The object. Sidebar, empty states, search results. |
| **kind: bundle** | `folder-open` | |
| **kind: page** | `file-code-2` | |
| **kind: document** | `file-text` | |
| **kind: image** | `image` | |
| **kind: video** | `file-video` | Never `play` — this is a file, not a player. |
| **kind: file** | `file` | The fallback. |
| **version** | `git-commit-horizontal` | A single version. The versions *list* and tab use `history`. |
| **trash** | `trash-2` | The screen, the verb "Move to trash", and the `In trash` badge. |
| **restore** | `rotate-ccw` | Restoring from trash and rolling back to an older version. |
| **copy** (clipboard) | `copy` | Swaps to `check` on success. |
| **copy to my space** (duplicate) | `copy-plus` | Deliberately distinct from clipboard copy; §7.7.1's action, and the two appear in the same menu. |
| **tag** | `tag` | |
| **token** (API token) | `key-square` | Square, versus `key-round` for a link password. The two never appear on the same screen. |
| **passkey** | `fingerprint` | Never a key icon — a passkey is not a token, and the audit log must not blur them. |
| **session** | `monitor-smartphone` | A signed-in device on 11.19. |
| **audit** | `scroll-text` | |
| **search** | `search` | |
| **upload** (post) | `upload` | The verb for putting bytes in — never "publish", and never a globe. |
| **download** | `download` | |
| **grant** (verb: share with a user) | `user-plus` | |
| **revoke** (verb: link or grant) | `circle-slash` | The same icon for both, because they are the same act — ending someone's access — and reusing it makes the pattern learnable. Rendered in `--text-secondary`, not red (§13.6.1). |
| **user** | `user-round` | The users *list* (11.22) uses `users-round`. |
| **quota / storage** | `hard-drive` | The screen, the meter's label, and the over-quota banner. |
| **stale** (not opened recently) | `clock-alert` | Screen 11.24 only. |
| **agent** | `bot` | The help page (11.27) and any row whose actor is a token acting on an agent's behalf. |

Supporting icons, fixed by convention and used nowhere unexpected: `check` (success, selected),
`circle-check` (success banner), `triangle-alert` (warning), `octagon-alert` (danger, error),
`info` (info banner), `settings` (settings), `eye` / `eye-off` (show or hide a password),
`folder` / `file` (file tree), `arrow-up-right` (opens in a new tab), `ellipsis` (overflow
menu), `chevron-*` (disclosure and sort), `x` (dismiss), `plus` (create), `corner-down-right`
(entry point), `server-cog` (system actor), `loader-circle` (spinner), `panel-left` (sidebar
collapse), `sun` / `monitor` / `moon` (the theme control).

---

## 13.8 Motion

### 13.8.1 Tokens

```css
--duration-instant:    0ms;
--duration-fast:     120ms;   /* hover, focus, checkbox, toggle thumb */
--duration-base:     180ms;   /* the default: fades, colour swaps, toasts */
--duration-slow:     240ms;   /* drawers, progress fill, tree expansion */
--duration-deliberate: 320ms; /* nothing in phase 1; reserved */

--ease-standard: cubic-bezier(0.2, 0, 0, 1);     /* on-screen movement */
--ease-out:      cubic-bezier(0.16, 1, 0.3, 1);  /* entering */
--ease-in:       cubic-bezier(0.4, 0, 1, 1);     /* exiting */
--ease-linear:   linear;                          /* spinners and indeterminate bars only */
```

### 13.8.2 What animates

| Thing | Animation |
| --- | --- |
| Hover, focus, pressed | `background-color`, `border-color`, `color`, `box-shadow` over `--duration-fast --ease-standard` |
| Dialog | Overlay `opacity` 0→1 over `--duration-base`. Panel `opacity` 0→1 with `scale(0.98)→1` and `translateY(4px)→0` over 200ms `--ease-out`. Exit 120ms `--ease-in`, no scale. |
| Drawer | `translateX(100%)→0` over `--duration-slow --ease-out`; exit `--duration-base --ease-in` |
| Dropdown, popover, tooltip | `opacity` plus `scale(0.96)→1` from the trigger-adjacent origin, `--duration-fast --ease-out` |
| Toast | `translateY(8px)→0` plus fade, `--duration-base --ease-out`; exit is fade only |
| Tree and accordion expansion | `height`, via `grid-template-rows`, over `--duration-slow --ease-standard` |
| Sharing-state change | Badge cross-fade `--duration-base`; the row or header flashes `--bg-selected` → transparent over 600ms |
| Route change | `opacity` 0→1 on the content region only, `--duration-fast`. The shell never animates. |
| Spinner | `rotate` 360° over 800ms, `--ease-linear`, infinite |
| Indeterminate progress | `translateX` sweep over 1,200ms, `--ease-standard`, infinite |
| Skeleton shimmer | `background-position` over 1,400ms, `--ease-linear`, infinite |

### 13.8.3 What must not animate

- **The sharing-state indicator must never pulse, glow, blink, or loop.** A throbbing
  link-active badge would be noise within an hour and ignored within a day, and the whole design
  depends on it still being noticed in month six. It changes once, calmly, and then holds still.
- **Nothing in the viewer animates.** No fade-in on the artifact, no transition between files in
  a bundle, no zoom easing on an image. Rendered content appears when it is ready; an animation
  over somebody else's document is the chrome talking over the content (D3).
- Numbers never count up. A stat tile renders its final value; view counts and quota figures
  appear at rest.
- Table rows do not animate on sort, filter, or reorder, and rows appended by "Load more" do not
  slide in.
- Nothing animates on scroll: no parallax, no reveal, no sticky-header height change.
- Skeletons never cross-fade into content — the swap is instantaneous, and invisible because the
  boxes are the same size.
- No page-load or first-mount animation of any kind.
- Buttons do not scale, lift, or ripple on press. They change background colour.

### 13.8.4 Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

With these exceptions, implemented as explicit overrides rather than by weakening the rule:

1. **Opacity-only transitions stay, at 100ms.** Fading is not vestibular motion, and an
   instantaneous dialog is disorienting in a different way.
2. **All `transform` is removed** — dialogs, drawers, toasts, and menus appear at their final
   position with a fade only.
3. **The spinner keeps rotating.** It is small, local, and the only remaining signal that
   something is happening. Every other infinite animation stops.
4. **The indeterminate progress bar** becomes a static 30% fill with the state in its caption.
5. **The sharing-change row flash** becomes a 2px `--focus-ring-color` left border held for 3
   seconds.
6. **The skeleton shimmer** becomes a flat `--bg-sunken`.

The preference is also read through `matchMedia` so behaviour can branch and not just CSS —
"Load more" scroll management uses `auto` rather than `smooth`.

---

## 13.9 Data display conventions

Rendering rules, not suggestions. Two screens showing the same value must show identical
characters.

### 13.9.1 Byte sizes

Base 10 — `KB` is 1,000 bytes — matching what the disk vendor and the host's dashboard say.
Never `KiB` in the UI. The API always returns raw integers.

| Range | Format | Example |
| --- | --- | --- |
| 0 | `0 bytes` | `0 bytes` |
| 1–999 | integer + ` bytes` | `812 bytes` |
| < 10 of a unit | one decimal | `9.4 MB`, `1.0 KB` |
| ≥ 10 of a unit | no decimals | `24 MB`, `147 KB` |
| ≥ 1,000 of a unit | promote | `1,204 MB` → `1.2 GB` |

Units: `bytes`, `KB`, `MB`, `GB`, `TB`, always space-separated, always `tabular-nums`,
right-aligned in tables. A summed size — a version total, an artifact total, the trash total —
renders identically and never with a `~`, because Share knows these numbers exactly.

**Deduplicated sizes are labelled.** Because identical bytes are stored once instance-wide
(§1.7, principle 7), an artifact's displayed size is the size of its files, while the quota
figure counts unique bytes. Where the two appear together the smaller carries a `--type-sm`
`--text-tertiary` note: `24 MB · 3 MB unique`. Never one number pretending to be both.

### 13.9.2 Dates and times

Absolute: **`24 Aug 2026, 15:04`** — day, abbreviated month, four-digit year, comma, 24-hour
clock, in the viewer's local zone. The year is omitted within the current year
(`24 Aug, 15:04`). Seconds appear only in the audit log, as `15:04:32`.

Relative: `just now`, `4 min ago`, `3 hr ago`, `2 days ago`, `6 days ago`; future forms
`in 4 min`, `in 6 days`. Never "yesterday", never "a while ago", never "recently".

| Where | Rendering |
| --- | --- |
| Table timestamp columns (created, updated, last opened) | Relative within 7 days, absolute beyond. The `title` attribute always carries the full ISO 8601 UTC value. |
| Audit log (11.23) | **Always absolute, with seconds.** An audit trail with relative times is not a trail. |
| Version list | Relative within 7 days, absolute beyond, plus the actor. |
| View counts by day (11.7) | Absolute dates, always. |
| Trash | `Deleted 2 days ago · removed permanently on 23 Sep 2026, 00:00` — relative for the past act, absolute for the deadline. |
| **Any expiry** | **Always absolute, with the relative form as a parenthetical hint.** |

**The expiry rule.** Anywhere a share link's expiry appears — the expiry chip, the artifact
header, the create-link dialog, the sharing panel, the expiring-soon banner, the email in §12.9,
a rendered API response — the primary rendering is the absolute datetime. The relative form may
follow in parentheses in `--text-tertiary`, but never replaces it.

```
Expires 7 Sep 2026, 18:04 (in 6 days)      ✓
Expires in 6 days                           ✗
Expires in 6 days (7 Sep 2026, 18:04)       ✗   — the absolute form must lead
```

"In 6 days" is a fact about *now*, and this screen may be read tomorrow, screenshotted today, or
pasted into an email on Friday; only the absolute form survives being moved. In the expiry chip,
where space is tight, the parenthetical drops to the tooltip — the absolute form stays.

Time zone: rendered local, with the zone abbreviation appended for **expiries and audit
timestamps** (`7 Sep 2026, 18:04 BST`) and omitted elsewhere. Every timestamp's `title` carries
the ISO 8601 UTC string, and every `<time>` element carries a machine-readable `datetime`.

### 13.9.3 Durations

| Range | Format | Example |
| --- | --- | --- |
| < 1,000 ms | integer + ` ms` | `340 ms` |
| 1–60 s | one decimal + ` s` | `1.2 s` |
| 1–60 min | `Xm Ys` | `2m 05s` |
| ≥ 1 hr | `Xh Ym` | `3h 12m` |
| ≥ 1 day (TTLs, retention) | `X days` | `14 days` |

TTL **inputs** use the API's duration strings verbatim, in monospace — `30m`, `24h`, `14d`,
`180d` — so what the dashboard shows is exactly what someone would type into the CLI. TTL
**outputs** in prose use the long form: "This link lasts 14 days."

### 13.9.4 Counts

Locale thousands separators (`1,204`). **Never abbreviated in tables** — a cell reading `12.4k`
cannot be reconciled against an export. Abbreviation (`12.4k`, `1.2M`) is permitted only in stat
tiles, with the exact value in the tooltip. Zero renders as `0`, never an em dash and never
"None". A count that is a pagination lower bound renders `50+`, never `~50`.

**View counts** carry their unit because they are estimates of people, not requests:
`14 views · 6 viewers` where the first is a request count and the second is the
HyperLogLog-derived distinct-viewer estimate for the day (§10.6). The viewer figure always
carries the tooltip "An estimate. Share does not store who viewed this." Never a precise-looking
number for an estimated quantity, and never a viewer list, which does not exist and cannot be
made to exist.

### 13.9.5 Empty and null values

A genuinely absent value renders as an em dash `—` in `--text-tertiary` with
`aria-label="not set"`. Never `N/A`, never `null`, never `-`, and never an empty cell — an empty
cell is indistinguishable from a rendering failure.

A value absent *because a feature is off* renders the reason instead, at `--type-sm`
`--text-tertiary`: `No password`, `No description`, `Never opened`, `No links yet`.

A value absent *because we could not fetch it* renders `Unavailable` in `--state-danger-fg` with
a 12px `octagon-alert`. This case is never allowed to look like either of the two above, for the
same reason `unknown` exists on the sharing-state indicator.

### 13.9.6 Truncated names, tokens, and paths

| Kind | Rule |
| --- | --- |
| **Artifact name** | **Never truncated.** The name is the artifact's identity and the thing someone types into the CLI or the address bar. If a column cannot fit it, the column widens and something else gives. |
| **Share token** | First 8 and last 4 of the 22 base58 characters: `9fq2n4kw…TvQ8`. Both ends survive because a person comparing a token against an email checks the ends first. Full value in the `title` and in whatever the copy control copies. |
| **API token** | Prefix plus the last 4: `shr_…4f2a`. The middle is never shown after creation because the server does not have it. |
| **SHA-256** | First 7 characters, monospace: `9f2a1c4`. Full value in the `title`. Never the last N characters. |
| **Prefixed ID** | Prefix plus the first 6 of the ULID plus `…`: `lnk_01JAV3…`. The prefix always survives so the object type stays readable. |
| **File path** | Middle truncation preserving the full basename: `assets/…/app.css`. The filename is never truncated. |
| **Title, description, link label** | CSS `text-overflow: ellipsis` on one line, full value in a tooltip. This is the **only** place CSS truncation is permitted. |

Identifier truncation happens **in code, not in CSS**, so the DOM holds the truncated string and
a mouse selection yields exactly what is visible. The full value stays reachable through the
adjacent copy control, which always copies the untruncated string (§13.6.20).

### 13.9.7 URLs

Rendered in `--font-mono`, `--text-primary`, with the `https://` scheme **omitted** and any other
scheme shown. The path is included when non-root. A trailing slash on a root URL is dropped.

```
share.c52.com/postcal
share.c52.com/~sarah/q3/market-report
share.c52.com/s/9fq2n4kw…TvQ8
```

Every URL carries a copy control and, when reachable by the current viewer, an `arrow-up-right`
icon button opening it in a new tab with `rel="noopener noreferrer"`.

**The canonical URL and a share URL are always labelled and never adjacent without labels.** A
`--type-xs` `--text-tertiary` label sits above each (`Artifact URL` / `Share URL`), and the share
URL's copy field carries a 3px `--share-link-solid` left border. The distinction matters because
the two look similar and do entirely different things: one needs a sign-in, one is a bearer
credential that works for anyone. Sending the wrong one is the most consequential slip available
in this product, and labelling is the cheapest defence against it.

An unreachable URL — the artifact is trashed, the link is expired — renders at `--text-tertiary`
with the matching state badge and no open-in-new-tab button. It is not hidden; the owner needs to
know the address still exists and is dead.

---

## 13.10 Writing-in-UI rules that affect layout

Part 12 owns the words. These are the rules that constrain the boxes they go in; breaking one of
these breaks layout, not just tone.

**Sentence case everywhere** — buttons, headings, labels, column headers, menu items, tabs,
badges, toasts, dialog titles. Never Title Case, never ALL CAPS, never small caps. Capitalised:
the first word, proper nouns (Share, Postgres, Caddy, WebAuthn), and the sharing-state labels
**Private**, **Shared with n people**, **Link active**, and **Unknown**, which are capitalised as
state names in every position including mid-sentence.

**Button labels: 1–3 words, ≤24 characters, verb first.** `Create link`, `Revoke link`,
`Copy share URL`, `Move to trash`, `Load more`, `Delete forever`. Forbidden: `OK`, `Yes`, `No`,
`Submit`, `Click here`, and any label that does not name what happens. A label that will not fit
in 24 characters is naming two actions. **Buttons never wrap** — a button that would wrap is a
spec violation, and the fix is a shorter label, not a wider button. No trailing ellipsis on a
button that opens a dialog; that is a desktop convention this product does not use.

**Length caps.** Labels ≤3 words. Column headers ≤2 words. Section headings ≤5 words.
Empty-state headings ≤6 words. Empty-state bodies ≤2 sentences. Tooltips ≤80 characters. Toast
titles ≤60 characters; toast bodies wrap to at most 2 lines. Banner titles ≤60 characters.

**Field errors attach to the field.** The message renders directly beneath the field, 6px below,
at `--type-sm` in `--state-danger-fg`, preceded by a 14px `circle-alert`, with the field's border
switched to `--state-danger-solid` and `aria-invalid="true"` plus `aria-describedby` wired to the
message's id.

The message slot is a permanently reserved `min-height: 18px` box beneath every field, so showing
or clearing an error never reflows the form — this matters most in the create-link dialog, where a
reflow would move the confirm button under the cursor. The error **replaces** the helper text;
they never stack, and the helper text returns when the error clears. Messages wrap rather than
truncate, growing the slot downward.

Error text names the constraint and the fix in one sentence, without "Please" and without
"invalid" standing alone: `Names use lowercase letters, digits, hyphens, and slashes.`
`Passwords need at least 8 characters.` Server errors are mapped through §12.8; a raw API `code`
never reaches a field.

**Form-level errors** (request failed, quota exceeded, conflict) render as a `danger` banner at
the top of the form, inside the same scroll container, scrolled into view. On a server-side
validation failure, focus moves to the first invalid field and the banner summarises:
`2 fields need attention.`

**Terminology enforcement.** Per §12.2 the UI says *artifact*, *name*, *title*, *share link*,
*grant*, *revoke*, *post*, *version*, *trash*, *token*, *passkey*, *recipient*. It never says
*public*, *publish*, *deploy*, *go live*, *unpublish*, *file share*, *permissions*, *access
level*, or *visibility setting*. This is a layout rule as much as a copy rule: the alternatives
are different lengths and would break the fixed widths above, and "public" in particular would
misdescribe the guarantee (§13.6.8.1).

---

## 13.11 Implementation notes

### 13.11.1 Stack

**React 18 + TypeScript + Vite, with Radix UI primitives, plain CSS custom properties and CSS
Modules, TanStack Query for server state, and `lucide-react` for icons.**

Radix is chosen because this spec demands correct focus trapping, roving tabindex,
collision-aware positioning, and ARIA wiring across dialog, drawer, dropdown, select, tabs,
tooltip, and toast — seven components that are expensive to get right, unacceptable to get wrong,
and which Radix ships unstyled, leaving §13.6 the only source of visual truth. Plain CSS custom
properties rather than a utility framework is chosen because the same token block must be
**inlined verbatim** into the R1–R7 pages — Jinja templates emitted by FastAPI with no build
step, no JavaScript, and an 8 KB budget — and a utility framework's output cannot cross that
boundary while a token file can.

Supporting choices: React Router (URL-driven tabs, cursors, and filters), `zod` for form and
response validation, and no CSS-in-JS runtime. The initial-route budget is **250 KB gzipped**;
the syntax highlighter lazy-loads on the help and file-viewer routes only.

### 13.11.2 How tokens are consumed

`design/tokens.json` is the single source of truth. A build step (`npm run tokens`) emits three
artefacts and fails the build if any of them would drift:

1. `src/styles/tokens.css` — the complete three-layer block from §13.2.4.
2. `src/styles/tokens.d.ts` — a union type of every token name, so `var(--typo)` fails to
   compile.
3. `api/share/templates/_tokens.css.j2` — the recipient-page subset (surfaces, text, borders,
   focus, danger, password, expired), minified, for inlining.

Rules enforced in CI:

- **No raw colour values in component CSS.** `stylelint` blocks
  `/#([0-9a-fA-F]{3,8})\b|\brgba?\(/` outside `tokens.css`. One rule, no exceptions list.
- **No raw spacing values.** `declaration-property-value-allowed-list` restricts `padding`,
  `margin`, and `gap` to `var(--space-*)`, `0`, `auto`, and percentages.
- **Contrast is a test.** A Node script reads `tokens.json`, recomputes every pair in §13.2.5,
  and fails on any regression below its stated threshold.
- Components consume tokens through the global stylesheet only. There is no per-component theme
  object and no JavaScript token access except `getComputedStyle` where a chart needs a resolved
  colour.
- Tokens are additive-only within a phase; a rename ships with its codemod in the same commit.

### 13.11.3 Theme switching

Three states, in exactly this model:

| Setting | `data-theme` on `<html>` | Result |
| --- | --- | --- |
| `system` (**default**) | *no attribute* | `prefers-color-scheme` decides, live, with no reload |
| `light` | `data-theme="light"` | Light even on a dark OS — the `:not([data-theme="light"])` guard excludes the media block |
| `dark` | `data-theme="dark"` | Dark even on a light OS — the third block re-applies the overrides |

Mechanics:

1. The preference is stored in `localStorage` under `share.theme` **and** mirrored to a
   `share_theme` cookie (`SameSite=Lax`, `Secure`, `Path=/`, `Max-Age=31536000`, carrying nothing
   else), so the server can render R1–R7 in the chosen theme without JavaScript.
2. A blocking inline script in `index.html`'s `<head>`, before any stylesheet, reads that value
   and stamps `data-theme` when it is `light` or `dark`. About ten lines, wrapped in `try/catch`
   because private-mode browsers throw on storage access, and stamping nothing by default. This
   prevents the light-flash on a dark-OS reload.
3. `<meta name="color-scheme" content="light dark">` so native controls, scrollbars, and the
   address bar follow before CSS loads.
4. The top-bar control is a three-position segmented control (`sun` / `monitor` / `moon`), not a
   switch — `system` must be visible and selectable, and a binary toggle cannot express it.
5. Because `system` stamps no attribute, an OS switching to dark at sunset repaints the dashboard
   live. Nothing listens for a media-query change; the CSS does it.

The two dark blocks are generated from one source object, so a token cannot land in one and not
the other.

### 13.11.4 JavaScript: the dashboard versus the recipient pages

**The dashboard (11.1–11.28) requires JavaScript.** It is an authenticated operator tool behind a
passkey sign-in; a no-JS fallback would double the surface area for no user. Without JavaScript
it renders one centred `danger` banner from `<noscript>` saying so and linking to the CLI docs.

**Pages R1–R7 must work with JavaScript entirely disabled and must make no external request of
any kind.** This is a hard requirement, tested in Part 14.

| Page | No-JS behaviour |
| --- | --- |
| R1 Password gate | `<form method="post" action="/s/{token}/unlock">` with one password field and a submit button. `302` on success; re-renders with a field error on failure. No show/hide toggle, no strength meter. |
| R2 Share landing (non-HTML) | Static: the title if one is set, the kind tile, the byte size, a view link, and a download link. No name, no handle, no state indicator. |
| R3 Link expired or revoked | Static. One `timer-off` icon, one sentence, nothing else — it must reveal nothing about the artifact or its owner (§7.6). |
| R4 Not found · R5 Rate limited · R6 Maintenance | Static content, no interaction. R6 is served by Caddy from disk when the API is down, so it carries its own copy of the inlined CSS. |
| R7 File listing | A static `<ul>` of name, size, and type, each a plain link under `/s/{token}/…`. Sorted server-side. No tree, no JavaScript, no sorting controls. |

Construction rules, following from §6 and §1.6:

- **One inlined `<style>` block** — `_tokens.css.j2` plus roughly sixty lines of layout. No
  external stylesheet, no `<script>` of any kind, under **8 KB total** including the SVG. The
  budget is asserted by a byte-count test on the rendered output of every one of R1–R7.
- **No web fonts.** The system stack only. A request to a font CDN from R1 would tell a third
  party that a specific viewer, at a specific time, opened a specific person's private link —
  precisely the leak this product exists to close. That is also why Inter is self-hosted in the
  dashboard (§13.3.1): one rule everywhere.
- **No images, no favicons fetched from elsewhere, no analytics, no preconnect, no prefetch.**
  The only graphic is a single inline `<svg>` per page, with its path data pasted into the
  template.
- Theme comes from the `share_theme` cookie when present, otherwise `prefers-color-scheme`. Both
  dark blocks are present in the inlined CSS, so an explicit choice still wins.
- **No sharing-state indicator, no artifact name, no owner handle, no tags, no version count,
  no expiry** on any of R1–R7. These pages inherit tokens, type, and spacing from this design
  system, and nothing else. A recipient learns what they were given and not one fact more.

### 13.11.5 Accessibility baseline

Every screen ships meeting these, and Part 14 asserts them:

- WCAG 2.1 AA contrast for all text and all non-text indicators, per the §13.2.5 audit, in both
  themes.
- A visible `:focus-visible` ring on every interactive element; no `outline: none` without an
  equally visible replacement.
- Full keyboard operability — the file tree, the command palette, tables with row actions, the
  viewer, and every dialog. No positive `tabindex` anywhere.
- Landmarks: one `<nav>` (sidebar), one `<main>` (content region), one `<header>` (top bar), and
  a "Skip to content" link as the first focusable element.
- Every state conveyed by colour is also conveyed by an icon and a word (D4), including in
  print and in greyscale.
- `prefers-reduced-motion` honoured per §13.8.4.
- Live regions used sparingly: toasts (`polite`), form-error summaries (`assertive`), copy
  confirmations (`polite`), and the sharing-state indicator on the three screens named in
  §13.6.8.7. Nowhere else.
- Usable at 200% zoom and at 320px CSS width with no horizontal page scrolling — wide tables
  scroll inside their own container, never the body.
- The viewer's `iframe` carries `title="Artifact content"` so a screen reader announces the frame
  boundary, and the sandboxed content is never made a focus trap.
