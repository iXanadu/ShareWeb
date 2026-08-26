# Part 9 — The Agent Surface: MCP and CLI

## 9.1 Order of precedence

The HTTP API of Part 5 is the product. Two front doors sit on it, and **neither has a
capability the other lacks**:

1. **Remote MCP** — `https://share.c52.com/mcp`, streamable HTTP, bearer token. Nothing to
   install. This is the primary path and the one the docs lead with.
2. **CLI** — `share`, a single binary. Full parity with MCP, plus the things a shell needs.

An earlier draft had a stdio MCP server as an afterthought behind a CLI-first design. That was
backwards: a stdio server needs a local process, which is the same distribution problem the CLI
has, and it cannot be reached at all by a cloud-hosted agent. A remote endpoint with a token
works identically from Claude Code on a Mac Mini, a Cursor-routed cloud agent, a Grok session,
or someone else's machine entirely.

### 9.1.1 What still needs the CLI

Worth stating plainly, because "MCP first" is sometimes read as "MCP only":

- CI runners, cron jobs, Makefiles, git hooks — no MCP host process exists.
- A human at a terminal wanting to push a directory without an agent in the loop.
- Large directories, where walking the tree locally and sending only changed files is the whole
  point — a remote MCP server cannot see the caller's filesystem.
- Sandboxes where an agent cannot reach an external endpoint but can run a local binary.

So the CLI is not a legacy path. It is the door for anything without an MCP host, and it holds
every capability.

## 9.2 Remote MCP endpoint

Transport: streamable HTTP at `/mcp`, per the current MCP specification, with SSE for
server-to-client messages. Authentication is `Authorization: Bearer shr_…` — the same token as
the HTTP API, with the same scopes.

Client configuration is one object:

```json
{
  "mcpServers": {
    "share": {
      "type": "http",
      "url": "https://share.c52.com/mcp",
      "headers": { "Authorization": "Bearer shr_…" }
    }
  }
}
```

An agent with no token calls any tool and receives a structured error carrying the device-code
instructions from §4.6.2, so it can walk its human through setup without being told how.

## 9.3 Tools

| Tool | Arguments | Returns |
| --- | --- | --- |
| `share_post` | `files: [{path, content \| contentBase64}]`, `name?`, `title?`, `description?`, `tags?`, `entryPath?`, `ttl?`, `note?` | URL, name, seq, kind, warnings |
| `share_request_upload` | `files: [{path, size, sha256, contentType}]`, plus the same metadata | Signed PUT URLs the **agent** uploads to directly. For content too large to pass inline |
| `share_update` | `name`, plus any of `title`, `description`, `tags`, `entryPath`, `ttl`, `pinned` | The artifact |
| `share_list` | `q?`, `tag?`, `kind?`, `shared?`, `trashed?`, `limit?`, `cursor?` | Artifact summaries |
| `share_get` | `name` | Artifact detail including live links |
| `share_read_file` | `name`, `path`, `version?` | File contents (text) or a note that it is binary |
| `share_versions` | `name` | Version list with change counts |
| `share_restore_version` | `name`, `versionId`, `note?` | New version |
| `share_delete` | `name` | Confirmation that it went to the trash |
| `share_restore` | `name` | Confirmation |
| `share_create_link` | `name`, `ttl`, `password?`, `label?` | URL, expiry, generated password once |
| `share_revoke_link` | `linkId` | Confirmation |
| `share_grant` | `name`, `handle`, `note?` | Confirmation |
| `share_whoami` | — | Handle, scopes, quota used and remaining, artifact count |

**`share_post` takes content, not paths.** A remote server cannot read the agent's disk. Small
text files go inline; binary goes base64 up to 8 MB per call. Above that, `share_request_upload`
returns signed URLs the agent PUTs to itself, and the tool's error message says so rather than
failing opaquely.

**The server never fetches a URL supplied by a caller.** There is no "post from this address"
tool, because that would make Share issue outbound requests on behalf of published content —
reintroducing the entire SSRF class that §2.9 says does not exist here, and which §1.6.1 partly
rests on. Bytes always travel from the agent to Share, never the other way. T-MCP-05 asserts
zero outbound sockets during a post.

**Annotations.** `share_create_link` and `share_grant` are marked as having external effects so
hosts that gate such tools prompt the human. `share_delete` is marked destructive but
reversible; `share_post` is marked idempotent-by-name.

**Tool descriptions carry the two things agents get wrong.** Every description of `share_post`
states that posting does not make anything public, and that supplying `title` and `tags` is how
the thing will be found later, because content is never indexed (§8.7).

## 9.4 CLI

```
share post <path> [flags]           Post a file or directory
share ls [flags]                    List artifacts
share get <name>                    Show one
share open <name>                   Print or open the URL
share cat <name> <path>             Print a file from an artifact
share pull <name> [dir]             Download an artifact
share rm <name> [--purge]           Trash, or permanently delete
share restore <name>                Bring back from trash
share versions <name>               List versions
share rollback <name> <seq>         Restore a version
share link <name> [flags]           Create a share link
share links <name>                  List links
share unlink <linkId>               Revoke a link
share grant <name> <handle>         Share with another user
share tag <name> <tag…>             Add or remove tags
share search <query> [flags]        Search
share trash                         List the trash
share login                         Device-code flow, writes credentials
share whoami                        Identity, scopes, quota
share logout                        Remove credentials
share doctor                        Diagnose connectivity, credentials, clock skew
share mcp                           Run a local stdio MCP proxy to the remote endpoint
```

