/*
 * "How to Use" help centre (templates/help/guide.html).
 *
 * The server renders only the sections the signed-in user's role and the
 * restaurant's switched-on features allow, so everything built here (contents,
 * search, Previous/Next, walkthroughs, Open Feature links) can only ever show
 * those sections. The owner's Guide Access matrix and role preview only hide
 * sections inside this page; they save nothing and grant no permission.
 */
(function () {
    "use strict";

    const root = document.getElementById("rsGuide");
    if (!root) return;

    const ROLE_LABELS = {
        owner: "Owner", manager: "Manager", cashier: "Cashier", captain: "Captain",
        waiter: "Waiter", chef: "Chef", kitchen: "Kitchen Staff",
    };
    const STAFF_ROLES = ["manager", "cashier", "captain", "waiter", "chef", "kitchen"];

    const main = root.querySelector(".rsg-main");
    const tocList = root.querySelector("[data-rsg-toc]");
    const crumbs = root.querySelector("[data-rsg-crumbs]");
    const searchInput = root.querySelector("[data-rsg-search]");
    const searchStatus = root.querySelector("[data-rsg-search-status]");
    const prevBtn = root.querySelector("[data-rsg-prev]");
    const nextBtn = root.querySelector("[data-rsg-next]");
    const allSections = Array.from(root.querySelectorAll(".rsg-section"));
    const byId = {};
    allSections.forEach(s => { byId[s.id.replace(/^g-/, "")] = s; });

    let current = null;
    let previewRole = "";          // "" = the signed-in user's own view
    let lastFocus = null;

    // ---- Guide Access (owner only, in-memory preview) -------------------------
    // allowed[sectionId][role] starts as "the role can use this feature" (the
    // data-roles list the server wrote). Unticking only hides the section in the
    // role preview below. Nothing is stored: see the Save Changes note on screen.
    const initial = {};
    const allowed = {};
    allSections.forEach(s => {
        const id = s.id.replace(/^g-/, "");
        const roles = (s.dataset.roles || "").split(",").filter(Boolean);
        initial[id] = {};
        STAFF_ROLES.forEach(r => { initial[id][r] = roles.includes(r); });
        allowed[id] = Object.assign({}, initial[id]);
    });

    function sectionVisible(s) {
        if (!previewRole) return true;
        const id = s.id.replace(/^g-/, "");
        if (previewRole === "owner") return true;
        return !!(allowed[id] && allowed[id][previewRole]);
    }

    function visibleSections() {
        return allSections.filter(sectionVisible);
    }

    // The owner's Guide Access page stays reachable during a role preview (so the
    // ticks can be changed or reset) without being listed as part of that role's guide.
    function canShow(s) {
        return visibleSections().includes(s) || s.id === "g-guide-access";
    }

    // ---- Contents list ----------------------------------------------------------
    function textOf(s) {
        if (!s._text) s._text = (s.dataset.title + " " + (s.dataset.keywords || "") + " " + s.textContent).toLowerCase();
        return s._text;
    }

    function markText(el, text, q) {
        el.textContent = "";
        if (!q) { el.textContent = text; return; }
        const i = text.toLowerCase().indexOf(q);
        if (i < 0) { el.textContent = text; return; }
        el.append(text.slice(0, i));
        const m = document.createElement("mark");
        m.textContent = text.slice(i, i + q.length);
        el.append(m, text.slice(i + q.length));
    }

    function buildToc() {
        const q = (searchInput.value || "").trim().toLowerCase();
        const words = q.split(/\s+/).filter(Boolean);
        tocList.textContent = "";
        let group = null, ol = null, n = 0, shown = 0;
        visibleSections().forEach(s => {
            n += 1;
            const hit = !words.length || words.every(w => textOf(s).includes(w));
            if (!hit) return;
            shown += 1;
            if (s.dataset.group !== group) {
                group = s.dataset.group;
                const h = document.createElement("h2");
                h.textContent = group;
                ol = document.createElement("ol");
                tocList.append(h, ol);
            }
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = "#" + s.id;
            a.dataset.goto = s.id.replace(/^g-/, "");
            const num = document.createElement("span");
            num.className = "rsg-num";
            num.textContent = n + ".";
            const label = document.createElement("span");
            markText(label, s.dataset.title, words[0] || "");
            a.append(num, label);
            if (current === s) a.setAttribute("aria-current", "true");
            li.append(a);
            ol.append(li);
        });
        if (!shown) {
            const p = document.createElement("p");
            p.className = "rsg-empty";
            p.textContent = "No help topic matches “" + searchInput.value.trim() + "”. Try a simpler word such as bill, menu, table or stock.";
            tocList.append(p);
        }
        if (searchStatus) {
            searchStatus.textContent = words.length ? shown + " topic" + (shown === 1 ? "" : "s") + " found" : "";
        }
        return shown;
    }

    // ---- Showing a section ------------------------------------------------------
    function show(id, opts) {
        opts = opts || {};
        let s = byId[id];
        const vis = visibleSections();
        if (!s || !canShow(s)) s = vis[0];
        if (!s) return;
        allSections.forEach(x => x.classList.toggle("is-current", x === s));
        current = s;

        // Breadcrumbs
        crumbs.textContent = "";
        const ol = document.createElement("ol");
        const home = document.createElement("li");
        const hb = document.createElement("button");
        hb.type = "button";
        hb.textContent = "How to Use";
        hb.addEventListener("click", () => show(vis[0].id.replace(/^g-/, ""), { focus: true }));
        home.append(hb);
        const g = document.createElement("li");
        g.textContent = s.dataset.group;
        const here = document.createElement("li");
        here.textContent = s.dataset.title;
        here.setAttribute("aria-current", "page");
        ol.append(home, g, here);
        crumbs.append(ol);

        // Previous / Next
        const i = vis.indexOf(s);
        setPager(prevBtn, vis[i - 1], "Previous");
        setPager(nextBtn, vis[i + 1], "Next");

        buildToc();
        main.scrollTop = 0;
        if (opts.focus) {
            const h = s.querySelector("h2");
            if (h) { h.setAttribute("tabindex", "-1"); h.focus({ preventScroll: true }); }
        }
        if (!opts.noUrl) setParam("guide", s.id.replace(/^g-/, ""));
        root.classList.remove("toc-open");
    }

    function setPager(btn, target, word) {
        if (!btn) return;
        if (!target) { btn.hidden = true; return; }
        btn.hidden = false;
        btn.dataset.goto = target.id.replace(/^g-/, "");
        btn.querySelector("span").textContent = word + ": " + target.dataset.title;
    }

    // ---- URL helpers (no reloads) -----------------------------------------------
    function setParam(name, value) {
        try {
            const u = new URL(window.location.href);
            if (value === null) u.searchParams.delete(name); else u.searchParams.set(name, value);
            window.history.replaceState(window.history.state, "", u);
        } catch (_) { /* old browser: the URL simply doesn't update */ }
    }

    // ---- Open / close -----------------------------------------------------------
    function open(id) {
        lastFocus = document.activeElement;
        root.hidden = false;
        document.body.classList.add("rsg-open");
        show(id, { focus: true });
    }

    function close() {
        root.hidden = true;
        document.body.classList.remove("rsg-open");
        setParam("guide", null);
        const fab = document.getElementById("rs-help-fab");
        (lastFocus && document.body.contains(lastFocus) ? lastFocus : fab || document.body).focus?.();
    }

    root.addEventListener("click", e => {
        const go = e.target.closest("[data-goto]");
        if (go && root.contains(go)) {
            e.preventDefault();
            show(go.dataset.goto, { focus: true });
            return;
        }
        if (e.target.closest("[data-rsg-close]")) { close(); return; }
        if (e.target.closest("[data-rsg-toc-toggle]")) { root.classList.toggle("toc-open"); return; }
        if (e.target.closest("[data-rsg-print]")) { window.print(); return; }
        const tb = e.target.closest("[data-tour-start]");
        if (tb) startTourFromGuide(tb.dataset.tourStart, tb);
    });

    root.addEventListener("keydown", e => {
        if (e.key === "Escape") {
            if (root.classList.contains("toc-open")) { root.classList.remove("toc-open"); return; }
            if (document.activeElement === searchInput && searchInput.value) { searchInput.value = ""; buildToc(); return; }
            close();
        }
        // Keep Tab inside the help window while it's open.
        if (e.key === "Tab") {
            const f = Array.from(root.querySelectorAll("a[href],button:not([disabled]),input:not([disabled]),select,summary,[tabindex='0']"))
                .filter(el => el.offsetParent !== null);
            if (!f.length) return;
            const first = f[0], last = f[f.length - 1];
            if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
            else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
        }
    });

    searchInput.addEventListener("input", () => {
        const shown = buildToc();
        if (shown && window.innerWidth < 992) root.classList.add("toc-open");
    });
    searchInput.addEventListener("keydown", e => {
        if (e.key === "Enter") {
            e.preventDefault();
            const a = tocList.querySelector("a[data-goto]");
            if (a) show(a.dataset.goto, { focus: true });
        }
    });

    // ---- Beginner checklist: real status from the existing /setup/checklist/ ----
    const checklist = root.querySelector("[data-rsg-checklist]");
    if (checklist) {
        fetch("/setup/checklist/", { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" })
            .then(r => (r.ok ? r.json() : null))
            .then(d => {
                if (!d || !d.steps) return;
                d.steps.forEach(step => {
                    const el = checklist.querySelector('[data-step="' + step.key + '"] .st');
                    if (!el) return;
                    el.textContent = step.done ? "✓ Done" : "Not done yet";
                    el.className = "st " + (step.done ? "done" : "todo");
                });
            })
            .catch(() => {});
    }

    // ---- Guide Access matrix (owner) --------------------------------------------
    const matrix = root.querySelector("[data-rsg-matrix]");
    const previewSelect = root.querySelector("[data-rsg-preview-role]");
    const dirtyLabel = root.querySelector("[data-rsg-dirty]");
    const resetBtn = root.querySelector("[data-rsg-reset]");

    function dirtyCount() {
        let n = 0;
        Object.keys(allowed).forEach(id => STAFF_ROLES.forEach(r => { if (allowed[id][r] !== initial[id][r]) n += 1; }));
        return n;
    }

    function refreshDirty() {
        const n = dirtyCount();
        if (dirtyLabel) dirtyLabel.textContent = n ? n + " unsaved change" + (n === 1 ? "" : "s") + " (preview only)" : "No unsaved changes";
        if (resetBtn) resetBtn.disabled = !n;
        if (matrix) {
            matrix.querySelectorAll("tr[data-sec]").forEach(tr => {
                const id = tr.dataset.sec;
                tr.classList.toggle("changed", STAFF_ROLES.some(r => allowed[id][r] !== initial[id][r]));
            });
        }
    }

    function buildMatrix() {
        if (!matrix) return;
        const tbody = matrix.querySelector("tbody");
        tbody.textContent = "";
        allSections.forEach(s => {
            const id = s.id.replace(/^g-/, "");
            if (s.dataset.adminOnly === "1") return;   // the matrix itself, owner-only pages
            const tr = document.createElement("tr");
            tr.dataset.sec = id;
            const th = document.createElement("td");
            th.textContent = s.dataset.title;
            tr.append(th);
            STAFF_ROLES.forEach(r => {
                const td = document.createElement("td");
                if (!initial[id][r]) {
                    const lock = document.createElement("span");
                    lock.className = "lock";
                    lock.innerHTML = '<i class="bi bi-lock" aria-hidden="true"></i>';
                    lock.title = ROLE_LABELS[r] + " has no access to this feature, so the guide cannot be shown to them.";
                    const sr = document.createElement("span");
                    sr.className = "visually-hidden";
                    sr.textContent = "Not available: " + ROLE_LABELS[r] + " cannot use this feature";
                    lock.append(sr);
                    td.append(lock);
                } else {
                    const cb = document.createElement("input");
                    cb.type = "checkbox";
                    cb.checked = allowed[id][r];
                    cb.setAttribute("aria-label", "Show “" + s.dataset.title + "” to " + ROLE_LABELS[r]);
                    cb.addEventListener("change", () => {
                        allowed[id][r] = cb.checked;
                        refreshDirty();
                        if (previewRole) buildToc();
                    });
                    td.append(cb);
                }
                tr.append(td);
            });
            tbody.append(tr);
        });
        refreshDirty();
    }

    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            Object.keys(initial).forEach(id => { allowed[id] = Object.assign({}, initial[id]); });
            buildMatrix();
            if (previewRole) buildToc();
        });
    }

    function setPreview(role) {
        previewRole = role;
        root.classList.toggle("is-previewing", !!role);
        const label = root.querySelector("[data-rsg-preview-label]");
        if (label) label.textContent = role ? ROLE_LABELS[role] : "";
        if (previewSelect) previewSelect.value = role;
        const vis = visibleSections();
        show(current && canShow(current) ? current.id.replace(/^g-/, "") : (vis[0] ? vis[0].id.replace(/^g-/, "") : ""), { noUrl: true });
    }

    if (previewSelect) previewSelect.addEventListener("change", () => setPreview(previewSelect.value));
    root.querySelectorAll("[data-rsg-preview-exit]").forEach(b => b.addEventListener("click", () => {
        setPreview("");
        show("guide-access", { focus: true });
    }));
    buildMatrix();

    // ---- Walkthroughs -----------------------------------------------------------
    // A walkthrough only points at things on the real screen. It never clicks,
    // submits, pays or deletes anything: Next/Back just move the highlight.
    function tourData(id) {
        const el = root.querySelector('script.rsg-tour[data-tour="' + id + '"]');
        if (!el) return null;
        try {
            return {
                id: id,
                title: el.dataset.title || "Walkthrough",
                path: el.dataset.path ? new RegExp(el.dataset.path) : null,
                start: el.dataset.start || "",
                need: el.dataset.need || "",
                steps: JSON.parse(el.textContent),
            };
        } catch (_) { return null; }
    }

    function startTourFromGuide(id, btn) {
        const t = tourData(id);
        if (!t) return;
        if (t.path && !t.path.test(window.location.pathname)) {
            if (!t.start) {
                // This walkthrough needs a page that has no fixed address (one bill).
                let note = btn && btn.parentElement.querySelector(".rsg-tour-need");
                if (btn && !note) {
                    note = document.createElement("p");
                    note.className = "rsg-tour-need text-muted small w-100 mb-0";
                    note.setAttribute("role", "status");
                    btn.parentElement.append(note);
                }
                if (note) note.textContent = t.need || "Open the screen this walkthrough is for, then start it from there.";
                return;
            }
            const u = new URL(t.start, window.location.origin);
            u.searchParams.set("guide_tour", id);
            window.location.href = u.toString();
            return;
        }
        close();
        runTour(t);
    }

    function findTarget(step) {
        if (!step.sel) return null;
        let els;
        try { els = Array.from(document.querySelectorAll(step.sel)); } catch (_) { return null; }
        els = els.filter(el => !root.contains(el) && el.getClientRects().length && getComputedStyle(el).visibility !== "hidden");
        if (step.has) els = els.filter(el => el.textContent.toLowerCase().includes(step.has.toLowerCase()));
        return els[0] || null;
    }

    function runTour(t) {
        let i = 0;
        const ring = document.createElement("div");
        ring.className = "rsg-tour-ring";
        const box = document.createElement("div");
        box.className = "rsg-tour-box";
        box.setAttribute("role", "dialog");
        box.setAttribute("aria-live", "polite");
        box.setAttribute("aria-label", t.title);
        document.body.append(ring, box);

        function end() {
            ring.remove(); box.remove();
            document.removeEventListener("keydown", onKey, true);
            window.removeEventListener("resize", place);
            setParam("guide_tour", null);
        }

        function place() {
            const step = t.steps[i];
            const el = findTarget(step);
            if (el) {
                const r = el.getBoundingClientRect();
                ring.classList.remove("no-target");
                Object.assign(ring.style, { top: (r.top - 6) + "px", left: (r.left - 6) + "px", width: (r.width + 12) + "px", height: (r.height + 12) + "px" });
                const below = r.bottom + 12 + box.offsetHeight < window.innerHeight;
                let top = below ? r.bottom + 12 : Math.max(16, r.top - box.offsetHeight - 12);
                if (top + box.offsetHeight > window.innerHeight - 16) top = Math.max(16, window.innerHeight - box.offsetHeight - 16);
                let left = Math.min(Math.max(16, r.left), window.innerWidth - box.offsetWidth - 16);
                Object.assign(box.style, { top: top + "px", left: left + "px" });
            } else {
                ring.classList.add("no-target");
                Object.assign(box.style, { top: Math.max(16, (window.innerHeight - box.offsetHeight) / 2) + "px", left: Math.max(16, (window.innerWidth - box.offsetWidth) / 2) + "px" });
            }
        }

        function render() {
            const step = t.steps[i];
            const el = findTarget(step);
            if (el) el.scrollIntoView({ block: "center", behavior: "auto" });
            box.innerHTML = "";
            const cnt = document.createElement("div");
            cnt.className = "cnt";
            cnt.textContent = t.title + " · step " + (i + 1) + " of " + t.steps.length;
            const h = document.createElement("h2");
            h.textContent = step.title;
            const p = document.createElement("p");
            p.style.margin = "0";
            p.textContent = step.text;
            box.append(cnt, h, p);
            if (step.sel && !el) {
                const m = document.createElement("div");
                m.className = "miss";
                m.textContent = step.missing || "This part is not on the screen right now (it may appear after an earlier step, or on a wider screen).";
                box.append(m);
            }
            const btns = document.createElement("div");
            btns.className = "btns";
            const mk = (label, fn, cls, dis) => {
                const b = document.createElement("button");
                b.type = "button"; b.className = "rsg-btn " + (cls || ""); b.textContent = label;
                b.disabled = !!dis; b.addEventListener("click", fn); btns.append(b); return b;
            };
            mk("Back", () => { i -= 1; render(); }, "", i === 0);
            const last = i === t.steps.length - 1;
            const nb = mk(last ? "Finish" : "Next", () => { if (last) end(); else { i += 1; render(); } }, "rsg-btn-gold");
            mk("Restart", () => { i = 0; render(); });
            mk("Skip", end);
            box.append(btns);
            place();
            nb.focus();
        }

        function onKey(e) {
            if (e.key === "Escape") { e.preventDefault(); end(); }
        }
        document.addEventListener("keydown", onKey, true);
        window.addEventListener("resize", place);
        render();
    }

    // ---- Start-up ---------------------------------------------------------------
    const params = new URLSearchParams(window.location.search);
    const tourParam = params.get("guide_tour");
    if (root.dataset.autoOpen === "1") {
        const want = params.get("guide");
        open(want && want !== "1" ? want : (window.location.hash || "").replace(/^#g-/, ""));
    } else if (tourParam) {
        const t = tourData(tourParam);
        if (t && (!t.path || t.path.test(window.location.pathname))) {
            // Let the page finish drawing its own content (menus, tables) first.
            setTimeout(() => runTour(t), 600);
        } else {
            setParam("guide_tour", null);
        }
    }

    window.RasovaGuide = { open: open, close: close };
})();
