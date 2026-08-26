# Shared Inventory — canonical numbering for Parts 11, 12, 13

Do not renumber. Parts 11 (screens), 12 (copy), and 13 (design system) cross-reference each
other by these numbers.

## Dashboard screens (all under `/~/`)

| # | Screen | Route | Phase |
| --- | --- | --- | --- |
| 11.1 | Sign in — passkey | `/~/signin` | 1 |
| 11.2 | Sign in — recovery code | `/~/signin/recovery` | 2 |
| 11.3 | Passkey registration / add a passkey | `/~/security/passkeys/new` | 1 |
| 11.4 | Invite acceptance | `/~/invite/{token}` | 3 |
| 11.5 | Home — artifact list | `/~/artifacts` | 1 |
| 11.6 | Home — empty state and first-run checklist | `/~/artifacts` | 1 |
| 11.7 | Artifact detail — overview and activity | `/~/artifacts/{name}` | 1 |
| 11.8 | Artifact detail — files | `/~/artifacts/{name}/files` | 1 |
| 11.9 | Artifact viewer — page, document, image, video, bundle | `/~/artifacts/{name}/view` | 2 |
| 11.10 | Artifact detail — versions | `/~/artifacts/{name}/versions` | 2 |
| 11.11 | Version preview and compare | `/~/artifacts/{name}/versions/{id}` | 2 |
| 11.12 | Sharing panel — links and grants | `/~/artifacts/{name}/share` | 2 |
| 11.13 | **Create share link dialog** | `/~/artifacts/{name}/share/new` | 2 |
| 11.14 | Shared with me | `/~/shared` | 3 |
| 11.15 | Trash | `/~/trash` | 1 |
| 11.16 | Search and command palette | `/~/search`, ⌘K anywhere | 2 |
| 11.17 | Upload from the browser | `/~/upload` | 2 |
| 11.18 | API tokens | `/~/tokens` | 1 |
| 11.19 | Passkeys and sessions | `/~/security` | 1 |
| 11.20 | Security overview | `/~/security/overview` | 3 |
| 11.21 | Settings | `/~/settings` | 2 |
| 11.22 | Users and invites (root only) | `/~/users` | 3 |
| 11.23 | Audit log | `/~/audit` | 3 |
| 11.24 | Staleness — things you have not opened | `/~/stale` | 3 |
| 11.25 | Storage and quota | `/~/storage` | 3 |
| 11.26 | Device authorization | `/~/authorize` | 1 |
| 11.27 | Help and agent setup | `/~/help`, `/~/help/agents` | 1 |
| 11.28 | Instance status | `/~/status` | 3 |

## Recipient-facing and error pages (served by the API, no dashboard chrome)

| # | Page | Status | Notes |
| --- | --- | --- | --- |
| R1 | Share-link password gate | 401 | Must work with JavaScript disabled |
| R2 | Share-link landing for non-HTML artifacts | 200 | Minimal chrome: title if set, view, download |
| R3 | Link expired or revoked | 410 | Only on `/s/{token}`; reveals nothing about the artifact |
| R4 | Not found | 404 | The universal response for anything inaccessible |
| R5 | Rate limited | 429 | |
| R6 | Maintenance | 503 | Static, served by Caddy when the API is down |
| R7 | Artifact file listing | 200 | A bundle with no entry point (§6.6.2) |

## Part 12 copy sections

| § | Contents |
| --- | --- |
| 12.1 | Voice and tone |
| 12.2 | Canonical terminology and tooltip definitions |
| 12.3 | First-run checklist copy |
| 12.4 | In-app documentation pages |
| 12.5 | UI microcopy, per screen 11.1–11.28 |
| 12.6 | Warning and advisory catalogue |
| 12.7 | Recipient-facing page copy (R1–R7) |
| 12.8 | Error message catalogue — every code in Parts 4–10 |
| 12.9 | Email templates |
| 12.10 | FAQ |
