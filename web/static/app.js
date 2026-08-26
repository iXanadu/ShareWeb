/** Share dashboard SPA — Phase 1 screens (Part 11/12). */

const COPY = {
  signin: {
    intro: "Sign in with a passkey.",
    button: "Sign in",
    buttonBusy: "Waiting for your passkey…",
    recovery: "Use a recovery code",
    errors: {
      invalid_credential:
        "That passkey is not registered here. Try another, or use a recovery code.",
      webauthn_verification_failed:
        "That sign-in could not be verified. Try again, or use a recovery code.",
      passkey_unavailable:
        "Passkey sign-in is not wired on this instance yet.",
      no_credential:
        "This device has no passkey for share.c52.com. Sign in on a device that does and add one there, or use a recovery code.",
    },
  },
  nav: {
    library: "Library",
    agents: "Agents",
    artifacts: "Artifacts",
    shared: "Shared with me",
    trash: "Trash",
    tokens: "API tokens",
    audit: "Audit log",
    security: "Security",
    help: "Help",
  },
  artifacts: {
    title: "Artifacts",
    search: "Search artifacts",
    columns: ["Name", "Sharing", "Updated", "Size", "Version"],
    emptyFilters: "No artifacts match these filters.",
    clearFilters: "Clear filters",
  },
  empty: {
    heading: "Set up Share",
    intro:
      "Five things, once. The first two get an agent posting to this instance; the rest make sure you can still get in and still know what is reachable.",
    footer:
      "You can leave this at any time — it disappears once every item is done or skipped.",
    nothingHeading: "Nothing here yet",
    nothingBody: "Artifacts your agents post appear here, newest first.",
    items: [
      {
        title: "Connect an agent",
        body: "Point Claude Code, Cursor, Codex, or any MCP host at this instance with one configuration block and a token.",
        cta: "Create a token",
        href: "/~/tokens",
      },
      {
        title: "Post your first artifact",
        body: "Have your agent call `share_post`, or run `share post ./folder`. It stays private until you say otherwise.",
        cta: "See the setup page",
        href: "/~/help/agents",
      },
      {
        title: "Add a second passkey",
        body: "One passkey is one device away from a recovery process. A second one on another device is what makes losing the first uneventful.",
        cta: "Add a passkey",
        href: "/~/security/passkeys/new",
      },
    ],
  },
  trash: {
    title: "Trash",
    subheader: "Items here still count against your storage quota.",
    emptyHeading: "Nothing in the trash",
    emptyBody: "Deleted artifacts stay here for 30 days before they are removed for good.",
    columns: ["Name", "Deleted", "Size"],
    restore: "Restore",
  },
  tokens: {
    title: "API tokens",
    new: "New token",
    emptyHeading: "No tokens yet",
    emptyBody:
      "An agent needs a token to post here. Create one below, or run `share login` and approve it from this browser.",
    deviceFlow: "Or approve a code from your terminal",
    deviceFlowLink: "Enter device code",
    columns: ["Name", "Prefix", "Scopes", "Last used"],
    nameLabel: "Name",
    namePlaceholder: "agent@machine",
    create: "Create token",
    createdHeading: "Copy this token now",
    createdBody: "It is shown once. Store it somewhere safe — Share cannot show it again.",
    copyToken: "Copy token",
    copyMcp: "Copy MCP config",
    done: "Done",
    revoke: "Revoke",
    revokeConfirm:
      "Revoke this token? The agent using it stops working immediately. Its artifacts and versions remain and stay attributed to it.",
    neverUsed: "never",
  },
  security: {
    title: "Security",
    passkeys: "Passkeys",
    addPasskey: "Add a passkey",
    onePasskey:
      "You have one passkey. If you lose it, the only ways back in are your recovery code or access to the server.",
    noPasskeys: "No passkeys registered yet.",
    backupSynced: "syncs across your devices",
    backupLocal: "this device only",
    passkeyColumns: ["Name", "Created", "Last used", "Backup"],
    existingPasskeys: "Your passkeys",
    sessions: "Sessions",
    recovery: "Recovery code",
    recoveryNone:
      "No recovery code. Generate one now — it is the only way back if every passkey is gone and you cannot reach the server.",
    generate: "Generate a new code",
  },
  authorize: {
    title: "Authorize an agent",
    intro: "Enter the code your agent printed.",
    label: "Code",
    placeholder: "XXXX-XXXX",
    lookup: "Continue",
    unknown:
      "That code is not valid. It may have expired — codes last 10 minutes. Run the command again for a new one.",
    approvalHeading: (name) => `Give ${name} a token?`,
    rowRequestedFrom: "Requested from",
    rowStarted: "Started",
    rowScopes: "Scopes",
    scopeRead: "Read and download your artifacts",
    scopeWrite: "Post, overwrite, rename, tag, and move to the trash",
    noShareLinks: "This token will not be able to create share links.",
    approve: "Approve",
    deny: "Deny",
    approvedHeading: "Approved",
    approvedBody: (name) =>
      `${name} has a token. Return to your terminal — the token is not shown here.`,
    manageToken: "Manage this token",
    deniedHeading: "Denied",
    deniedBody: "No token was issued. The agent will report that the request was refused.",
  },
  help: {
    title: "Help",
    agentsTitle: "Connecting agents",
    noToken: "You have no tokens yet. An agent needs one to post here.",
    createToken: "Create a token",
    tokenNote:
      "Replace `shr_YOUR_TOKEN` with a real token. Share never fills a real token into these blocks.",
    topics: "Three things people ask",
    quickstart:
      "Share is where your agents put finished work so you can find it later and hand it to people.",
    topicSearch:
      "Search covers names, titles, descriptions, and tags — never the contents of your files.",
    topicExpiry: "Every share link expires. There is no setting for a permanent link.",
    topicOverwrite:
      "When an agent posts again to the same name, the URL stays the same and anyone with a live share link sees the new version.",
  },
  detail: {
    back: "Artifacts",
    tabs: ["Overview", "Files", "Versions", "Sharing"],
    copyUrl: "Copy URL",
    open: "Open",
    sharingHeading: "Sharing",
    private: "Private",
    privateDetail: "Only you",
    postedBy: "Posted by",
    details: "Details",
    moveTrash: "Move to trash",
    copyToast:
      "URL copied. This is the signed-in address — it will not work for anyone else.",
    trashConfirm:
      "Move this artifact to the trash? It stops resolving at its URL immediately. Share links and grants are revoked now and are not restored when you restore it.",
    trashButton: "Move to trash",
  },
  files: {
    columns: ["Path", "Size", "Type"],
    entry: "entry",
    download: "Download",
    empty: "This version has no files.",
    countOne: "1 file",
    countMany: (n) => `${n} files`,
  },
};

