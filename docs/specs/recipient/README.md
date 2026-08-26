# Recipient-facing pages — R1–R7

Ten files, seven pages. Each is a complete HTML document: **inline CSS, no JavaScript, no
external requests, no dashboard chrome** (13.8). Serve them as they are.

| File | Page | Status |
| --- | --- | --- |
| `R1-password-gate.html` | R1, first view | 401 |
| `R1-password-gate-wrong.html` | R1, wrong password | 401 |
| `R1-password-gate-limited.html` | R1, rate limited | 429 |
| `R2-landing.html` | R2, renderable | 200 |
| `R2-landing-unrenderable.html` | R2, unrenderable | 200 |
| `R3-expired.html` | R3 | 410 |
| `R4-not-found.html` | R4 | 404 |
| `R5-rate-limited.html` | R5 | 429 |
| `R6-maintenance.html` | R6 | 503 |
| `R7-file-listing.html` | R7 | 200 |

## The style block is byte-identical across all ten

This is the security requirement, not a tidiness one: page identity must not be inferrable from
CSS differences, which is what makes R4's blanket 404 hold against an attacker comparing
responses (13.8.1, P1).

It follows that **the style block is one template constant**, emitted verbatim into every page.
Classes unused by a given page are still present. Do not prune per page, do not minify one and
not another, and do not let a build step reorder declarations for one route. If a page needs a
new rule, it goes into the shared block and every page gets it.

The same applies to the surrounding document: same `<head>` order, same `<div class="w">`
wrapper, same wordmark paragraph. Only the `<title>` and the body content differ, and only R2
and R7 vary their `<title>` at all.

## What is deliberately absent

- **No webfont.** Body is `Georgia, "Times New Roman", Times, serif`; identifiers are the
  system monospace stack. A blocked font cannot change these pages (13.8.2). The dashboard's
  Source Serif 4 never reaches here.
- **No JavaScript.** R1 is a plain `<form method="post">`. There is no auto-refresh anywhere,
  and R6 in particular renders with Postgres, Redis and the API all gone (13.8.2).
- **No favicon, no image, no icon, no logo, no preconnect.** Every page makes exactly one
  request: itself.
- **`noindex, nofollow`** on all ten.
- No link to the dashboard, no owner handle, no instance-owner name, and no sign-in prompt —
  offering one would tell a scanner that signing in might help (12.7, R4).

## Sizes and typography

Everything is in `em` off a 19px root, so 200% zoom and a user's own font size both work
without a media query. The measure is `34em` with a `30em` paragraph limit; at 320px the
padding collapses to the viewport and nothing overflows — the widest fixed thing on any page is
a 20em input capped by `max-width`, and long identifiers in R7 use `word-break: break-all`.

Verified at 320px, at 200% zoom, and with author styles disabled: each page reduces to a
hostname, a heading, a paragraph and at most a form, in that order, which is why disabling CSS
costs nothing.

## Both themes — 13.7

`body` paints background and colour explicitly, because these pages inherit nothing from us.
Dark comes from `prefers-color-scheme` alone: with no JavaScript there is no toggle and no
stored preference, so the OS preference is the only signal available. `color-scheme: light dark`
is set so form controls follow.

## Values

Taken from `Foundations.dc.html`; if one moves there, it moves here too.

    paper   #f3f2f2   ink       #201e1d   secondary #605d5d
    link    #006786   danger    #9e2b1e   focus     #201e1d
    dark bg #1a1918   dark ink  #ece9e7   dark link #62c5ee

## R7's paths are relative

Every path is a relative link so it resolves under whichever address is in the bar, including
`/s/{token}/`. Sorted by path with directories grouped. No sorting controls, no search, no
download-all.

## Copy

Verbatim from `spec/12-copy.md` §12.7. Dynamic values are shown filled in with plausible
examples — `14 minutes`, `3 files · 2.4 MB`, `application/zip`. Substitute; do not rewrite.
R2's title line is omitted entirely when the owner set no title, and R7's heading falls back to
`name`, then to nothing when served through a share link.
