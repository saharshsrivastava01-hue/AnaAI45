const $ = id => document.getElementById(id);
let trustedAdminEndpoint = "";

function base() {
  const value = $("api").value.trim();
  if (!value) return "";
  let parsed;
  try { parsed = new URL(value); }
  catch { throw Error("Enter a valid HTTPS Worker API URL."); }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw Error("The Worker API URL must use HTTPS and cannot contain credentials, a query or a fragment.");
  }
  return parsed.href.replace(/\/+$/, "");
}

function requireTrustedAdminEndpoint() {
  let endpoint;
  try { endpoint = base(); }
  catch (error) {
    trustedAdminEndpoint = "";
    $("trustAdminEndpoint").checked = false;
    $("adminToken").value = "";
    throw error;
  }
  if (!endpoint || !$("trustAdminEndpoint").checked || trustedAdminEndpoint !== endpoint) {
    trustedAdminEndpoint = "";
    $("trustAdminEndpoint").checked = false;
    $("adminToken").value = "";
    throw Error("Verify the exact HTTPS Worker URL and enable its page-session trust checkbox before sending the operator token.");
  }
  return endpoint;
}

function updateAdminEndpointTrust() {
  const checkbox = $("trustAdminEndpoint");
  if (!checkbox.checked) {
    trustedAdminEndpoint = "";
    msg("adminTrustStatus", "Endpoint trust is off. The operator token will not be sent.", false);
    return;
  }
  let endpoint;
  try { endpoint = base(); }
  catch (error) {
    checkbox.checked = false;
    trustedAdminEndpoint = "";
    throw error;
  }
  if (!endpoint) {
    checkbox.checked = false;
    trustedAdminEndpoint = "";
    throw Error("Enter the Worker API URL before trusting it.");
  }
  const accepted = window.confirm(
    "ULTRA will send the shared moderation bearer token only to this exact endpoint for this page session:\\n\\n" +
    endpoint +
    "\\n\\nContinue only if you independently verified that this endpoint is controlled by the ULTRA operator."
  );
  if (!accepted) {
    checkbox.checked = false;
    trustedAdminEndpoint = "";
    msg("adminTrustStatus", "Endpoint trust was not enabled.", false);
    return;
  }
  trustedAdminEndpoint = endpoint;
  msg("adminTrustStatus", "Endpoint pinned for this page session: " + endpoint + ". This confirmation does not independently prove domain ownership.", true);
}

function msg(id, text, ok) {
  const target = $(id);
  target.textContent = text;
  target.className = "status " + (ok === true ? "good" : ok === false ? "bad" : "small");
}

function element(tag, className = "", text = null) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== null) node.textContent = String(text);
  return node;
}

function actionButton(label, className, attributes = {}) {
  const button = element("button", className, label);
  button.type = "button";
  for (const [name, value] of Object.entries(attributes)) button.dataset[name] = String(value);
  return button;
}

function safeHttpsHref(value) {
  try {
    const url = new URL(value);
    if (url.protocol === "https:" && !url.username && !url.password) return url.href;
  } catch {}
  return null;
}

async function call(path, opts = {}) {
  const apiBase = base();
  if (!apiBase) throw Error("Enter the deployed Worker API URL first.");
  const r = await fetch(apiBase + path, {
    ...opts,
    credentials: "omit",
    redirect: "error",
    cache: "no-store",
    referrerPolicy: "no-referrer",
    headers: { "content-type":"application/json", ...(opts.headers || {}) }
  });
  const d = await r.json().catch(() => ({ error:"Invalid API response" }));
  if (!r.ok) throw Error(d.error || "Request failed (" + r.status + ")");
  return d;
}

const KEY_DB = "ultra-creator-keys-v1";
function openKeyDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(KEY_DB, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains("keys")) request.result.createObjectStore("keys", { keyPath:"handle" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || Error("Could not open local creator-key storage."));
    request.onblocked = () => reject(Error("Creator-key storage upgrade is blocked by another open tab. Close other ULTRA tabs and retry."));
  });
}
async function keyStore(mode, action, value) {
  const db = await openKeyDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("keys", mode);
    const store = tx.objectStore("keys");
    const request = action === "get" ? store.get(value) : action === "all" ? store.getAll() : action === "delete" ? store.delete(value) : store.put(value);
    let result;
    request.onsuccess = () => { result = request.result; };
    request.onerror = () => reject(request.error || Error("Creator-key storage failed."));
    tx.oncomplete = () => { db.close(); resolve(result); };
    tx.onerror = () => { db.close(); reject(tx.error || Error("Creator-key storage transaction failed.")); };
    tx.onabort = () => { db.close(); reject(tx.error || Error("Creator-key storage transaction was aborted.")); };
  });
}
const getKey = handle => keyStore("readonly", "get", handle);
const listKeys = () => keyStore("readonly", "all");
const saveKey = record => keyStore("readwrite", "put", record);
const deleteKey = handle => keyStore("readwrite", "delete", handle);