const PUBLIC_ROUTES = new Set(["/~/signin", "/~/signin/recovery"]);

function hostLine() {
  return window.location.host || "share.c52.com";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatBytes(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let v = Number(n);
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  const digits = i === 0 ? 0 : v >= 10 ? 0 : 1;
  return `${v.toFixed(digits)} ${units[i]}`;
}

function formatWhen(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
      timeZoneName: "short",
    });
  } catch {
    return iso;
  }
}

function b64ToBuffer(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const bin = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i);
  return out.buffer;
}

function bufferToB64(buf) {
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  const csrf = document.cookie.match(/(?:^|;\s*)share_csrf=([^;]+)/)?.[1];
  if (csrf && options.method && options.method !== "GET") {
    headers["X-Share-CSRF"] = decodeURIComponent(csrf);
  }
  const resp = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers,
  });
  if (resp.status === 401) return null;
  if (!resp.ok) {
    let body = {};
    try {
      body = await resp.json();
    } catch {
      /* ignore */
    }
    const err = new Error(body.error?.message || body.message || body.detail || resp.statusText);
    err.status = resp.status;
    err.code = body.error?.code || body.code;
    throw err;
  }
  if (resp.status === 204) return null;
  return resp.json();
}

async function sessionUser() {
  return api("/api/v1/me");
}

function parsePublicKeyOptions(publicKey) {
  const pk = { ...publicKey };
  pk.challenge = b64ToBuffer(pk.challenge);
  if (pk.user?.id) {
    pk.user = { ...pk.user, id: b64ToBuffer(pk.user.id) };
  }
  for (const field of ["allowCredentials", "excludeCredentials"]) {
    if (pk[field]?.length) {
      pk[field] = pk[field].map((c) => ({ ...c, id: b64ToBuffer(c.id) }));
    }
  }
  return pk;
}

function credentialToJSON(cred) {
  const response = cred.response;
  const out = {
    id: cred.id,
    rawId: bufferToB64(cred.rawId),
    type: cred.type,
    response: {
      authenticatorData: bufferToB64(response.authenticatorData),
      clientDataJSON: bufferToB64(response.clientDataJSON),
    },
  };
  if (response.signature) out.response.signature = bufferToB64(response.signature);
  if (response.attestationObject) {
    out.response.attestationObject = bufferToB64(response.attestationObject);
  }
  if (response.userHandle?.byteLength) {
    out.response.userHandle = bufferToB64(response.userHandle);
  }
  return out;
}

function mapAuthError(code, fallback) {
  if (code === "invalid_credential") return COPY.signin.errors.invalid_credential;
  if (code === "webauthn_verification_failed") return COPY.signin.errors.webauthn_verification_failed;
  if (code === "credential_counter_regressed") {
    return "This passkey reported an unexpected use count, which can mean it has been copied. Sign-in was refused and the account owner has been emailed. Sign in with a different passkey and revoke this one from your security settings.";
  }
  return fallback;
}

function navLinks(active) {
  const library = [
    { href: "/~/artifacts", label: COPY.nav.artifacts, key: "artifacts" },
    { href: "/~/shared", label: COPY.nav.shared, key: "shared" },
    { href: "/~/trash", label: COPY.nav.trash, key: "trash" },
  ];
  const agents = [
    { href: "/~/tokens", label: COPY.nav.tokens, key: "tokens" },
    { href: "/~/security", label: COPY.nav.security, key: "security" },
    { href: "/~/help", label: COPY.nav.help, key: "help" },
  ];
  const render = (items) =>
    items
      .map(
        (item) =>
          `<a href="${item.href}" class="${active === item.key ? "active" : ""}">${escapeHtml(item.label)}</a>`,
      )
      .join("");
  return { library: render(library), agents: render(agents) };
}