Global flags: `--host`, `--token`, `--json`, `--quiet`, `--no-color`, `--yes`, `--timeout`.

`share mcp` exists for hosts that only speak stdio — it is a thin proxy to the remote endpoint,
not a second implementation.

### 9.4.1 `share post`

```
share post ./calendar
share post ./calendar --name postcal --title "Q4 posting calendar" --tag social
share post report.pdf
share post ./dist --ttl 30d
share post ./calendar --link --link-ttl 14d --password
```

| Flag | Effect |
| --- | --- |
| `--name` | Address to post at; creates or overwrites |
| `--title`, `--description` | Explicit metadata |
| `--tag` | Repeatable |
| `--entry` | Which file answers at the root |
| `--ttl` | Artifact self-trashes after this |
| `--note` | Version note |
| `--link` | Create a share link after posting; requires `share:create` |
| `--link-ttl`, `--password`, `--label` | Link options |
| `--include` / `--exclude` | Repeatable globs |
| `--dry-run` | Print the manifest and what would upload; change nothing |
| `--bundle` / `--no-bundle` | Force or forbid the one-shot path |
| `--concurrency` | Upload workers; default 8, or 4 when any file exceeds 100 MB |
| `--json` | Emit the commit response and nothing else |

### 9.4.2 Local walk rules

Always excluded, regardless of flags:

```
.git/ .hg/ .svn/ node_modules/ __pycache__/ .venv/ venv/ .mypy_cache/ .pytest_cache/
.terraform/ .next/cache/ .parcel-cache/ .idea/ .vscode/ .DS_Store Thumbs.db *.pyc
```

Refused **loudly**, requiring `--force-secrets` to proceed:

```
.env  .env.*  *.pem  *.key  id_rsa*  *.p12  *.keystore  credentials  .netrc
```

The server rejects dotfiles anyway (§6.4), but the point is to fail in the operator's own
terminal, naming the file, before anything leaves the machine.

Symlinks are skipped with a warning, never followed. Unreadable files are a hard error naming
the file.

### 9.4.3 Output

Terse, ending with the URL on its own line so `$(share post ./x | tail -1)` works:

```
Posting ./calendar  (3 files, 110 KB)
  1 new, 2 unchanged
  ████████████████████ 1/1 uploaded
Posted postcal v2 — private

https://share.c52.com/postcal
```

`--json` emits exactly the commit response body. Warnings go to stderr with a `warning:` prefix.
Errors print `error: <code>: <message>` and exit per §9.7.

## 9.5 Credentials and configuration

```
~/.share/credentials      mode 0600, one line: the token
~/.share/config.json      { "host": "https://share.c52.com", "concurrency": 8 }
./.share.json             per-project overrides (excluded from any walk)
```

Resolution for every setting: flag → environment (`SHARE_TOKEN`, `SHARE_HOST`) → project config
→ user config → default.

`share login` runs the device-code flow of §4.6.2: it prints a short user code and a URL, the
human approves in an authenticated session, and the CLI writes the token with mode `0600` and
prints the granted scopes — including, plainly, that the token cannot create share links.

## 9.6 What the agent surface says about privacy

Three places repeat the same fact, because the failure mode is an agent assuming that posting
means publishing:

1. `share post` output: `Posted postcal v2 — private`.
2. The `share_post` tool description, first sentence.
3. `share whoami`: `scopes: artifacts:read artifacts:write  (cannot create share links)`.

And the inverse: `share link` always prints the expiry in absolute terms —
`Public until 2026-09-07 18:04 UTC (14 days)` — so an agent transcript shows exactly what
became reachable and for how long.

## 9.7 Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Generic failure |
| 2 | Usage error |
| 3 | No credentials |
| 4 | Authentication failed |
| 5 | Insufficient scope |
| 6 | Not found |
| 7 | Conflict |
| 8 | Quota or size limit |
| 9 | Rate limited |
| 10 | Host unreachable |
| 11 | Refused locally (secret file, symlink, unreadable file) |
| 12 | Server error |

With `--json`, every failure emits the §5.1.1 error envelope on stdout so a wrapper can branch
on `error.code` without scraping text.

## 9.8 Discovery and installation

```
https://share.c52.com/.well-known/mcp                 → endpoint descriptor
https://share.c52.com/install.sh                      → CLI installer
https://share.c52.com/~/help/agents                   → copy-paste setup for each host
```

The help page carries ready-made configuration blocks for Claude Code, Cursor, Codex, Cline,
and a generic MCP host, each with the user's own hostname already filled in and a placeholder
where the token goes. `install.sh` installs the CLI, writes `~/.share/config.json` pointing at
the instance it came from, and offers to run `share login`. It never writes a credential it was
not given interactively.

## 9.9 CI use

- `SHARE_TOKEN` from the runner's secret store; never a credentials file in CI.
- `--yes` suppresses prompts; without it, a confirmation in a non-TTY is an error rather than a
  silent assumption.
- The documented pattern is `share post ./out --name preview-$BRANCH --ttl 30d`, giving each
  branch a stable private URL that cleans itself up. **`--link` from CI is discouraged in the
  docs** — a pipeline that can publish to the internet is a pipeline whose compromise publishes
  to the internet.