function toBase64(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}
function toHex(bytes) {
  return [...bytes].map(x => x.toString(16).padStart(2, "0")).join("");
}
async function signPayload(privateKey, payload) {
  const signature = await crypto.subtle.sign(
    { name:"ECDSA", hash:"SHA-256" },
    privateKey,
    new TextEncoder().encode(JSON.stringify(payload))
  );
  return toBase64(new Uint8Array(signature));
}
async function createOrLoadSigningKey(handle) {
  let account = await getKey(handle);
  if (account) return account;
  const pair = await crypto.subtle.generateKey({ name:"ECDSA", namedCurve:"P-256" }, false, ["sign", "verify"]);
  const publicBytes = new Uint8Array(await crypto.subtle.exportKey("spki", pair.publicKey));
  const publicKey = toBase64(publicBytes);
  const fingerprint = toHex(new Uint8Array(await crypto.subtle.digest("SHA-256", publicBytes)));
  account = { handle, privateKey:pair.privateKey, publicKey, fingerprint, creatorId:null, status:"local key only" };
  await saveKey(account);
  return account;
}

async function refreshAccounts(selectedHandle) {
  let accounts = [];
  try { accounts = await listKeys(); }
  catch (e) { msg("accountStatus", e.message, false); return; }
  if (base()) {
    for (const account of accounts) {
      try {
        const owner = await call("/api/v1/creators/by-key/" + account.fingerprint);
        account.creatorId = owner.id;
        account.status = owner.status;
        await saveKey(account);
      } catch {}
    }
  }
  accounts = await listKeys();
  const select = $("creatorAccount");
  select.replaceChildren();
  if (accounts.length) {
    for (const account of accounts) {
      const option = element("option", "", account.handle + " · " + (account.status || (account.creatorId ? "registered" : "local key")));
      option.value = account.handle;
      select.append(option);
    }
  } else {
    const option = element("option", "", "No local creator keys found");
    option.value = "";
    select.append(option);
  }
  if (selectedHandle && accounts.some(a => a.handle === selectedHandle)) select.value = selectedHandle;
  await updateAccountStatus();
}

async function selectedAccount() {
  const handle = $("creatorAccount").value;
  return handle ? getKey(handle) : null;
}
async function updateAccountStatus() {
  const target = $("accountStatus");
  target.replaceChildren();
  const account = await selectedAccount();
  if (!account) { target.textContent = "No local creator key selected."; return; }
  const description = account.creatorId
    ? "@" + account.handle + " · " + (account.status || "registered") + ". Posts are signed locally and queued for moderation."
    : "@" + account.handle + " has a local key but no server account yet. Retry profile creation with the same handle and details.";
  target.append(element("span", "", description));
  if (account.status === "rejected") {
    target.append(element("p", "small", "This rejected claim's handle has been released. You can delete this local key before making a fresh claim. Deletion is permanent; the old key can no longer sign an appeal."));
    const remove = actionButton("Delete rejected local key", "btn alt");
    remove.addEventListener("click", async () => {
      const confirmed = window.confirm(
        "Permanently delete the local signing key for @" + account.handle + "? The rejected server record and audit history will remain, but this browser will no longer be able to sign with this key."
      );
      if (!confirmed) return;
      remove.disabled = true;
      try {
        await deleteKey(account.handle);
        await refreshAccounts();
        msg("accountStatus", "Rejected local key deleted. You can now submit a fresh claim for the released handle.", true);
      } catch (error) {
        remove.disabled = false;
        msg("accountStatus", error.message, false);
      }
    });
    target.append(remove);
  }
}