function renderShell(active, title, bodyHtml, user = "you") {
  const nav = navLinks(active);
  return `
    <div class="share-shell">
      <nav class="share-nav" aria-label="Main">
        <div>
          <div class="share-nav-brand">
            <span class="share-nav-brand-title">Share</span>
            <span class="share-host">${escapeHtml(hostLine())}</span>
          </div>
          <div class="share-nav-section">
            <div>
              <span class="share-nav-label">${escapeHtml(COPY.nav.library)}</span>
              ${nav.library}
            </div>
            <div class="share-nav-agents">
              <span class="share-nav-label">${escapeHtml(COPY.nav.agents)}</span>
              ${nav.agents}
            </div>
          </div>
        </div>
        <div class="share-quota">—</div>
      </nav>
      <div class="share-main">
        <header class="share-topbar">
          <input class="share-input share-topbar-search" type="search" placeholder="${escapeHtml(COPY.artifacts.search)}" disabled>
          <span class="share-topbar-user">@${escapeHtml(user?.handle || "you")}</span>
        </header>
        <main class="share-content">
          ${title ? `<h1 class="share-page-title">${escapeHtml(title)}</h1>` : ""}
          ${bodyHtml}
        </main>
      </div>
    </div>`;
}

function renderSignIn(error = "") {
  return `
    <div class="share-signin">
      <div class="share-signin-inner">
        <div class="share-wordmark">
          <span class="share-wordmark-title">Share</span>
          <span class="share-host">${escapeHtml(hostLine())}</span>
        </div>
        <p class="share-intro">${escapeHtml(COPY.signin.intro)}</p>
        ${error ? `<div class="share-error" role="alert">${escapeHtml(error)}</div>` : ""}
        <div style="display:flex;flex-direction:column;gap:20px;align-items:flex-start">
          <button type="button" class="share-btn" id="signin-btn">${escapeHtml(COPY.signin.button)}</button>
          <a href="/~/signin/recovery">${escapeHtml(COPY.signin.recovery)}</a>
        </div>
      </div>
    </div>`;
}

function renderEmptyChecklist() {
  const items = COPY.empty.items
    .map(
      (item, i) => `
    <div class="share-checklist-item">
      <span class="share-checklist-num">${i + 1}</span>
      <div class="share-checklist-body">
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.body)}</p>
        <a href="${item.href}">${escapeHtml(item.cta)}</a>
      </div>
    </div>`,
    )
    .join("");
  return `
    <div class="share-checklist">
      <h2>${escapeHtml(COPY.empty.heading)}</h2>
      <p class="share-checklist-intro">${escapeHtml(COPY.empty.intro)}</p>
      ${items}
      <p class="share-checklist-intro" style="margin-top:20px">${escapeHtml(COPY.empty.footer)}</p>
    </div>
    <h2 style="font-size:22px;margin:0 0 8px">${escapeHtml(COPY.empty.nothingHeading)}</h2>
    <p class="share-empty">${escapeHtml(COPY.empty.nothingBody)}</p>`;
}

function renderArtifactRows(items) {
  if (!items.length) return renderEmptyChecklist();
  const rows = items
    .map(
      (item) => `
      <tr>
        <td>
          <a class="mono" href="/~/artifacts/${encodeURIComponent(item.name)}">${escapeHtml(item.name)}</a>
          ${item.title ? `<div style="font-size:15px;color:var(--share-muted)">${escapeHtml(item.title)}</div>` : ""}
        </td>
        <td><span class="share-badge-private">${escapeHtml(COPY.detail.private)}</span></td>
        <td>${escapeHtml(formatWhen(item.updatedAt))}</td>
        <td>${escapeHtml(formatBytes(item.totalBytes))}</td>
        <td>v${escapeHtml(item.seq ?? 1)}</td>
      </tr>`,
    )
    .join("");
  return `
    <table class="share-table">
      <thead><tr>${COPY.artifacts.columns.map((c) => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function artifactTabs(name, active) {
  const base = `/~/artifacts/${encodeURIComponent(name)}`;
  const tabs = [
    { key: "overview", label: COPY.detail.tabs[0], href: base },
    { key: "files", label: COPY.detail.tabs[1], href: `${base}/files` },
  ];
  return `<nav class="share-tabs">${tabs.map((t) => `<a href="${t.href}" class="${active === t.key ? "active" : ""}">${escapeHtml(t.label)}</a>`).join("")}</nav>`;
}

function mcpBlock(token = "shr_YOUR_TOKEN") {
  const host = hostLine();
  return JSON.stringify(
    {
      mcpServers: {
        share: {
          type: "http",
          url: `https://${host}/mcp`,
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    },
    null,
    2,
  );
}

function scopeChips(scopes) {
  if (!scopes?.length) return "—";
  return scopes
    .map((s) => {
      const warn = s === "share:create" ? " share-scope-warn" : "";
      return `<span class="share-scope${warn}">${escapeHtml(s)}</span>`;
    })
    .join(" ");
}

function backupLabel(state) {
  if (state === "backed_up") return COPY.security.backupSynced;
  if (state === "not_backed_up") return COPY.security.backupLocal;
  return state ? escapeHtml(state) : "—";
}

