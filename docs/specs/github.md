# Source repositories

## phosphor-icons/core

Icon assets only — this project does not build from a codebase. The Broadsheet design system
mandates Phosphor icons in the duotone weight, and the three sharing-state glyphs were taken from
the upstream SVGs rather than hand-drawn.

repo: phosphor-icons/core
branch: main
path: assets/duotone

## Last sync

date: 2026-08-26T03:37:19Z

### Updated in this project

- Read `lock-simple-duotone.svg`, `users-duotone.svg`, `link-duotone.svg` and inlined their path
  data into the three sharing-state badges.
- Replaced the hand-drawn geometry that stood in for them in `Foundations.dc.html` and
  `Screens.dc.html`.
- Recorded the icon choice in `spec/DECISIONS.md` D-18.

## Screen map

| Where | Built from |
| --- | --- |
| `Foundations.dc.html` § the three sharing states | `assets/duotone/lock-simple-duotone.svg`, `users-duotone.svg`, `link-duotone.svg` |
| `Screens.dc.html` — 11.5, 11.7 state badges | the same three files |