async function submitCreatorProfile() {
  if (!window.crypto || !crypto.subtle || !window.indexedDB) throw Error("Secure browser cryptography and IndexedDB are required. Open this page over HTTPS.");
  const handle = $("handle").value.trim().toLowerCase();
  const displayName = $("display").value.trim();
  const bio = $("bio").value.trim();
  const website = $("website").value.trim();
  if (!/^[a-z0-9_]{3,24}$/.test(handle) || !displayName) throw Error("Enter a valid handle and display name.");
  if (website && !safeHttpsHref(website)) throw Error("Website must be a valid HTTPS URL without embedded credentials.");
  const existing = await getKey(handle);
  if (existing && existing.creatorId) throw Error("This browser already has a creator key for @" + handle + ". Select it in the post form.");
  const account = await createOrLoadSigningKey(handle);
  const createdAt = new Date().toISOString();
  const claim = { handle, displayName, bio, website, createdAt, version:1, publicKey:account.publicKey, fingerprint:account.fingerprint };
  const signature = await signPayload(account.privateKey, claim);
  await saveKey({ ...account, displayName, bio, website });
  const result = await call("/api/v1/creators", { method:"POST", body:JSON.stringify({ ...claim, signature }) });
  await saveKey({ ...account, creatorId:result.id, status:result.status, displayName, bio, website });
  await refreshAccounts(handle);
  msg("profileStatus", result.message + " Your signing key is stored only in this browser.", true);
}

async function submitSignedPost() {
  if (!window.crypto || !crypto.subtle || !window.indexedDB) throw Error("Secure browser cryptography and IndexedDB are required. Open this page over HTTPS.");
  const account = await selectedAccount();
  if (!account || !account.creatorId) throw Error("Select a registered local creator account first.");
  if (account.status !== "approved") throw Error("This creator account must be approved before it can submit posts.");
  const title = $("title").value.trim();
  const body = $("body").value.trim();
  const category = $("category").value.trim();
  if (!title || !body || title.length > 100 || body.length > 4000) throw Error("Enter a title and post content within the displayed limits.");
  const post = {
    creatorId:account.creatorId,
    id:crypto.randomUUID(),
    title,
    body,
    category,
    createdAt:new Date().toISOString(),
    version:1,
    fingerprint:account.fingerprint
  };
  const signature = await signPayload(account.privateKey, post);
  const result = await call("/api/v1/posts", { method:"POST", body:JSON.stringify({ ...post, signature }) });
  msg("postStatus", result.message, true);
  $("title").value = "";
  $("body").value = "";
}

async function loadCreators() {
  const container = $("creators");
  container.replaceChildren();
  try {
    const d = await call("/api/v1/creators");
    if (!Array.isArray(d.items) || d.items.length === 0) {
      container.append(element("div", "feedempty", "No approved creators yet."));
      return;
    }
    for (const creator of d.items) {
      const article = element("article", "post");
      const heading = element("b", "", "@" + creator.handle);
      article.append(heading, document.createTextNode(" · " + creator.display_name));
      article.append(element("p", "", creator.bio || ""));
      const href = creator.website ? safeHttpsHref(creator.website) : null;
      if (href) {
        const link = element("a", "", "Website ↗");
        link.href = href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        article.append(link);
      }
      container.append(article);
    }
  } catch (e) { container.textContent = e.message; }
}

async function loadFeed() {
  const container = $("feed");
  container.replaceChildren();
  try {
    const d = await call("/api/v1/posts");
    if (!Array.isArray(d.items) || d.items.length === 0) {
      container.append(element("div", "feedempty", "No approved posts yet."));
      return;
    }
    for (const post of d.items) {
      const article = element("article", "post");
      article.append(element("div", "tag", post.category + " · @" + post.handle));
      article.append(element("h3", "", post.title));
      article.append(element("p", "", post.body));
      const date = new Date(post.created_at);
      article.append(element("div", "small", Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleString()));
      container.append(article);
    }
  } catch (e) { container.textContent = e.message; }
}

async function connect() {
  try {
    const health = await call("/health");
    try { localStorage.setItem("ultra_creator_api", base()); } catch {}
    msg("connection", "Connected to " + health.service + " v" + health.version, true);
    await Promise.all([loadCreators(), loadFeed()]);
    await refreshAccounts();
  } catch (e) { msg("connection", e.message, false); }
}

async function moderate(path, status) {
  requireTrustedAdminEndpoint();
  const token = $("adminToken").value;
  if (!token) throw Error("Enter the operator token.");
  return call(path, { method:"POST", headers:{ authorization:"Bearer " + token }, body:JSON.stringify({ status }) });
}

function moderationButton(label, kind, id, status, className = "btn") {
  return actionButton(label, className, { kind, id, status });
}
function reportButton(label, id, status, className = "btn") {
  return actionButton(label, className, { reportId:id, reportStatus:status });
}

