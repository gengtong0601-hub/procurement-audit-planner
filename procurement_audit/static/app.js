"use strict";
let current = null;
let currentView = "overview";
const $ = (id) => document.getElementById(id);
const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const money = (value) =>
  new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: current.manifest.currency,
    maximumFractionDigits: 0,
  }).format(Number(value));
const labels = {
  overview: [
    "Follow the evidence.",
    "Source documents, verified rules and the full payment population.",
  ],
  risks: [
    "Bring your judgment.",
    "Approve, amend or reject each risk before the team builds the plan.",
  ],
  pack: [
    "A focused fieldwork plan.",
    "Three connected documents, independently checked and ready for review.",
  ],
  team: [
    "Make the reasoning visible.",
    "Specialized roles, explicit handoffs and four independent checks.",
  ],
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json();
  if (!response.ok)
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail),
    );
  return body;
}
async function action(fn) {
  $("alert").hidden = true;
  document
    .querySelectorAll("button")
    .forEach((button) => (button.disabled = true));
  try {
    await fn();
  } catch (error) {
    $("alert").textContent = error.message;
    $("alert").hidden = false;
    $("alert").scrollIntoView({ behavior: "smooth", block: "center" });
  } finally {
    document
      .querySelectorAll("button")
      .forEach((button) => (button.disabled = false));
  }
}
async function listCases() {
  const result = await api("/api/cases");
  $("case-select").innerHTML =
    '<option value="">Select a case</option>' +
    result.cases
      .map(
        (id) => `<option value="${escapeHTML(id)}">${escapeHTML(id)}</option>`,
      )
      .join("");
  if (current) $("case-select").value = current.case_id;
}
function switchView(view) {
  currentView = view;
  document
    .querySelectorAll(".view")
    .forEach((section) => (section.hidden = section.id !== view));
  document
    .querySelectorAll("[data-view]")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.view === view),
    );
  if (current) {
    $("page-title").textContent = labels[view][0];
    $("page-description").textContent = labels[view][1];
  }
}
function showCase(data) {
  current = data;
  $("empty-state").hidden = true;
  $("workspace").hidden = false;
  $("case-banner").hidden = false;
  $("case-banner").textContent =
    `${data.manifest.synthetic ? "SYNTHETIC DEMONSTRATION · " : ""}${data.manifest.council} · ${data.manifest.period_start} to ${data.manifest.period_end} · ${data.stage.replaceAll("_", " ")}`;
  if (data.stale) {
    $("alert").textContent = data.error;
    $("alert").hidden = false;
  }
  const a = data.analytics;
  $("stats").innerHTML = a
    ? [
        ["Net spend", money(a.net_spend), "Credits retained in population"],
        ["Payments analysed", a.row_count, "Every supplied payment row"],
        [
          "Risk indicators",
          data.register.risks.length,
          "Awaiting or reflecting human judgment",
        ],
        [
          "Verified rules",
          data.rules.rules.length,
          "With literal PDF quotations",
        ],
      ]
        .map(
          ([title, value, subtitle]) =>
            `<div class="stat"><span>${escapeHTML(title)}</span><strong>${escapeHTML(value)}</strong><small>${escapeHTML(subtitle)}</small></div>`,
        )
        .join("")
    : "";
  renderOverview();
  renderRisks();
  renderPack();
  renderTeam();
  switchView(currentView);
}
function renderOverview() {
  const m = current.manifest;
  const sources = [
    ["PDF", m.contract_rules, "Contract Procedure Rules"],
    ...m.spend.map((s) => ["XLSX", s.file, `Sheet: ${s.sheet}`]),
    ["CSV", m.contracts, "Contracts register"],
    ...m.committee_papers.map((f) => ["PDF", f, "Historical audit evidence"]),
  ];
  $("overview").innerHTML =
    `<div class="grid-two"><article class="card"><div class="section-title"><div><h2>The source set</h2><p>Each artifact retains its original evidence references.</p></div><span class="pill">${sources.length} sources</span></div>${sources.map(([type, file, note]) => `<div class="source"><span class="file-icon">${type}</span><div><strong>${escapeHTML(file)}</strong><small>${escapeHTML(note)}</small></div></div>`).join("")}<p class="small">${m.synthetic ? "Demonstration mode uses reviewed extraction candidates and deterministic role agents. No LLM call was made." : "Source hashes protect against using analysis after its inputs change."}</p></article><article class="card"><div class="section-title"><div><h2>Rules with receipts</h2><p>Quotes checked against the cited PDF page.</p></div></div>${(current.rules?.rules || []).map((r) => `<div class="rule"><span class="pill">${r.rule_id} · Clause ${escapeHTML(r.clause)}</span><h3>${escapeHTML(r.requirement)}</h3><blockquote>${escapeHTML(r.quote)}</blockquote><p>${escapeHTML(r.source_file)} · Page ${r.page} · ${escapeHTML(r.indicator.replaceAll("_", " "))}</p></div>`).join("")}</article></div><details class="card"><summary>Inspect generated artifacts</summary><div class="artifact-links">${fileButtons()}</div></details>`;
}
function fileButtons() {
  return current.files
    .map(
      (file) =>
        `<button data-file="${escapeHTML(file)}">${escapeHTML(file)}</button>`,
    )
    .join("");
}
function renderRisks() {
  if (!current.register) {
    $("risks").innerHTML =
      '<p class="notice">Run the analysis stage from the CLI to produce the risk register.</p>';
    return;
  }
  const saved = new Map(current.decisions.decisions.map((d) => [d.risk_id, d]));
  $("risks").innerHTML =
    `<div class="section-title"><div><h2>The auditor's decision</h2><p>Amendments and rejections need an explanation. Ratings use a fixed 1–5 scale.</p></div><span class="pill amber">HUMAN GATE 01</span></div><form id="risk-decisions">${
      current.register.risks
        .map((r) => {
          const d = saved.get(r.risk_id);
          const indicator = current.analytics.indicators.find((i) =>
            r.indicator_ids.includes(i.indicator_id),
          );
          return `<article class="card risk-card" data-risk="${r.risk_id}"><div class="risk-head"><div><span class="small-label">${r.risk_id} · ${r.rule_ids.join(", ") || "Historical evidence"}</span><h3>${escapeHTML(r.title)}</h3></div><span class="pill ${r.score >= 15 ? "red" : "amber"}">${r.likelihood} × ${r.impact} = ${r.score}</span></div><p>${escapeHTML(r.narrative)}</p><div class="risk-evidence">${escapeHTML(r.rating_rationale)}${indicator ? `<br>Source payments: ${indicator.transaction_ids.map(escapeHTML).join(", ")}` : ""}${r.history_ids.length ? `<br>History: ${r.history_ids.join(", ")}` : ""}</div><div class="risk-form"><label>Decision<select name="decision">${["pending", "approve", "amend", "reject"].map((v) => `<option value="${v}" ${d?.decision === v ? "selected" : ""}>${v[0].toUpperCase() + v.slice(1)}</option>`).join("")}</select></label><label>Likelihood<input name="likelihood" type="number" min="1" max="5" value="${d?.likelihood || r.likelihood}" aria-label="Revised likelihood for ${r.risk_id}"></label><label>Impact<input name="impact" type="number" min="1" max="5" value="${d?.impact || r.impact}" aria-label="Revised impact for ${r.risk_id}"></label><label>Auditor comment<input name="comment" maxlength="3000" placeholder="Explain your decision…" value="${escapeHTML(d?.comment || "")}"></label></div></article>`;
        })
        .join("") ||
      '<p class="notice">No configured indicators triggered. Review the source limitations and confirm the empty scope explicitly.</p>'
    }<div class="review-actions"><label class="field-label">Auditor name<input name="reviewer" required minlength="2" maxlength="100" placeholder="Your name" value="${escapeHTML(current.decisions.reviewer === "PENDING" ? "" : current.decisions.reviewer)}"></label><button class="primary" type="submit">Save decisions & build the pack →</button></div></form>`;
  $("risk-decisions").addEventListener("submit", (event) => {
    event.preventDefault();
    action(async () => {
      const form = event.currentTarget;
      const decisions = [...form.querySelectorAll("[data-risk]")].map(
        (card) => {
          const type = card.querySelector('[name="decision"]').value;
          return {
            risk_id: card.dataset.risk,
            decision: type,
            comment: card.querySelector('[name="comment"]').value,
            likelihood:
              type === "amend"
                ? Number(card.querySelector('[name="likelihood"]').value)
                : null,
            impact:
              type === "amend"
                ? Number(card.querySelector('[name="impact"]').value)
                : null,
          };
        },
      );
      if (decisions.some((d) => d.decision === "pending"))
        throw new Error(
          "Please approve, amend or reject every risk before building the pack.",
        );
      await api(`/api/cases/${current.case_id}/decisions`, {
        method: "POST",
        body: JSON.stringify({
          reviewer: form.querySelector('[name="reviewer"]').value,
          decisions,
        }),
      });
      const id = current.case_id;
      const data = await api(`/api/cases/${id}/plan`, { method: "POST" });
      showCase({ case_id: id, ...data });
      switchView("pack");
    });
  });
  $("risks")
    .querySelectorAll('[name="decision"]')
    .forEach((select) => {
      const update = () => {
        const card = select.closest("[data-risk]");
        card
          .querySelectorAll('input[type="number"]')
          .forEach((input) => (input.disabled = select.value !== "amend"));
      };
      select.addEventListener("change", update);
      update();
    });
}
function renderPack() {
  if (!current.program) {
    $("pack").innerHTML =
      '<div class="notice"><h2>The planning team is waiting for you.</h2><p>Complete the risk decisions to unlock the planning memo, risk-control matrix and audit program.</p><button data-view="risks">Review the risks →</button></div>';
    return;
  }
  const documents = [
    [
      "planning-memo.md",
      "Planning memo",
      "Purpose, scope decisions, approach, rule coverage and limitations.",
    ],
    [
      "risk-control-matrix.md",
      "Risk-control matrix",
      "Each approved risk, the required control and the corresponding test.",
    ],
    [
      "audit-program.md",
      "Audit program",
      "Fieldwork steps, evidence requests and exact workbook sample rows.",
    ],
  ];
  $("pack").innerHTML =
    `<div class="section-title"><div><h2>Your planning pack</h2><p>${current.program.tests.length} tests · ${current.program.auditor_days} available auditor-days · Four QA checks passed</p></div><a href="/api/cases/${current.case_id}/download">Download artifacts (.zip) ↗</a></div><div class="document-cards">${documents.map(([file, title, note]) => `<article class="card document-card"><span class="file-icon">MD</span><h3>${title}</h3><p>${note}</p><button data-file="${file}">Read document ↗</button></article>`).join("")}</div><div class="checks">${current.checks.map((check) => `<div class="check"><strong>${check.passed ? "✓ PASS" : "FAIL"} · ${escapeHTML(check.name)}</strong>${escapeHTML(check.details)}</div>`).join("")}</div><div class="card table-wrap"><h2>Fieldwork schedule</h2><table><thead><tr><th>Test</th><th>Risk</th><th>Auditor-days</th><th>Payments selected</th></tr></thead><tbody>${current.program.tests.map((t) => `<tr><td>${t.test_id}</td><td>${t.risk_id}</td><td>${t.day_start}–${t.day_end}</td><td>${t.sample_ids.length ? t.sample_ids.map(escapeHTML).join(", ") : "Documentary review"}</td></tr>`).join("")}</tbody></table></div><section class="card signoff-card"><div class="section-title"><div><h2>Auditor sign-off</h2><p>Read the pack and challenge log before recording your decision.</p></div><span class="pill amber">HUMAN GATE 02</span></div>${current.signoff ? `<p class="notice">${escapeHTML(current.signoff.decision.replaceAll("_", " "))} · ${escapeHTML(current.signoff.reviewer)}<br>${escapeHTML(current.signoff.comment)}</p>` : ""}<form id="signoff-form"><label class="field-label">Auditor name<input name="reviewer" required minlength="2" maxlength="100" placeholder="Your name"></label><label class="field-label">Decision<select name="decision"><option value="">Choose a decision</option><option value="sign_off">Sign off the planning pack</option><option value="return_for_revision">Return for revision</option></select></label><label class="field-label full-width">Review comment<textarea name="comment" required minlength="5" maxlength="3000" placeholder="Record your review and any limitations…"></textarea></label><div class="full-width"><button class="primary" type="submit">Record my review</button> <button type="button" data-file="challenge.md">Read challenger comments</button></div></form></section>`;
  $("signoff-form").addEventListener("submit", (event) => {
    event.preventDefault();
    action(async () => {
      const data = Object.fromEntries(new FormData(event.currentTarget));
      if (!data.decision)
        throw new Error(
          "Choose whether to sign off or return the pack for revision.",
        );
      const id = current.case_id;
      const result = await api(`/api/cases/${id}/sign-off`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      showCase({ case_id: id, ...result });
      switchView("pack");
    });
  });
}
function renderTeam() {
  $("team").innerHTML =
    `<div class="section-title"><div><h2>One workflow. Specialized roles.</h2><p>Python role workers use explicit messages. Demo mode uses deterministic logic and reviewed candidates.</p></div><span class="pill">SKILLS + AGENTS</span></div><div class="card"><div class="timeline-message"><div><strong>extract-rules</strong><small>Reusable skill</small></div><p>Reads proposed rules and verifies each verbatim quote against the declared PDF page.</p></div><div class="timeline-message"><div><strong>spend-analyst</strong><small>Analysis sub-agent</small></div><p>Computes every indicator in Python over the full population; retains original workbook rows.</p></div><div class="timeline-message"><div><strong>findings-analyst</strong><small>Analysis sub-agent</small></div><p>Extracts or validates past opinions, coverage, open actions and registered risks.</p></div><div class="timeline-message"><div><strong>risk-assessor</strong><small>Analysis sub-agent</small></div><p>Combines evidence into a fixed-scale register and stops at the first human gate.</p></div>${(current.messages || []).map((message) => `<div class="timeline-message"><div><strong>${escapeHTML(message.sender)}</strong><small>→ ${escapeHTML(message.recipient)}</small></div><p>${escapeHTML(message.message)}</p></div>`).join("") || '<p class="small">Planner, challenger and QA messages appear after the auditor approves the scope.</p>'}</div><details class="card"><summary>All case artifacts</summary><div class="artifact-links">${fileButtons()}</div></details>`;
}
document.addEventListener("click", (event) => {
  const navigation = event.target.closest("[data-view]");
  if (navigation) switchView(navigation.dataset.view);
  const file = event.target.closest("[data-file]");
  if (file)
    action(async () => {
      const response = await fetch(
        `/api/cases/${current.case_id}/files/${file.dataset.file}`,
      );
      if (!response.ok) throw new Error("Could not load this artifact.");
      $("document-title").textContent = file.dataset.file;
      $("document-content").textContent = await response.text();
      $("document-dialog").showModal();
    });
});
$("close-dialog").addEventListener("click", () => $("document-dialog").close());
const createDemo = () =>
  action(async () => {
    showCase(await api("/api/cases/demo", { method: "POST" }));
    await listCases();
    switchView("overview");
  });
$("demo-button").addEventListener("click", createDemo);
$("welcome-demo").addEventListener("click", createDemo);
$("case-select").addEventListener("change", (event) => {
  if (event.target.value)
    action(async () => showCase(await api(`/api/cases/${event.target.value}`)));
});
action(listCases);
