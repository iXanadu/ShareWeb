# marketing/

Three static pages for the public base URL. They are **surface decoration
only**: positioning copy plus a rook/tiding-press look. They are not the
design system, not the spec, and not the dashboard or recipient pages.

| File | Route |
| --- | --- |
| `index.html` | `/` |
| `how-it-works.html` | `/how-it-works` |
| `for-agents.html` | `/for-agents` |
| `your-server.html` | `/your-server` |
| `site.css` | `/site.css` |
| `assets/` | `/assets/…` |

Links between the pages are relative `.html` filenames, so the folder also works
opened straight off disk.

## The site holds no documentation

There is deliberately no docs page. The nav's **Docs ↗** item leaves the site for
`docs/specs/spec/` on GitHub, and every documentation reference on every page is
an outbound link to the repository. GitHub is the live surface; nothing here has
to be republished when a spec file changes.

**Do not add a page to this folder that restates anything the repo already says.**
If a visitor needs detail, link to the file on GitHub. The three pages carry
positioning only — what Share is, the shape of the API, and how to point an
agent at it.

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
   marketing page. Allow only the public pages:

   ```
   User-agent: *
   Allow: /$
   Allow: /how-it-works
   Allow: /for-agents
   Allow: /your-server
   Disallow: /
   ```

   The per-response `X-Robots-Tag: noindex, nofollow` on artifact responses is set
   separately in `serve_artifact` and does not apply to these pages. Leave it.

3. **The dashboard does not move.** It is already mounted at `/~` and `/~/*`, so
   the base URL is free. No change needed. Recipient pages (`docs/specs/recipient/`)
   are a different surface and keep their own inline CSS.

## Facts the copy asserts

Everything on the pages was taken from the code, not from a design doc.
If any of these change, the copy is wrong:

- MCP is `/mcp` (JSON-RPC POST; GET is an SSE ping), bearer token `shr_…`, seven
  tools: `share_post`, `share_create_link`, `share_list`, `share_get`,
  `share_delete`, `share_restore`, `share_whoami`. Posting is private.
  `share_create_link` mints the `/s/` URL and requires the `share:create` scope.
- Failed tool calls return tool content with `isError: true` and a
  `code: message` string, not a JSON-RPC error.
- The upload sequence is declare (`POST /api/v1/artifacts`) → `PUT` each returned
  signed URL → commit (`POST .../versions/{id}/commit`).
- Files are addressed by SHA-256, so unchanged files are not re-uploaded.
- `share post` refuses probable secrets unless `--force-secrets` is passed.
- Share links live at `/s/{token}/` and take a TTL, a label and an optional
  password.
- Unknown and unauthorized both return the same 404. Expired, revoked, burned
  and trashed share links are the same 410.
- Artifact responses carry CSP, `nosniff`, `noindex` and a strict referrer policy.
- TLS in front is nginx or Caddy; FastAPI serves artifact bytes if nothing is
  in front.

## Deliberately not claimed

- **No hosted service, and no status snapshot.** The pages never assert which
  phase is built or whether share.c52.com is up. `index.html` links to
  `BACKLOG.md` and the commit history instead.
- **No MCP transport detail.** The pages say MCP without specifying JSON-RPC-over-POST.
  SW-4: an agent framework expecting streamable HTTP/SSE will fail to connect.
- License is Apache 2.0 (confirmed from `LICENSE`). Footers name it.
- **No metrics, users or testimonials.**

## Visuals

Rook engravings and a shared stylesheet (`site.css`) so these pages sit next to
tiding and pigeon. That look stops at this folder. It does not retoken the
dashboard, the recipient pages, or Broadsheet in `docs/specs/`.
