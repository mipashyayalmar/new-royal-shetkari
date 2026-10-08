/*
 * Scan-and-pay with the restaurant's own UPI QR (payments/upi_service.py).
 *
 *   const v = await UpiVerify.collect({ orderId, amount });
 *   if (v) post to pay-order with { method: 'upi', amount, ...v }
 *
 * Showing the QR opens a *pending* request on the server; nothing is paid.
 * collect() resolves only when a cashier/manager/owner types the UPI
 * transaction reference and ticks that the money was received; pay-order
 * then records the payment and who verified it. Closing the panel, the
 * guest scanning, or the guest pressing "I have paid" never pays the bill.
 *
 * Needs the global `apiClient` and `ui` from templates/core/base.html.
 */
(function () {
  "use strict";

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

  const REF_RE = /^[A-Za-z0-9]{6,35}$/;

  function buildOverlay() {
    const el = document.createElement("div");
    el.id = "upi-verify-overlay";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-modal", "true");
    el.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.65);z-index:2000;display:flex;align-items:center;justify-content:center;padding:12px;";
    document.body.appendChild(el);
    return el;
  }

  function render(el, data, amount) {
    const r = data.request, q = data.qr || {};
    const instructions = (q.instructions || []).map((t) => `<li>${esc(t)}</li>`).join("");
    const qrBlock = q.has_qr
      ? `<img src="${esc(q.qr_url)}" alt="Scan and pay QR" style="display:block;margin:0 auto;max-width:100%;max-height:52vh;width:auto;height:auto;background:#fff;">`
      : `<div style="padding:1.5rem;border:1px dashed var(--border-color);color:var(--text-muted);font-size:0.85rem;">
           No QR image uploaded yet. Owner: Setup &rarr; Payment Methods &rarr; upload QR.</div>`;
    const verifyBlock = data.can_verify ? `
        <label style="display:block;font-size:0.62rem;text-transform:uppercase;letter-spacing:2px;color:var(--text-muted);margin:0.9rem 0 0.3rem;text-align:left;">
          UPI transaction reference (UTR / transaction ID)</label>
        <input id="upiv-ref" type="text" autocomplete="off" maxlength="40" inputmode="text"
               placeholder="e.g. 427812345678 or T2410081234567890"
               style="width:100%;padding:0.6rem 0.7rem;background:transparent;border:1px solid var(--border-color);color:var(--text-main);font-family:monospace;font-size:0.95rem;">
        <label style="display:flex;gap:0.5rem;align-items:flex-start;text-align:left;font-size:0.8rem;margin-top:0.7rem;cursor:pointer;">
          <input id="upiv-ok" type="checkbox" style="margin-top:3px;">
          <span>I have checked the restaurant's PhonePe / bank app and <b>&#8377;${esc(r.amount)}</b> from this guest has been received.</span>
        </label>
        <button id="upiv-confirm" disabled
                style="width:100%;margin-top:0.9rem;padding:0.85rem;border:none;background:#16a34a;color:#fff;font-weight:700;letter-spacing:1px;text-transform:uppercase;font-size:0.78rem;cursor:pointer;opacity:0.5;">
          Confirm payment received
        </button>`
      : `<div style="margin-top:0.9rem;font-size:0.82rem;color:var(--text-muted);">
           Ask a cashier or manager to check the payment and confirm it.</div>`;

    el.innerHTML = `
      <div style="background:var(--panel-bg);color:var(--text-main);border:1px solid var(--border-color);width:100%;max-width:460px;max-height:96vh;overflow:auto;padding:1.25rem 1.25rem 1rem;text-align:center;">
        <div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:2px;color:var(--text-muted);">Scan &amp; Pay</div>
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin:0.4rem 0 0.8rem;gap:0.5rem;">
          <div style="text-align:left;"><div style="font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;">Order</div>
            <div style="font-family:monospace;font-size:0.95rem;">${esc(r.order_number)}</div></div>
          <div style="text-align:right;"><div style="font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;">Amount to pay</div>
            <div style="font-size:1.8rem;font-weight:800;line-height:1.1;">&#8377;${esc(r.amount)}</div></div>
        </div>
        ${qrBlock}
        <div style="margin-top:0.6rem;font-size:0.8rem;">
          ${q.payee_name ? `Pay to <b>${esc(q.payee_name)}</b>` : ""}
          ${q.upi_id ? `<div style="font-family:monospace;color:var(--text-muted);font-size:0.78rem;">UPI ID: ${esc(q.upi_id)}</div>` : ""}
        </div>
        <ol style="text-align:left;font-size:0.78rem;color:var(--text-muted);margin:0.7rem 0 0;padding-left:1.2rem;">${instructions}</ol>
        <div id="upiv-status" style="margin-top:0.8rem;padding:0.55rem;font-size:0.8rem;font-weight:600;background:rgba(234,179,8,0.12);color:#b45309;">
          Payment PENDING &mdash; not recorded until verified.</div>
        ${verifyBlock}
        <div style="display:flex;gap:0.5rem;margin-top:0.6rem;">
          <button id="upiv-cancel" style="flex:1;padding:0.6rem;background:transparent;border:1px solid var(--border-color);color:var(--text-muted);font-size:0.72rem;text-transform:uppercase;letter-spacing:1px;cursor:pointer;">Cancel QR request</button>
          <button id="upiv-close" style="flex:1;padding:0.6rem;background:transparent;border:1px solid var(--border-color);color:var(--text-main);font-size:0.72rem;text-transform:uppercase;letter-spacing:1px;cursor:pointer;">Close (keep pending)</button>
        </div>
      </div>`;
  }

  function collect({ orderId, amount }) {
    return new Promise(async (resolve) => {
      let data;
      try {
        data = await apiClient.post(`/upi/start/${orderId}/`, { amount });
      } catch (e) {
        resolve(null); // apiClient already showed the error
        return;
      }
      const el = buildOverlay();
      render(el, data, amount);
      const reqId = data.request.id;
      let poll = null;
      const done = (value) => {
        if (poll) clearInterval(poll);
        el.remove();
        document.removeEventListener("keydown", onKey);
        resolve(value);
      };
      const onKey = (ev) => { if (ev.key === "Escape") done(null); };
      document.addEventListener("keydown", onKey);

      const status = el.querySelector("#upiv-status");
      poll = setInterval(async () => {
        try {
          const res = await fetch(`/upi/request/${reqId}/`, { headers: { Accept: "application/json" } });
          const d = await res.json();
          if (d.request && d.request.customer_claimed_at) {
            status.innerHTML = `Guest says they paid at ${esc(d.request.customer_claimed_at)}. ` +
              `Check the PhonePe / bank app before confirming. Payment still PENDING.`;
          }
          if (d.request && d.request.status !== "pending") done(null);
        } catch (e) { /* keep polling */ }
      }, 5000);

      el.querySelector("#upiv-close").onclick = () => done(null);
      el.querySelector("#upiv-cancel").onclick = async () => {
        try { await apiClient.post(`/upi/request/${reqId}/cancel/`, {}); ui.toast("QR request cancelled", "info"); } catch (e) {}
        done(null);
      };

      const ref = el.querySelector("#upiv-ref");
      const ok = el.querySelector("#upiv-ok");
      const btn = el.querySelector("#upiv-confirm");
      if (ref && ok && btn) {
        const sync = () => {
          const valid = REF_RE.test(ref.value.replace(/[\s-]+/g, "")) && ok.checked;
          btn.disabled = !valid;
          btn.style.opacity = valid ? "1" : "0.5";
        };
        ref.addEventListener("input", sync);
        ok.addEventListener("change", sync);
        setTimeout(() => ref.focus(), 50);
        btn.onclick = () => {
          if (btn.disabled) return;
          done({
            upi_request_id: reqId,
            reference: ref.value.replace(/[\s-]+/g, "").toUpperCase(),
            confirm_received: true,
            amount: data.request.amount,
          });
        };
      }
    });
  }

  window.UpiVerify = { collect };
})();
