"""Four independently callable QA checks required before auditor sign-off."""

from procurement_audit.analytics import analyse
from procurement_audit.decisions import validate_gate
from procurement_audit.models import Check
from procurement_audit.sources import verify_citations, verify_rule_thresholds
from procurement_audit.storage import WorkflowError, load_manifest


def check_quotes(case, rules, history):
    manifest = load_manifest(case)
    verify_citations(case, rules.rules, {manifest.contract_rules})
    verify_citations(case, history.items, set(manifest.committee_papers))
    verify_rule_thresholds(rules)
    return "Every rule and history quote exists on its cited PDF page (whitespace normalized only)."


def check_numbers(case, rules, analytics, register):
    recomputed = analyse(case, rules)
    if recomputed != analytics:
        raise WorkflowError("Recomputed full-population analytics differ from the saved artifact.")
    for risk in register.risks:
        if risk.score != risk.likelihood * risk.impact:
            raise WorkflowError(f"Invalid likelihood × impact score: {risk.risk_id}")
    return "Full-population analytics, source hashes and risk-score arithmetic reconcile."


def check_traceability(rules, analytics, history, register, decisions, program):
    validate_gate(register, decisions)
    rule_ids = {r.rule_id for r in rules.rules}
    history_ids = {h.item_id for h in history.items}
    indicator_ids = {i.indicator_id for i in analytics.indicators}
    risks = {r.risk_id: r for r in register.risks}
    approved = {d.risk_id for d in decisions.decisions if d.decision in {"approve", "amend"}}
    planned = [t.risk_id for t in program.tests]
    if set(planned) != approved or len(planned) != len(approved):
        raise WorkflowError(
            "The program must cover every approved risk exactly once and no rejected risks."
        )
    for risk in register.risks:
        if not (
            set(risk.rule_ids) <= rule_ids
            and set(risk.history_ids) <= history_ids
            and set(risk.indicator_ids) <= indicator_ids
        ):
            raise WorkflowError(f"Broken evidence reference: {risk.risk_id}")
        if not (risk.rule_ids or risk.history_ids or risk.indicator_ids):
            raise WorkflowError(f"Risk has no evidence: {risk.risk_id}")
    covered = set()
    for test in program.tests:
        if set(test.rule_ids) != set(risks[test.risk_id].rule_ids):
            raise WorkflowError(f"Test does not trace to its risk's rules: {test.test_id}")
        if not all([test.control, test.procedure, test.evidence, test.sample_recipe]):
            raise WorkflowError(f"Incomplete fieldwork instructions: {test.test_id}")
        covered.update(test.rule_ids)
    if covered & set(program.excluded_rules) or covered | set(program.excluded_rules) != rule_ids:
        raise WorkflowError("Every rule must be covered or explicitly excluded with rationale.")
    if any(not reason.strip() for reason in program.excluded_rules.values()):
        raise WorkflowError("Excluded rules need explanations.")
    if program.tests:
        if sum(t.days for t in program.tests) != program.auditor_days:
            raise WorkflowError("Auditor-day allocation does not reconcile.")
        next_day = 1
        for test in program.tests:
            if test.day_start != next_day or test.day_end != test.day_start + test.days - 1:
                raise WorkflowError("The work schedule has a gap or overlap.")
            next_day = test.day_end + 1
    return "Approved risks trace to controls/tests; all rules have coverage or an exclusion rationale; budget reconciles."


def check_samples(case, rules, analytics, register, program):
    rows = {t.transaction_id: t for t in analyse(case, rules).transactions}
    indicators = {i.indicator_id: i for i in analytics.indicators}
    risks = {r.risk_id: r for r in register.risks}
    for test in program.tests:
        risk = risks[test.risk_id]
        population = {tid for iid in risk.indicator_ids for tid in indicators[iid].transaction_ids}
        expected = sorted(population, key=lambda tid: (-abs(rows[tid].amount), tid))[:10]
        if test.sample_ids != expected:
            raise WorkflowError(f"Sample does not follow its documented recipe: {test.test_id}")
        locations = [
            f"{rows[tid].source_file} / {rows[tid].source_sheet} / row {rows[tid].source_row}"
            for tid in expected
        ]
        if test.sample_locations != locations:
            raise WorkflowError(f"Incorrect workbook row reference: {test.test_id}")
    return "Every sample follows the stated recipe and exists at its cited original workbook row."


def check_all(case, rules, analytics, history, register, decisions, program):
    checks = []
    functions = [
        ("quotes", lambda: check_quotes(case, rules, history)),
        ("numbers", lambda: check_numbers(case, rules, analytics, register)),
        (
            "traceability",
            lambda: check_traceability(rules, analytics, history, register, decisions, program),
        ),
        ("samples", lambda: check_samples(case, rules, analytics, register, program)),
    ]
    for name, function in functions:
        try:
            details = function()
            checks.append(Check(name=name, passed=True, details=details))
        except (WorkflowError, ValueError, KeyError) as exc:
            checks.append(Check(name=name, passed=False, details=str(exc)))
    return checks
