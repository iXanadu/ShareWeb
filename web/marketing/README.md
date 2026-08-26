# marketing/

Three static pages for the public base URL. Plain HTML, one inline style block per
page (byte-identical across all three), no JavaScript, no webfonts, no external
requests of any kind. Copy them into the repo as `web/marketing/` and serve them.

| File | Route |
| --- | --- |
| `index.html` | `/` |
| `how-it-works.html` | `/how-it-works` |
| `for-agents.html` | `/for-agents` |

Links between the pages are relative `.html` filenames, so the folder also works
opened straight off disk. If you serve them at the extensionless routes above,
rewrite the three `<a href>` sets or add a redirect.

## The site holds no documentation

There is deliberately no docs page. The nav's **Docs ↗** item leaves the site for
`docs/specs/spec/` on GitHub, and every documentation reference on every page is
an outbound link to the repository. GitHub is the live surface; nothing here has
to be republished when a spec file changes.

What that buys, and the rule it implies: **do not add a page to this folder that
restates anything the repo already says.** If a visitor needs detail, link to the
file. The three pages carry positioning only — what Share is, the shape of the
API, and how to point an agent at it.

`index.html` § "Where it stands" is a link list rather than a status paragraph for
the same reason: `BACKLOG.md`, the roadmap and the commit history report the
current state themselves.

## Serving notes

1. **Route order.** `server/routers/serve.py` registers a catch-all at
   `/{full_path:path}` and `main.py` includes it last. A marketing router must be
   included *before* `serve.router`, or the catch-all will try to resolve `/` as an
   artifact and 404.

2. **`robots.txt` currently blocks everything.** `serve.py` serves
   `User-agent: *\nDisallow: /`, which is right for artifacts and wrong for a
   marketing page. To let the marketing pages be indexed while artifacts stay
   private, allow only those four paths:

   ```
   User-agent: *
   Allow: /$
   Allow: /how-it-works
   Allow: /for-agents
   Allow: /docs
   Disallow: /
   ```

   The per-response `X-Robots-Tag: noindex, nofollow` on artifact responses is set
   separately in `serve_artifact` and does not apply to these pages. Leave it.

3. **The dashboard does not move.** It is already mounted at `/~` and `/~/*`, so
   the base URL is free. No change needed.

## Facts the copy asserts

Everything on the pages was taken from the code at `9ad462d`, not from the spec.
If any of these change, the copy is wrong:

- MCP is `/mcp` (JSON-RPC POST; GET is an SSE ping), bearer token `shr_…`, seven
  tools: `share_post`, `share_create_link`, `share_list`, `share_get`,
  `share_delete`, `share_restore`, `share_whoami`. Posting is private.
  `share_create_link` mints the `/s/` URL.
- Failed tool calls return tool content with `isError: true` and a
  `code: message` string, not a JSON-RPC error.
- The upload sequence is declare (`POST /api/v1/artifacts`) → `PUT` each returned
  signed URL → commit (`POST .../versions/{id}/commit`).
- Files are addressed by SHA-256, so unchanged files are not re-uploaded.
- `share post` refuses probable secrets unless `--force-secrets` is passed.
- Share links live at `/s/{token}/` and take a TTL, a label and an optional
  password.
- Unknown and unauthorized both return the same 404.
- Artifact responses carry CSP, `nosniff`, `noindex` and a strict referrer policy.

## Deliberately not claimed

- **No hosted service, and no status snapshot.** The pages never assert which
  phase is built or whether share.c52.com is up. That was a maintenance trap:
  BACKLOG SW-7 will close and the sentence would have gone stale. `index.html`
  links to `BACKLOG.md` and the commit history instead.
- **No MCP transport detail.** Per your call, the pages say MCP without
  specifying JSON-RPC-over-POST. If SW-4 stays open long-term, consider adding it
  — an agent framework expecting streamable HTTP/SSE will fail to connect and the
  page gives no warning.
- License is Apache 2.0 (confirmed from `LICENSE`). Footers name it.
- **No metrics, users or testimonials.** You had none to give.

## Design

Broadsheet: paper `#f3f2f2`, ink `#201e1d`, cyan `#006786` for interactive, magenta
`#d6006c` used once per page as the step numerals. Flush-left asymmetric column,
whitespace instead of dividers, with the one exception the system allows — the
thick-thin rule pair around the masthead dateline rail.

The serif is the system stack (`"Source Serif 4", Georgia, Times`), not a
webfont, matching `recipient/`. If you want the real Source Serif 4 on the
marketing pages, vendor the woff2 into `web/static/` and add an `@font-face` — do
not add a Google Fonts link to a product whose selling point is that you host it
yourself.
