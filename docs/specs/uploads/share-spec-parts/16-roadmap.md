# Part 16 — Phasing and Definition of Done

## 16.1 How to sequence this

Four phases. The instance is genuinely usable at the end of Phase 1 — an agent can post, the
owner can open it — and each later phase adds capability without reworking what came before.

An implementing agent completes a phase, runs its exit tests, and only then starts the next.
Phases 2 and 3 can be built in parallel by separate agents. Phase 4 depends on both.

This part is authoritative for phase membership; where `inventory.md`'s phase column disagrees,
this wins.

## 16.2 Phase 1 — Post and open

**Goal:** an agent posts a directory and the owner opens the URL from a phone.

| Deliverable | Spec |
| --- | --- |
| Schema, migrations, `sharectl bootstrap` | Part 3, §15.3 |
| Passkey registration and sign-in, sessions, recovery code | §4.2–4.5 |
| API tokens, scopes, the `require(scope)` dependency, device-code flow | §4.6 |
| Three-phase post, bundle post, name validation, path normalisation, file store | Part 5, §6.4 |
| `/internal/authorize`, `can_view`, resolution, serving, the Caddyfile | Part 2, §6.5–6.6 |
| Trash and restore | §8.4 |
| Audit log for auth, post, and trash | §10.7 |
| Remote MCP endpoint with the post/list/get/read/delete tools | §9.2–9.3 |
| CLI: `post`, `ls`, `get`, `open`, `rm`, `restore`, `login`, `whoami`, `doctor` | §9.4 |
| Screens 11.1, 11.3, 11.5, 11.6, 11.7, 11.8, 11.15, 11.18, 11.19, 11.26, 11.27 | Part 11 |
| Install playbook, backup job, `sharectl` basics | Part 15 |

**Exit criteria**

- `share post ./x` returns a working URL in under 5 seconds for a 40-file artifact.
- A passkey registered in 1Password signs in on a second device with no password anywhere.
- T-PRIV-01, T-PRIV-02, T-PRIV-05, T-PRIV-07, T-PRIV-08 pass.
- The whole T-POST and T-AUTH suites pass.
- T-SEC-07 passes — no credential class crosses into another.
- A restore drill succeeds and `verify-integrity` reports zero missing files.

**Deliberately deferred:** all sharing, versions UI, viewer chrome, search, grants, users.
Phase 1 has exactly one visibility state — private — which makes the access model trivially
testable before any sharing exists to complicate it.

## 16.3 Phase 2 — Sharing and viewing

**Goal:** the owner hands a client a link that works and dies on schedule.

| Deliverable | Spec |
| --- | --- |
| Share links: create, password, expiry, revoke, extend | §7.3–7.5 |
| Recipient sessions and the `/s/{token}` surface | §4.7, §2.5.2 |
| Recipient-facing pages R1–R7 | §11 R-series, §12.7 |
| Expiry sweep, inline expiry check, expiry notifications | §7.5, §10.8 |
| Versions: list, restore, retention, preview | §8.2–8.3 |
| Artifact TTL | §8.5 |
| The viewer: page, document, image, video, bundle, with Range serving | §11.9, §6.6.4 |
| Search and the command palette | §8.7 |
| Browser upload | §11.17 |
| Screens 11.2, 11.9–11.13, 11.16, 11.17, 11.21 | Part 11 |
| Design system and all product copy | Parts 12, 13 |

**Exit criteria**

- A password-protected link works end to end from a phone on cellular data, with JavaScript
  disabled.
- T-PRIV-03, T-PRIV-04, T-PRIV-06, T-PRIV-09 pass.
- The full T-SHARE matrix passes — five principals × nine artifact states.
- T-EXP-02 passes: a link is dead the second after expiry, before the sweep runs.
- A 2 GB video seeks correctly through a share link.
- Every screen renders in both themes at 375 px and 1440 px.

## 16.4 Phase 3 — More than one person

**Goal:** a second user exists and sees only what was shared with them.