function renderFileRows(items, entryPath, artifactName) {
  if (!items.length) {
    return `<p class="share-empty">${escapeHtml(COPY.files.empty)}</p>`;
  }
  const rows = items
    .map((f) => {
      const isEntry = f.path === entryPath;
      const dl = `/api/v1/artifacts/${encodeURIComponent(artifactName)}/files/content?path=${encodeURIComponent(f.path)}`;
      return `
      <tr>
        <td class="mono">
          ${escapeHtml(f.path)}
          ${isEntry ? ` <span class="share-badge-entry">${escapeHtml(COPY.files.entry)}</span>` : ""}
        </td>
        <td>${escapeHtml(formatBytes(f.size))}</td>
        <td>${escapeHtml(f.contentType || "—")}</td>
        <td><a href="${dl}" download>${escapeHtml(COPY.files.download)}</a></td>
      </tr>`;
    })
    .join("");
  const header =
    items.length === 1
      ? COPY.files.countOne
      : COPY.files.countMany(items.length);
  return `
    <p class="share-meta">${escapeHtml(header)}</p>
    <table class="share-table">
      <thead><tr>${[...COPY.files.columns, ""].map((c) => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

async function passkeySignIn() {
  if (!window.PublicKeyCredential) {
    throw new Error(COPY.signin.errors.no_credential);
  }
  const begin = await fetch("/auth/passkey/login/begin", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!begin.ok) {
    const body = await begin.json().catch(() => ({}));
    throw new Error(mapAuthError(body.error?.code, COPY.signin.errors.webauthn_verification_failed));
  }
  const { publicKey } = await begin.json();
  const cred = await navigator.credentials.get({
    publicKey: parsePublicKeyOptions(publicKey),
  });
  if (!cred) return;
  const finish = await fetch("/auth/passkey/login/finish", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential: credentialToJSON(cred) }),
  });
  if (!finish.ok) {
    const body = await finish.json().catch(() => ({}));
    throw new Error(
      mapAuthError(body.error?.code, COPY.signin.errors.webauthn_verification_failed),
    );
  }
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next");
  if (next && next.startsWith("/~/")) window.location.replace(next);
  else window.location.replace("/~/artifacts");
}

async function passkeyRegister(name) {
  if (!window.PublicKeyCredential) {
    throw new Error(COPY.signin.errors.no_credential);
  }
  const begin = await fetch("/auth/passkey/register/begin", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!begin.ok) {
    const body = await begin.json().catch(() => ({}));
    throw new Error(mapAuthError(body.error?.code, "Registration could not start."));
  }
  const { publicKey } = await begin.json();
  let cred;
  try {
    cred = await navigator.credentials.create({
      publicKey: parsePublicKeyOptions(publicKey),
    });
  } catch (e) {
    if (e.name === "InvalidStateError") {
      throw new Error("This authenticator is already registered. Use a different one.");
    }
    if (e.name === "NotAllowedError" || e.name === "AbortError") return null;
    throw e;
  }
  if (!cred) return null;
  const finish = await fetch("/auth/passkey/register/finish", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential: credentialToJSON(cred), name: name || "Passkey" }),
  });
  if (!finish.ok) {
    const body = await finish.json().catch(() => ({}));
    throw new Error(mapAuthError(body.error?.code, "Registration could not be verified."));
  }
  return finish.json();
}

async function viewSignIn(root, error = "") {
  root.innerHTML = renderSignIn(error);
  root.querySelector("#signin-btn")?.addEventListener("click", async () => {
    const btn = root.querySelector("#signin-btn");
    btn.disabled = true;
    btn.textContent = COPY.signin.buttonBusy;
    try {
      await passkeySignIn();
    } catch (e) {
      if (e.name === "NotAllowedError" || e.name === "AbortError") {
        await viewSignIn(root);
        return;
      }
      await viewSignIn(root, e.message || COPY.signin.errors.webauthn_verification_failed);
    } finally {
      btn.disabled = false;
      btn.textContent = COPY.signin.button;
    }
  });
}

async function viewArtifacts(root, user) {
  let items = [];
  try {
    const data = await api("/api/v1/artifacts");
    items = data?.items || [];
  } catch {
    items = [];
  }
  root.innerHTML = renderShell("artifacts", COPY.artifacts.title, renderArtifactRows(items), user);
}

async function viewTrash(root, user) {
  let items = [];
  try {
    const data = await api("/api/v1/artifacts?trashed=true");
    items = data?.items || [];
  } catch {
    items = [];
  }
  let body;
  if (!items.length) {
    body = `
      <p class="share-empty">${escapeHtml(COPY.trash.subheader)}</p>
      <h2 style="font-size:22px">${escapeHtml(COPY.trash.emptyHeading)}</h2>
      <p class="share-empty">${escapeHtml(COPY.trash.emptyBody)}</p>`;
  } else {
    const rows = items
      .map(
        (item) => `
        <tr>
          <td class="mono">${escapeHtml(item.name)}</td>
          <td>${escapeHtml(formatWhen(item.updatedAt))}</td>
          <td>${escapeHtml(formatBytes(item.totalBytes))}</td>
          <td><button type="button" class="share-btn share-btn-secondary" data-restore="${escapeHtml(item.name)}">${escapeHtml(COPY.trash.restore)}</button></td>
        </tr>`,
      )
      .join("");
    body = `
      <p class="share-empty">${escapeHtml(COPY.trash.subheader)}</p>
      <table class="share-table">
        <thead><tr>${[...COPY.trash.columns, ""].map((c) => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }
  root.innerHTML = renderShell("trash", COPY.trash.title, body, user);
  root.querySelectorAll("[data-restore]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const name = btn.getAttribute("data-restore");
      try {
        await api(`/api/v1/artifacts/${encodeURIComponent(name)}/restore`, { method: "POST" });
        await viewTrash(root, user);
      } catch (e) {
        alert(e.message);
      }
    });
  });
}

