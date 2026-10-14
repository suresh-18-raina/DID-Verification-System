/* DID Verification System - front-end logic (plain JavaScript, no libraries) */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const short = (h, n = 10) => (h && h.length > n * 2 + 1 ? h.slice(0, n) + "…" + h.slice(-n) : h || "");

  function toast(msg, bad) {
    const t = $("#toast");
    t.textContent = msg;
    t.className = "toast show" + (bad ? " bad" : "");
    clearTimeout(toast.t);
    toast.t = setTimeout(() => (t.className = "toast"), 3200);
  }

  async function api(path, body, method) {
    const opts = { method: method || (body !== undefined ? "POST" : "GET"), headers: {} };
    if (body !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
    let res, data;
    try { res = await fetch(path, opts); data = await res.json(); }
    catch (e) { throw new Error("Could not reach the server. Is app.py still running?"); }
    if (data.success === false) throw new Error(data.error || "Something went wrong.");
    return data;
  }

  async function busy(btn, fn) {
    const label = btn.textContent; btn.disabled = true;
    try { await fn(); } catch (e) { toast(e.message, true); } finally { btn.disabled = false; btn.textContent = label; }
  }

  // click-to-copy for any element with data-copy
  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-copy]");
    if (el && navigator.clipboard) navigator.clipboard.writeText(el.dataset.copy).then(() => toast("Copied to clipboard"));
  });

  /* ---------- Home ---------- */
  function initHome() {
    $("#demo-btn").addEventListener("click", (e) => busy(e.target, async () => {
      e.target.textContent = "Creating demo data…";
      const r = await api("/api/demo/seed", {});
      location.href = "/verify?id=" + encodeURIComponent(r.credential_id) + "&auto=1";
    }));
    $("#reset-btn").addEventListener("click", async () => {
      if (!confirm("Delete ALL identities, private keys, credentials and ledger blocks?")) return;
      try { await api("/api/reset", {}); toast("All data deleted"); setTimeout(() => location.reload(), 600); }
      catch (e) { toast(e.message, true); }
    });
  }

  /* ---------- Create identity ---------- */
  function initCreate() {
    const form = $("#identity-form");
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const name = form.name.value.trim();
      if (!name) { form.name.classList.add("err"); form.name.focus(); return toast("Please enter a name.", true); }
      form.name.classList.remove("err");
      busy(form.querySelector("button"), async () => {
        const r = await api("/api/identity/create", { name, role: form.role.value });
        const key = r.document.verificationMethod[0].publicKeyHex;
        const box = $("#identity-result");
        box.innerHTML = `
          <h3>Identity created</h3>
          <div class="kv">
            <div><span>Name</span><b>${esc(name)}</b></div>
            <div><span>DID</span><code class="copy" data-copy="${esc(r.did)}" title="Click to copy">${esc(r.did)}</code></div>
            <div><span>Public key</span><code class="copy" data-copy="${esc(key)}" title="Click to copy">${esc(short(key, 14))}</code></div>
            <div><span>Key type</span><code>Ed25519</code></div>
            <div><span>Ledger</span><code>Registered in block #${r.block_index}</code></div>
          </div>
          <p class="hint">The private key is saved on this computer and is never displayed.</p>
          <div class="row">
            <a class="btn primary" href="/issue-credential">Next: issue a credential</a>
            <a class="btn ghost" href="/identity/${esc(r.folder)}">View DID Document</a>
          </div>`;
        box.hidden = false; $("#identity-help").hidden = true;
        form.reset(); toast("Identity created");
      });
    });
  }

  /* ---------- Issue credential ---------- */
  function initIssue() {
    const form = $("#issue-form");
    if (!form) return;
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const payload = Object.fromEntries(new FormData(form).entries());
      const missing = ["name", "student_id", "department", "course"].filter((k) => !String(payload[k] || "").trim());
      form.querySelectorAll("input").forEach((i) => i.classList.toggle("err", missing.includes(i.name)));
      if (missing.length) return toast("Please fill in every student detail.", true);
      busy(form.querySelector("button[type=submit]"), async () => {
        const r = await api("/api/credential/issue", payload);
        const c = r.credential, id = encodeURIComponent(c.credential_id);
        const box = $("#issue-result");
        box.innerHTML = `
          <h3>Credential signed and recorded</h3>
          <div class="kv">
            <div><span>Credential ID</span><code>${esc(c.credential_id)}</code></div>
            <div><span>Student</span><b>${esc(c.subject.name)}</b> · ${esc(c.subject.student_id)}</div>
            <div><span>SHA-256 hash</span><code class="copy" data-copy="${esc(c.proof.hash)}" title="Click to copy">${esc(short(c.proof.hash, 14))}</code></div>
            <div><span>Signature</span><code class="copy" data-copy="${esc(c.proof.signature)}" title="Click to copy">${esc(short(c.proof.signature, 14))}</code></div>
            <div><span>Ledger</span><code>Block #${r.block_index}</code></div>
          </div>
          <div class="row">
            <a class="btn primary" href="/verify?id=${id}&auto=1">Verify it now</a>
            <a class="btn ghost" href="/api/credential/${id}/download">Download JSON</a>
          </div>`;
        box.hidden = false; $("#issue-help").hidden = true; toast("Credential issued");
      });
    });
  }

  /* ---------- Credentials list ---------- */
  function initCredentials() {
    document.querySelectorAll(".revoke-btn").forEach((b) => b.addEventListener("click", async () => {
      if (!confirm("Revoke this credential? The issuer signs a notice and it is recorded on the ledger. This cannot be undone.")) return;
      try { await api("/api/credential/" + b.dataset.id + "/revoke", {}); toast("Credential revoked"); setTimeout(() => location.reload(), 600); }
      catch (e) { toast(e.message, true); }
    }));
  }

  /* ---------- Verify ---------- */
  const SEAL_OK = `<svg class="seal" viewBox="0 0 96 96" role="img" aria-label="Verified"><circle cx="48" cy="48" r="44" fill="#E2F4EC" stroke="#117A55" stroke-width="4"/><circle cx="48" cy="48" r="36" fill="none" stroke="#117A55" stroke-width="1.5" stroke-dasharray="3 4"/><path d="M30 49l13 13 24-27" fill="none" stroke="#117A55" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const SEAL_BAD = `<svg class="seal" viewBox="0 0 96 96" role="img" aria-label="Rejected"><circle cx="48" cy="48" r="44" fill="#FCEAE8" stroke="#B42318" stroke-width="4"/><circle cx="48" cy="48" r="36" fill="none" stroke="#B42318" stroke-width="1.5" stroke-dasharray="3 4"/><path d="M33 33l30 30M63 33L33 63" fill="none" stroke="#B42318" stroke-width="7" stroke-linecap="round"/></svg>`;

  function renderVerdict(r) {
    const icon = { pass: "✓", fail: "✕", skip: "–" };
    const t = r.technical || {};
    $("#verify-out").innerHTML = `
      <div class="verdict ${r.valid ? "good" : "bad"}">
        ${r.valid ? SEAL_OK : SEAL_BAD}
        <div><h2>${r.valid ? "Credential verified" : "Verification failed"}</h2>
        <p>${esc(r.reason)}</p><p class="small muted">${r.passed} of ${r.total} checks passed</p></div>
      </div>
      <ul class="checks">${r.checks.map((c) => `
        <li class="${c.status}"><span class="ico ${c.status}" aria-hidden="true">${icon[c.status]}</span>
        <div><b>${esc(c.label)}<span class="sr" style="position:absolute;left:-999px"> — ${c.status === "pass" ? "passed" : c.status === "fail" ? "failed" : "not checked"}</span></b><span>${esc(c.detail)}</span></div></li>`).join("")}
      </ul>
      <details><summary>Show the technical values</summary><div class="tech">
        <div><b>SHA-256 recalculated now</b><code>${esc(t.recomputed_hash)}</code></div>
        <div><b>SHA-256 stored in the credential</b><code>${esc(t.claimed_hash)}</code></div>
        <div><b>Issuer public key (Ed25519)</b><code>${esc(t.issuer_public_key || "not found")}</code></div>
        <div><b>Signature</b><code>${esc(t.signature)}</code></div>
      </div></details>`;
  }

  function initVerify() {
    const text = $("#cred-text"), saved = $("#saved");
    async function loadSaved(id) {
      try { const r = await api("/api/credential/" + encodeURIComponent(id)); text.value = JSON.stringify(r.credential, null, 2); saved.value = id; return true; }
      catch (e) { toast(e.message, true); return false; }
    }
    async function run() {
      if (!text.value.trim()) return toast("Paste a credential or choose a saved one first.", true);
      const r = await api("/api/credential/verify", { credential: text.value });
      renderVerdict(r);
      $("#verify-out").scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    saved.addEventListener("change", () => saved.value && loadSaved(saved.value));
    $("#file").addEventListener("change", (e) => {
      const f = e.target.files[0]; if (!f) return;
      const reader = new FileReader();
      reader.onload = () => { text.value = reader.result; saved.value = ""; toast("File loaded"); };
      reader.readAsText(f);
    });
    $("#verify-btn").addEventListener("click", (e) => busy(e.target, run));
    $("#tamper-btn").addEventListener("click", () => {
      let c;
      try { c = JSON.parse(text.value); } catch (e) { return toast("Load a valid credential first.", true); }
      if (!c.subject) return toast("This credential has no subject to edit.", true);
      const old = c.subject.student_id;
      c.subject.student_id = old === "CS999" ? "CS998" : "CS999";
      text.value = JSON.stringify(c, null, 2);
      $("#tamper-hint").textContent = `Changed student_id from "${old}" to "${c.subject.student_id}" without re-signing. Press Verify.`;
      toast("Credential edited — now verify it");
    });

    const params = new URLSearchParams(location.search);
    if (params.get("id")) loadSaved(params.get("id")).then((ok) => ok && params.get("auto") && run().catch((e) => toast(e.message, true)));
  }

  /* ---------- Ledger ---------- */
  function blockSummary(b) {
    const d = b.data;
    if (b.type === "GENESIS") return esc(d.message);
    if (b.type === "DID_REGISTERED") return `Registered a <b>${esc(d.role)}</b> identity<br><code>${esc(d.did)}</code>`;
    if (b.type === "CREDENTIAL_ISSUED") return `Credential <code>${esc(d.credential_id)}</code> was signed.<br>Fingerprint: <code>${esc(short(d.credential_hash, 12))}</code>`;
    if (b.type === "CREDENTIAL_REVOKED") return `Credential <code>${esc(d.credential_id)}</code> was revoked by its issuer.`;
    return esc(JSON.stringify(d));
  }
  const TYPE_LABEL = { GENESIS: "Start", DID_REGISTERED: "Identity", CREDENTIAL_ISSUED: "Credential issued", CREDENTIAL_REVOKED: "Credential revoked" };

  async function loadChain() {
    const r = await api("/api/blockchain");
    const banner = $("#chain-banner");
    banner.className = "banner " + (r.valid ? "good" : "bad");
    banner.textContent = r.valid
      ? `Ledger is valid — all ${r.blocks.length} blocks are linked correctly.`
      : `Ledger is INVALID — the first problem is at block #${r.first_invalid}.`;
    $("#lab-restore").disabled = !r.has_backup;
    const sel = $("#lab-index"), keep = sel.value;
    sel.innerHTML = r.blocks.map((b) => `<option value="${b.index}">Block #${b.index} · ${esc(TYPE_LABEL[b.type] || b.type)}</option>`).join("");
    if (keep) sel.value = keep;
    $("#chain").innerHTML = r.blocks.map((b) => `
      <li class="block ${b.valid ? "" : "bad"}">
        <header><strong>Block #${b.index}</strong><span class="type ${b.type}">${esc(TYPE_LABEL[b.type] || b.type)}</span>
          <span class="time">${esc(b.timestamp)}</span></header>
        <div class="bdata">${blockSummary(b)}</div>
        ${b.problem ? `<div class="prob">✕ ${esc(b.problem)}</div>` : ""}
        <div class="hashes">
          <div>previous_hash<code title="${esc(b.previous_hash)}">${esc(b.previous_hash)}</code></div>
          <div>hash<code title="${esc(b.hash)}">${esc(b.hash)}</code></div>
        </div>
        <details><summary>Raw block</summary><pre class="code">${esc(JSON.stringify(b, null, 2))}</pre></details>
      </li>`).join("");
  }

  function initLedger() {
    loadChain().catch((e) => toast(e.message, true));
    $("#lab-tamper").addEventListener("click", (e) => busy(e.target, async () => {
      const r = await api("/api/blockchain/tamper", { index: $("#lab-index").value, recompute: $("#lab-recompute").checked });
      $("#lab-note").textContent = r.note || (($("#lab-recompute").checked)
        ? "The edited block now looks fine on its own, but the NEXT block no longer points to it."
        : "The block's contents no longer match its stored hash.");
      await loadChain(); toast("Block tampered — see the red marks", true);
    }));
    $("#lab-restore").addEventListener("click", (e) => busy(e.target, async () => {
      await api("/api/blockchain/restore", {});
      $("#lab-note").textContent = ""; await loadChain(); toast("Ledger restored");
    }));
  }

  const init = { home: initHome, create: initCreate, issue: initIssue, credentials: initCredentials, verify: initVerify, ledger: initLedger };
  const fn = init[document.body.dataset.page];
  if (fn) fn();
})();