| Deliverable | Spec |
| --- | --- |
| Invites, user creation, handles, `~handle` namespaces | §4.8, §6.2 |
| Grants and "shared with me" | §7.7 |
| Save a copy | §5.10, §7.7.1 |
| Staleness view and storage screen | §8.6, §11.24, §11.25 |
| Audit log screen and export | §10.7, §11.23 |
| Security overview | §11.20 |
| Screens 11.4, 11.14, 11.20, 11.22–11.25, 11.28 | Part 11 |

**Exit criteria**

- A second user signs in and can prove, by test, that they cannot see, list, search, guess, or
  reach anything of the root user's except what was granted.
- T-PRIV-07 passes against a real second user rather than a fixture.
- Revoking a grant takes effect on the grantee's next request.
- A grantee's saved copy survives the original being purged.

## 16.5 Phase 4 — Operational hardening

**Goal:** it can be trusted with client material and left alone.

| Deliverable | Spec |
| --- | --- |
| Anomaly detection and the full notification set | §10.4, §10.8 |
| Rate limiting on every bucket | §10.2 |
| `sharectl panic`, integrity sampling, audit sealing | §10.5, §15.7 |
| View counting and the activity feed | §10.6, §8.8 |
| Monitoring, alerting, restore drill automation | §15.5 |
| Instance status screen | §11.28 |

**Exit criteria**

- Every bucket in §10.2 has a passing test, verified by the bucket-registry coverage gate.
- An anomaly fires an email within 15 minutes of tripping.
- `sharectl panic` kills every link and session and is verified against a live recipient.
- The full acceptance suite in Part 14 passes with no skips.
- The manual checklist in §14 is signed off.

## 16.6 Definition of done, per feature

Applied before any task is marked complete:

1. **Behaviour matches the spec section**, including every error and warning code in its table.
2. **Tests exist and pass** at the levels the feature warrants — unit for pure logic,
   integration against real Postgres and Redis, end-to-end through Caddy for anything touching
   serving.
3. **The three negative cases are tested** for every endpoint: permission denial, limit breach,
   malformed input. Enforced reflectively over the route table (T-SEC-00).
4. **Audit events fire** for every action in §10.7 the feature covers.
5. **No secret appears** in any log line, error body, or API response.
6. **The OpenAPI document is regenerated** and its examples execute against a test instance.
7. **The docs in Part 12 are updated**, including any new error or warning code.
8. **Both the MCP tools and the CLI cover it**, or a note records why not — §9.1 requires
   parity, and parity that drifts silently is worse than parity never claimed.
9. **A rollback path exists**: the migration is reversible, or its irreversibility is documented
   in the migration file.

## 16.7 Where the weight is

Relative sizing, not a schedule.

| Phase | Effort | Riskiest part |
| --- | --- | --- |
| 1 | 35% | The `forward_auth` contract, and getting WebAuthn right the first time |
| 2 | 35% | Recipient session semantics and revocation; the viewer across five artifact kinds |
| 3 | 15% | Nothing especially risky — mostly mechanical once spaces are enforced |
| 4 | 15% | Anomaly thresholds that are useful rather than noisy |

Two places deserve disproportionate care: **§6.5, the `authorize` function and `can_view`** —
four lines that are the entire access model, and the only place a mistake becomes a data leak —
and **§4.7, credential-class confinement**, because a recipient session that leaks into the API
would turn a shared link into an account.

Everything else is recoverable from. Those two are not.

## 16.8 What is deliberately not on the roadmap

- Multi-region or high availability (§1.4 N5).
- Any server-side execution of published content, build steps, or application runtime (N1).
- Embedded data storage for published pages, or API proxying with injected credentials (N2).
  These were in an earlier draft, were the largest security surface in the system, and are cut.
- Teams, roles, or permission matrices (N3). Sharing is per-artifact; there is nothing else.
- Public sign-up (N4).
- Full-text search inside artifacts (N6, P5).
- Custom domains, subdomains, or any hostname beyond `share.c52.com`.
- Content-derived anything: no generated titles, summaries, thumbnails, or classifications.
- Permanent share links. Not a phase, not a flag, not a future consideration.
- Anonymous posting. This is the thing the instance exists to not have.