async function viewTokens(root, user) {
  let items = [];
  try {
    const data = await api("/api/v1/tokens");
    items = data?.items || [];
  } catch {
    items = [];
  }

  function renderList() {
    if (!items.length) {
      return `
        <h2 style="font-size:22px">${escapeHtml(COPY.tokens.emptyHeading)}</h2>
        <p class="share-empty">${escapeHtml(COPY.tokens.emptyBody)}</p>
        <p class="share-empty">${escapeHtml(COPY.tokens.deviceFlow)} — <a href="/~/authorize">${escapeHtml(COPY.tokens.deviceFlowLink)}</a></p>`;
    }
    const rows = items
      .map(
        (t) => `
        <tr>
          <td>${escapeHtml(t.name)}</td>
          <td class="mono">${escapeHtml(t.displayPrefix)}…</td>
          <td>${scopeChips(t.scopes)}</td>
          <td>${escapeHtml(t.lastUsedAt ? formatWhen(t.lastUsedAt) : COPY.tokens.neverUsed)}</td>
          <td><button type="button" class="share-btn share-btn-danger share-btn-sm" data-revoke="${escapeHtml(t.id)}">${escapeHtml(COPY.tokens.revoke)}</button></td>
        </tr>`,
      )
      .join("");
    return `
      <table class="share-table">
        <thead><tr>${[...COPY.tokens.columns, ""].map((c) => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  const body = `
    <div class="share-actions">
      <button type="button" class="share-btn" id="new-token-btn">${escapeHtml(COPY.tokens.new)}</button>
    </div>
    <div id="token-create" hidden>
      <div class="share-card">
        <div class="share-form-row">
          <label for="token-name">${escapeHtml(COPY.tokens.nameLabel)}</label>
          <input class="share-input" id="token-name" type="text" placeholder="${escapeHtml(COPY.tokens.namePlaceholder)}">
        </div>
        <div class="share-error" id="token-error" role="alert" hidden></div>
        <button type="button" class="share-btn" id="create-token-btn">${escapeHtml(COPY.tokens.create)}</button>
      </div>
    </div>
    <div id="token-created" hidden>
      <div class="share-card share-card-warn">
        <h2>${escapeHtml(COPY.tokens.createdHeading)}</h2>
        <p>${escapeHtml(COPY.tokens.createdBody)}</p>
        <div class="share-mono-block" id="token-secret"></div>
        <div class="share-actions">
          <button type="button" class="share-btn share-btn-secondary" id="copy-token-btn">${escapeHtml(COPY.tokens.copyToken)}</button>
          <button type="button" class="share-btn share-btn-secondary" id="copy-mcp-btn">${escapeHtml(COPY.tokens.copyMcp)}</button>
        </div>
        <p class="share-meta">MCP configuration</p>
        <div class="share-mono-block" id="token-mcp"></div>
        <button type="button" class="share-btn" id="token-done-btn" style="margin-top:16px">${escapeHtml(COPY.tokens.done)}</button>
      </div>
    </div>
    <div id="token-list">${renderList()}</div>`;

  root.innerHTML = renderShell("tokens", COPY.tokens.title, body, user);

  root.querySelector("#new-token-btn")?.addEventListener("click", () => {
    root.querySelector("#token-create").hidden = false;
    root.querySelector("#token-name")?.focus();
  });

  root.querySelector("#create-token-btn")?.addEventListener("click", async () => {
    const name = root.querySelector("#token-name")?.value?.trim();
    const errEl = root.querySelector("#token-error");
    const btn = root.querySelector("#create-token-btn");
    errEl.hidden = true;
    if (!name) {
      errEl.textContent = "A token needs a name.";
      errEl.hidden = false;
      return;
    }
    btn.disabled = true;
    try {
      const created = await api("/api/v1/tokens", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, scopes: ["artifacts:read", "artifacts:write"] }),
      });
      root.querySelector("#token-create").hidden = true;
      root.querySelector("#token-list").hidden = true;
      root.querySelector("#token-created").hidden = false;
      root.querySelector("#token-secret").textContent = created.token;
      root.querySelector("#token-mcp").textContent = mcpBlock(created.token);
      root.querySelector("#copy-token-btn")?.addEventListener("click", () => {
        navigator.clipboard.writeText(created.token);
      });
      root.querySelector("#copy-mcp-btn")?.addEventListener("click", () => {
        navigator.clipboard.writeText(mcpBlock(created.token));
      });
      root.querySelector("#token-done-btn")?.addEventListener("click", async () => {
        await viewTokens(root, user);
      });
    } catch (e) {
      errEl.textContent = e.message;
      errEl.hidden = false;
    } finally {
      btn.disabled = false;
    }
  });

  root.querySelectorAll("[data-revoke]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!window.confirm(COPY.tokens.revokeConfirm)) return;
      const id = btn.getAttribute("data-revoke");
      try {
        await api(`/api/v1/tokens/${encodeURIComponent(id)}`, { method: "DELETE" });
        await viewTokens(root, user);
      } catch (e) {
        alert(e.message);
      }
    });
  });
}

async function viewSecurity(root, user) {
  let passkeys = [];
  try {
    const data = await api("/api/v1/auth/passkeys");
    passkeys = data?.items || [];
  } catch {
    passkeys = [];
  }

  let passkeySection;
  if (!passkeys.length) {
    passkeySection = `<p class="share-empty">${escapeHtml(COPY.security.noPasskeys)}</p>`;
  } else {
    if (passkeys.length === 1) {
      passkeySection = `<p class="share-empty">${escapeHtml(COPY.security.onePasskey)}</p>`;
    }
    const rows = passkeys
      .map(
        (pk) => `
        <tr>
          <td>${escapeHtml(pk.name)}</td>
          <td>${escapeHtml(formatWhen(pk.createdAt))}</td>
          <td>${escapeHtml(pk.lastUsedAt ? formatWhen(pk.lastUsedAt) : "—")}</td>
          <td>${escapeHtml(backupLabel(pk.backupState))}</td>
        </tr>`,
      )
      .join("");
    passkeySection += `
      <table class="share-table">
        <thead><tr>${COPY.security.passkeyColumns.map((c) => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  const body = `
    <div class="share-card">
      <h2>${escapeHtml(COPY.security.passkeys)}</h2>
      ${passkeySection}
      <div class="share-actions">
        <a href="/~/security/passkeys/new" class="share-btn">${escapeHtml(COPY.security.addPasskey)}</a>
      </div>
    </div>
    <div class="share-card">
      <h2>${escapeHtml(COPY.security.recovery)}</h2>
      <p>${escapeHtml(COPY.security.recoveryNone)}</p>
      <button type="button" class="share-btn share-btn-secondary" disabled>${escapeHtml(COPY.security.generate)}</button>
    </div>`;
  root.innerHTML = renderShell("security", COPY.security.title, body, user);
}

async function viewPasskeyNew(root, user) {
  let existing = [];
  try {
    const data = await api("/api/v1/auth/passkeys");
    existing = data?.items || [];
  } catch {
    existing = [];
  }

  let existingHtml = "";
  if (existing.length) {
    const rows = existing
      .map(
        (pk) => `
        <tr>
          <td>${escapeHtml(pk.name)}</td>
          <td>${escapeHtml(formatWhen(pk.createdAt))}</td>
        </tr>`,
      )
      .join("");
    existingHtml = `
      <h2 style="font-size:22px;margin:24px 0 8px">${escapeHtml(COPY.security.existingPasskeys)}</h2>
      <table class="share-table">
        <thead><tr><th>Name</th><th>Created</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  const body = `
    <p class="share-empty">A second passkey on another device is what makes losing the first uneventful.</p>
    ${existingHtml}
    <div class="share-form-row">
      <label for="pk-name">Name this passkey</label>
      <input class="share-input" id="pk-name" type="text" placeholder="MacBook Touch ID">
      <span style="font-size:15px;color:var(--share-muted)">Defaults to your authenticator's name. Change it to something you will recognize when you have three.</span>
    </div>
    <div class="share-error" id="pk-error" role="alert" hidden></div>
    <button type="button" class="share-btn" id="register-pk">Register a passkey</button>`;
  root.innerHTML = renderShell("security", COPY.security.addPasskey, body, user);
  root.querySelector("#register-pk")?.addEventListener("click", async () => {
    const btn = root.querySelector("#register-pk");
    const errEl = root.querySelector("#pk-error");
    const name = root.querySelector("#pk-name")?.value?.trim() || "Passkey";
    btn.disabled = true;
    errEl.hidden = true;
    try {
      const result = await passkeyRegister(name);
      if (result) window.location.replace("/~/security");
    } catch (e) {
      errEl.textContent = e.message;
      errEl.hidden = false;
    } finally {
      btn.disabled = false;
    }
  });
}

function formatUserCode(raw) {
  const compact = String(raw || "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "");
  if (compact.length <= 4) return compact;
  return `${compact.slice(0, 4)}-${compact.slice(4, 8)}`;
}

function userCodeReady(code) {
  return formatUserCode(code).replace(/-/g, "").length === 8;
}

async function viewAuthorize(root, user) {
  const params = new URLSearchParams(window.location.search);
  let userCode = formatUserCode(params.get("code") || "");
  let pending = null;
  let terminal = null; // "approved" | "denied"
  let approvedMeta = null;
  let lookupError = "";

  function render() {
    let main = `
      <p class="share-empty">${escapeHtml(COPY.authorize.intro)}</p>
      <div class="share-form-row">
        <label for="device-code">${escapeHtml(COPY.authorize.label)}</label>
        <input class="share-input mono" id="device-code" type="text" placeholder="${escapeHtml(COPY.authorize.placeholder)}" autocomplete="off" maxlength="9" value="${escapeHtml(userCode)}">
      </div>
      <div class="share-error" id="auth-error" role="alert" ${lookupError ? "" : "hidden"}>${escapeHtml(lookupError)}</div>
      <button type="button" class="share-btn" id="lookup-code" ${userCodeReady(userCode) && !pending ? "" : "disabled"}>${escapeHtml(COPY.authorize.lookup)}</button>`;

    if (pending) {
      main += `
        <div class="share-card" style="margin-top:24px">
          <h2>${escapeHtml(COPY.authorize.approvalHeading(pending.name))}</h2>
          <p><strong>${escapeHtml(COPY.authorize.rowRequestedFrom)}</strong> ${escapeHtml(pending.sourceIp || "—")}${pending.userAgent ? ` · ${escapeHtml(pending.userAgent)}` : ""}</p>
          <p><strong>${escapeHtml(COPY.authorize.rowStarted)}</strong> ${escapeHtml(formatWhen(pending.createdAt))}</p>
          <p><strong>${escapeHtml(COPY.authorize.rowScopes)}</strong><br>
            ${escapeHtml(COPY.authorize.scopeRead)}<br>
            ${escapeHtml(COPY.authorize.scopeWrite)}</p>
          <p class="share-meta">${escapeHtml(COPY.authorize.noShareLinks)}</p>
          <div class="share-actions">
            <button type="button" class="share-btn" id="approve-code">${escapeHtml(COPY.authorize.approve)}</button>
            <button type="button" class="share-btn share-btn-secondary" id="deny-code">${escapeHtml(COPY.authorize.deny)}</button>
          </div>
        </div>`;
    }

    if (terminal === "approved") {
      main += `
        <div class="share-card" style="margin-top:24px">
          <h2>${escapeHtml(COPY.authorize.approvedHeading)}</h2>
          <p>${escapeHtml(COPY.authorize.approvedBody(approvedMeta?.name || "The agent"))}</p>
          <a href="/~/tokens" class="share-btn">${escapeHtml(COPY.authorize.manageToken)}</a>
        </div>`;
    } else if (terminal === "denied") {
      main += `
        <div class="share-card" style="margin-top:24px">
          <h2>${escapeHtml(COPY.authorize.deniedHeading)}</h2>
          <p>${escapeHtml(COPY.authorize.deniedBody)}</p>
        </div>`;
    }

    root.innerHTML = renderShell("help", COPY.authorize.title, main, user);
    bindEvents();
  }

  async function doLookup() {
    lookupError = "";
    pending = null;
    terminal = null;
    try {
      pending = await api("/api/v1/auth/device/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userCode }),
      });
    } catch (e) {
      lookupError = e.code === "unknown_or_expired" ? COPY.authorize.unknown : e.message;
    }
    render();
  }

  function bindEvents() {
    const input = root.querySelector("#device-code");
    input?.addEventListener("input", () => {
      userCode = formatUserCode(input.value);
      input.value = userCode;
      lookupError = "";
      const btn = root.querySelector("#lookup-code");
      if (btn) btn.disabled = !userCodeReady(userCode) || !!pending;
    });
    input?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && userCodeReady(userCode) && !pending) doLookup();
    });
    root.querySelector("#lookup-code")?.addEventListener("click", doLookup);
    root.querySelector("#approve-code")?.addEventListener("click", async () => {
      const btn = root.querySelector("#approve-code");
      btn.disabled = true;
      try {
        approvedMeta = await api("/api/v1/auth/device/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ userCode }),
        });
        pending = null;
        terminal = "approved";
        render();
      } catch (e) {
        lookupError = e.code === "unknown_or_expired" ? COPY.authorize.unknown : e.message;
        pending = null;
        render();
      }
    });
    root.querySelector("#deny-code")?.addEventListener("click", async () => {
      try {
        await api("/api/v1/auth/device/deny", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ userCode }),
        });
        pending = null;
        terminal = "denied";
        render();
      } catch (e) {
        lookupError = e.code === "unknown_or_expired" ? COPY.authorize.unknown : e.message;
        pending = null;
        render();
      }
    });
  }

  render();
  if (userCodeReady(userCode) && params.get("code")) await doLookup();
}

function viewHelp(root, user, agents = false) {
  const body = agents
    ? `
    <nav class="share-help-nav">
      <a href="/~/help">← ${escapeHtml(COPY.help.title)}</a>
    </nav>
    <h2 style="font-size:22px;margin:0 0 16px">${escapeHtml(COPY.help.agentsTitle)}</h2>
    <p class="share-help-content">${escapeHtml(COPY.help.noToken)} <a href="/~/tokens">${escapeHtml(COPY.help.createToken)}</a></p>
    <p class="share-help-content">${escapeHtml(COPY.help.tokenNote)}</p>
    <div class="share-mono-block">${escapeHtml(mcpBlock())}</div>
    <p class="share-help-content">That URL is <strong>private</strong>. Open it in this browser, signed in, and it works. Open it in a private window and it is a 404, indistinguishable from a name that never existed.</p>`
    : `
    <nav class="share-help-nav">
      <a href="/~/help/agents">${escapeHtml(COPY.help.agentsTitle)}</a>
    </nav>
    <p class="share-help-content">${escapeHtml(COPY.help.quickstart)}</p>
    <h2>${escapeHtml(COPY.help.topics)}</h2>
    <ul class="share-help-content">
      <li>${escapeHtml(COPY.help.topicSearch)}</li>
      <li>${escapeHtml(COPY.help.topicExpiry)}</li>
      <li>${escapeHtml(COPY.help.topicOverwrite)}</li>
    </ul>`;
  root.innerHTML = renderShell("help", agents ? COPY.help.agentsTitle : COPY.help.title, body, user);
}

async function viewArtifactDetail(root, user, name, tab = "overview") {
  let art;
  try {
    art = await api(`/api/v1/artifacts/${encodeURIComponent(name)}`);
  } catch {
    root.innerHTML = renderShell(
      "artifacts",
      COPY.detail.back,
      `<p class="share-empty">No artifact with that name.</p>`,
      user,
    );
    return;
  }
  const meta = `${escapeHtml(art.kind)} · v${escapeHtml(art.seq)} · ${escapeHtml(art.fileCount)} files · ${escapeHtml(formatBytes(art.totalBytes))}`;
  const titleLine = art.title
    ? `<p class="share-meta">${escapeHtml(art.title)}</p>`
    : "";
  let body = `<p><a href="/~/artifacts">${escapeHtml(COPY.detail.back)}</a></p>${titleLine}${artifactTabs(name, tab)}`;
  if (tab === "files") {
    let files = [];
    try {
      const data = await api(`/api/v1/artifacts/${encodeURIComponent(name)}/files`);
      files = data?.items || [];
    } catch {
      files = [];
    }
    body += renderFileRows(files, art.entryPath, name);
    body += `<p class="share-meta">Entry file: <span class="mono">${escapeHtml(art.entryPath || "—")}</span></p>`;
  } else {
    const tags = art.tags?.length ? art.tags.join(", ") : "—";
    body += `
      <p class="share-meta">${meta}</p>
      <div class="share-actions">
        <a class="share-btn" href="${escapeHtml(art.url)}" target="_blank" rel="noopener">${escapeHtml(COPY.detail.open)}</a>
        <button type="button" class="share-btn share-btn-secondary" id="copy-url">${escapeHtml(COPY.detail.copyUrl)}</button>
        <button type="button" class="share-btn share-btn-danger" id="move-trash">${escapeHtml(COPY.detail.trashButton)}</button>
      </div>
      <div class="share-card">
        <h2>${escapeHtml(COPY.detail.sharingHeading)}</h2>
        <p><strong>${escapeHtml(COPY.detail.private)}</strong> — ${escapeHtml(COPY.detail.privateDetail)}</p>
      </div>
      <div class="share-card">
        <h2>${escapeHtml(COPY.detail.postedBy)}</h2>
        <p>${escapeHtml(art.createdBy?.name || (art.createdBy?.type === "token" ? "agent token" : "you"))}</p>
      </div>
      <div class="share-card">
        <h2>${escapeHtml(COPY.detail.details)}</h2>
        <p>Created ${escapeHtml(formatWhen(art.createdAt))}<br>
        Updated ${escapeHtml(formatWhen(art.updatedAt))}<br>
        Tags: ${escapeHtml(tags)}</p>
      </div>`;
  }
  root.innerHTML = renderShell("artifacts", art.name, body, user);
  root.querySelector("#copy-url")?.addEventListener("click", async () => {
    await navigator.clipboard.writeText(art.url);
    alert(COPY.detail.copyToast);
  });
  root.querySelector("#move-trash")?.addEventListener("click", async () => {
    if (!window.confirm(COPY.detail.trashConfirm)) return;
    try {
      await api(`/api/v1/artifacts/${encodeURIComponent(name)}`, { method: "DELETE" });
      window.location.replace("/~/artifacts");
    } catch (e) {
      alert(e.message);
    }
  });
}

function parseArtifactPath(path) {
  const prefix = "/~/artifacts/";
  if (!path.startsWith(prefix)) return null;
  const rest = path.slice(prefix.length);
  if (rest.endsWith("/files")) {
    return { name: decodeURIComponent(rest.slice(0, -"/files".length)), tab: "files" };
  }
  if (rest.includes("/")) return null;
  return { name: decodeURIComponent(rest), tab: "overview" };
}

async function route() {
  const root = document.getElementById("app");
  const path = window.location.pathname.replace(/\/+$/, "") || "/~";
  const user = await sessionUser();

  if (!user && !PUBLIC_ROUTES.has(path) && !path.startsWith("/~/invite/")) {
    window.location.replace(`/~/signin?next=${encodeURIComponent(path + window.location.search)}`);
    return;
  }

  if (path === "/~/signin" || path === "/~/signin/recovery") {
    if (user) {
      window.location.replace("/~/artifacts");
      return;
    }
    await viewSignIn(root);
    return;
  }

  if (path === "/~/artifacts") {
    await viewArtifacts(root, user);
    return;
  }
  if (path === "/~/trash") {
    await viewTrash(root, user);
    return;
  }
  if (path === "/~/tokens") {
    await viewTokens(root, user);
    return;
  }
  if (path === "/~/security") {
    await viewSecurity(root, user);
    return;
  }
  if (path === "/~/security/passkeys/new") {
    await viewPasskeyNew(root, user);
    return;
  }
  if (path === "/~/authorize") {
    await viewAuthorize(root, user);
    return;
  }
  if (path === "/~/help/agents") {
    viewHelp(root, user, true);
    return;
  }
  if (path === "/~/help") {
    viewHelp(root, user, false);
    return;
  }

  const artifact = parseArtifactPath(path);
  if (artifact) {
    await viewArtifactDetail(root, user, artifact.name, artifact.tab);
    return;
  }

  root.innerHTML = renderShell("artifacts", "Share", `<p class="share-empty">This screen is not built yet.</p>`, user);
}

window.addEventListener("popstate", () => route());
document.addEventListener("DOMContentLoaded", () => route());