async function loadQueue() {
  const container = $("queue");
  const status = "queueStatus";
  container.replaceChildren();
  try {
    requireTrustedAdminEndpoint();
    const token = $("adminToken").value;
    if (!token) throw Error("Enter the operator token.");
    const d = await call("/api/v1/moderation/queue", { headers:{ authorization:"Bearer " + token } });

    for (const creator of d.creators || []) {
      const article = element("article", "post");
      article.append(element("b", "", "Creator @" + creator.handle));
      article.append(document.createTextNode(" · " + creator.display_name));
      article.append(element("p", "", creator.bio || ""));
      article.append(element("div", "small", creator.ownership_verified_at ? "Cryptographic owner proof verified" : "Legacy profile — no verified owner key"));
      article.append(moderationButton("Approve", "creators", creator.id, "approved"));
      article.append(moderationButton("Reject", "creators", creator.id, "rejected", "btn alt"));
      container.append(article);
    }

    for (const post of d.posts || []) {
      const article = element("article", "post");
      article.append(element("b", "", "Post: " + post.title));
      article.append(document.createTextNode(" · @" + post.handle));
      article.append(element("p", "", post.body));
      article.append(moderationButton("Approve", "posts", post.id, "approved"));
      article.append(moderationButton("Reject", "posts", post.id, "rejected", "btn alt"));
      container.append(article);
    }

    for (const report of d.reports || []) {
      const article = element("article", "post");
      article.append(element("b", "", "Report: " + report.label));
      article.append(document.createTextNode(" · " + report.reason));
      article.append(element("p", "", report.details || ""));
      article.append(reportButton("Mark reviewed", report.id, "reviewed"));
      article.append(reportButton("Dismiss", report.id, "dismissed", "btn alt"));
      container.append(article);
    }

    if ((d.events || []).length) {
      const section = element("section", "post");
      section.append(element("h3", "", "Recent moderation activity"));
      for (const event of d.events) {
        const date = new Date(event.created_at);
        const dateText = Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleString();
        section.append(element("p", "small",
          event.target_type + " " + event.target_id + " · " +
          event.from_status + " → " + event.to_status + " · " +
          event.actor_type + " · " + dateText
        ));
      }
      container.append(section);
    }

    if (!container.childElementCount) container.append(element("p", "", "No pending submissions or reports."));
    msg(status, "Loaded " + (d.creators || []).length + " creator(s), " + (d.posts || []).length + " post(s), " + (d.reports || []).length + " report(s).", true);

    container.querySelectorAll("button[data-kind]").forEach(button => {
      button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          await moderate("/api/v1/moderation/" + button.dataset.kind + "/" + button.dataset.id, button.dataset.status);
          await loadQueue();
          await Promise.all([loadCreators(), loadFeed()]);
        } catch (e) {
          button.disabled = false;
          msg(status, e.message, false);
        }
      });
    });

    container.querySelectorAll("button[data-report-id]").forEach(button => {
      button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          await moderate("/api/v1/moderation/reports/" + button.dataset.reportId, button.dataset.reportStatus);
          await loadQueue();
        } catch (e) {
          button.disabled = false;
          msg(status, e.message, false);
        }
      });
    });
  } catch (e) {
    container.replaceChildren();
    msg(status, e.message, false);
  }
}

$("api").addEventListener("input", () => {
  trustedAdminEndpoint = "";
  $("trustAdminEndpoint").checked = false;
  $("adminToken").value = "";
  msg("adminTrustStatus", "Worker URL changed. Verify and trust the new exact endpoint before moderation.", false);
});
$("trustAdminEndpoint").addEventListener("change", () => {
  try { updateAdminEndpointTrust(); }
  catch (error) { msg("adminTrustStatus", error.message, false); }
});

$("connect").addEventListener("click", connect);
$("createProfile").addEventListener("click", async () => {
  try { await submitCreatorProfile(); }
  catch (e) { msg("profileStatus", e.message, false); }
});
$("submitPost").addEventListener("click", async () => {
  try { await submitSignedPost(); }
  catch (e) { msg("postStatus", e.message, false); }
});
$("creatorAccount").addEventListener("change", updateAccountStatus);
$("loadCreators").addEventListener("click", loadCreators);
$("loadFeed").addEventListener("click", loadFeed);
$("loadQueue").addEventListener("click", loadQueue);
$("report").addEventListener("click", async () => {
  try {
    const result = await call("/api/v1/reports", {
      method:"POST",
      body:JSON.stringify({
        label:$("reportLabel").value,
        reason:$("reason").value,
        details:$("reportDetails").value
      })
    });
    msg("reportStatus", result.message, true);
  } catch (e) { msg("reportStatus", e.message, false); }
});

try { $("api").value = localStorage.getItem("ultra_creator_api") || ""; } catch {}
refreshAccounts().catch(() => {});
try { if (base()) connect(); } catch (e) { msg("connection", e.message, false); }
