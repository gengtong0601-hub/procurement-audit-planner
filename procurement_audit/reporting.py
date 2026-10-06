"""Render the exact planning artifacts specified in the assignment guide."""

from html import escape


def safe(value):
    return escape(str(value), quote=False).replace("|", "\\|").replace("\n", " ")


def register_markdown(register, analytics, history, rules):
    lines = [
        "# Procurement risk register",
        "",
        "Planning indicators only; no audit findings.",
        "",
        register.method,
        "",
    ]
    for risk in register.risks:
        lines.extend(
            [
                f"## {risk.risk_id} — {safe(risk.title)}",
                "",
                f"Likelihood **{risk.likelihood}** × impact **{risk.impact}** = **{risk.score}**.",
                "",
                safe(risk.narrative),
                "",
                "Rating basis: " + safe(risk.rating_rationale),
                "",
                "Rules: " + (", ".join(risk.rule_ids) or "None; historical evidence only"),
                "Indicators: " + (", ".join(risk.indicator_ids) or "None"),
                "History: " + (", ".join(risk.history_ids) or "None"),
                "",
            ]
        )
    if not register.risks:
        lines.extend(
            ["No configured indicators triggered. This is not assurance of compliance.", ""]
        )
    lines += ["## Verified rule citations", ""]
    for rule in rules.rules:
        lines.extend(
            [
                f"- {rule.rule_id}, clause {safe(rule.clause)}: {safe(rule.source_file)}, page {rule.page}. “{safe(rule.quote)}”"
            ]
        )
    lines += ["", "## Verified historical evidence", ""]
    for item in history.items:
        lines.append(
            f"- {item.item_id} ({item.category}): {safe(item.description)} — {safe(item.source_file)}, page {item.page}. “{safe(item.quote)}”"
        )
    lines += [
        "",
        "## Population",
        "",
        f"Rows: {analytics.row_count}. Net spend: {analytics.net_spend}. Gross spend: {analytics.gross_spend}.",
    ]
    return "\n".join(lines) + "\n"


def pack_markdown(manifest, rules, analytics, history, register, decisions, program, challenges):
    rules_by_id = {r.rule_id: r for r in rules.rules}
    risk_by_id = {r.risk_id: r for r in register.risks}
    label = (
        "SYNTHETIC DEMONSTRATION — NOT COUNCIL DATA"
        if manifest.synthetic
        else "DRAFT — AWAITING AUDITOR SIGN-OFF"
    )
    memo = [
        "# Procurement audit planning memo",
        "",
        label,
        "",
        f"**Council:** {safe(manifest.council)}. **Period:** {manifest.period_start} to {manifest.period_end}.",
        "",
        "**Purpose:** plan fieldwork over compliance with Contract Procedure Rules and follow-up of historical issues.",
        "",
        f"**Population:** all {analytics.row_count} supplied rows; net {manifest.currency} {analytics.net_spend:,.2f}; "
        f"gross {manifest.currency} {analytics.gross_spend:,.2f}; {analytics.supplier_count} suppliers. "
        "Amounts, counts and indicators were computed by `procurement_audit/analytics.py`.",
        "",
        f"**Approach:** full-population screening, human risk decisions, targeted judgmental samples, "
        f"a challenger review and four Python QA checks. Budget: {program.auditor_days} auditor-days.",
        "",
        f"## Auditor scope decisions — {safe(decisions.reviewer)}",
        "",
    ]
    for decision in decisions.decisions:
        risk = risk_by_id[decision.risk_id]
        rating = (
            f"{decision.likelihood} × {decision.impact}"
            if decision.decision == "amend"
            else f"{risk.likelihood} × {risk.impact}"
        )
        memo.append(
            f"- {decision.risk_id}: **{decision.decision}**, rating {rating}. {safe(decision.comment)}"
        )
    if not program.tests:
        memo += [
            "",
            "No fieldwork is scheduled because no risks were approved. Unused days do not establish assurance.",
        ]
    memo += ["", "## Rule coverage", ""]
    for rule in rules.rules:
        covering = [t.test_id for t in program.tests if rule.rule_id in t.rule_ids]
        memo.append(
            f"- {rule.rule_id}, clause {safe(rule.clause)}: "
            + (
                "covered by " + ", ".join(covering)
                if covering
                else "excluded — " + safe(program.excluded_rules[rule.rule_id])
            )
        )
    memo += [
        "",
        "## Limitations",
        "",
        "Indicators are not findings or proof of misconduct. Public contracts may be incomplete. "
        "Supplier matching is exact after trimming whitespace. Payment dates may differ from commitment dates. "
        "Amounts can overlap across indicators; do not sum them as losses. Credits remain in the population. "
        "Threshold-band width, 30-day windows and the rating rubric are disclosed planning assumptions. "
        "Judgmental samples do not support statistical extrapolation. Source quotations are verified, "
        "but extraction completeness and interpretation still require human review. No documents were inspected for fieldwork.",
        "",
        "## Historical coverage",
        "",
        *["- " + safe(note) for note in history.coverage_notes],
        "",
        "## Challenger considerations",
        "",
        *["- " + safe(note) for note in challenges],
        "",
    ]
    matrix = [
        "# Risk-control matrix",
        "",
        label,
        "",
        "| Risk | Rule / clause | Required control | Test |",
        "|---|---|---|---|",
    ]
    for test in program.tests:
        refs = (
            "; ".join(f"{rid} / {rules_by_id[rid].clause}" for rid in test.rule_ids)
            or "Historical action"
        )
        matrix.append(f"| {test.risk_id} | {safe(refs)} | {safe(test.control)} | {test.test_id} |")
    audit = [
        "# Audit program",
        "",
        label,
        "",
        "This pack plans the audit. It does not perform it or reach findings.",
        "",
    ]
    for test in program.tests:
        audit += [
            f"## {test.test_id} — {test.risk_id}",
            "",
            f"**Objective:** {safe(test.objective)}",
            "",
            f"**Control:** {safe(test.control)}",
            "",
            f"**Test step:** {safe(test.procedure)}",
            "",
            f"**Evidence:** {safe('; '.join(test.evidence))}",
            "",
            f"**Schedule:** auditor-days {test.day_start}–{test.day_end} ({test.days} days).",
            "",
            f"**Sample recipe:** {safe(test.sample_recipe)}",
            "",
            "| Payment ID | Original source row |",
            "|---|---|",
        ]
        for tid, location in zip(test.sample_ids, test.sample_locations, strict=True):
            audit.append(f"| {safe(tid)} | {safe(location)} |")
        if not test.sample_ids:
            audit.append("| No payment sample | Documentary control/action review |")
        audit.append("")
        for rid in test.rule_ids:
            rule = rules_by_id[rid]
            audit.extend(
                [
                    f"**{rid}, clause {safe(rule.clause)}** — {safe(rule.source_file)}, page {rule.page}:",
                    "",
                    f"> {safe(rule.quote)}",
                    "",
                ]
            )
    audit += [
        "## Documents to request from the council",
        "",
        *["- " + safe(item) for item in program.document_requests],
        "",
    ]
    return {
        "planning-memo.md": "\n".join(memo),
        "risk-control-matrix.md": "\n".join(matrix) + "\n",
        "audit-program.md": "\n".join(audit),
    }
