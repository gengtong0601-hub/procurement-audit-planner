"""A local agent team with explicit messages and one controlled revision cycle."""

from concurrent.futures import ThreadPoolExecutor

from procurement_audit.llm import agent_text
from procurement_audit.models import AgentMessage, Challenges, PlanningAdvice, Program, TestStep
from procurement_audit.storage import WorkflowError

PROCEDURES = {
    "threshold_clustering": (
        "Compare requisition and commitment dates, aggregate related requirements, and inspect tender "
        "records and approved exceptions. Establish whether values reflect the full requirement.",
        ["Requisitions", "Tender evaluation", "Approved exemptions", "Purchase orders"],
    ),
    "split_purchases": (
        "Retrieve the complete related-payment group around the selected rows. Compare purpose, "
        "dates, approval routes and aggregated commitments to establish whether separate orders were justified.",
        ["Related purchase orders", "Requisitions", "Delegated approvals", "Supplier invoices"],
    ),
    "off_contract": (
        "Reconcile each selected payment to the full internal contract register; inspect supplier, scope, "
        "start/end dates, extensions and exemptions before treating a public-data mismatch as an exception.",
        ["Internal contract register", "Signed contracts", "Extensions", "Approved exemptions"],
    ),
    "duplicates": (
        "Retrieve every member of each selected duplicate group, invoices, ledger entries and credits. "
        "Distinguish a duplicate payment from corrections, installments and data publication artifacts.",
        ["Original invoices", "Accounts payable ledger", "Bank payment references", "Credit notes"],
    ),
    "manual_review": (
        "Walk through the cited control with its owner, inspect a documented example and corroborate "
        "implementation against the rule or outstanding audit action.",
        [
            "Control procedure",
            "Control-owner explanation",
            "Implementation evidence",
            "Action tracker",
        ],
    ),
}


class Challenger:
    name = "challenger"

    def run(self, register, analytics, history, decisions, *, model=None):
        approved = {d.risk_id for d in decisions.decisions if d.decision in {"approve", "amend"}}
        notes = [
            "Include alternative explanations: an unmatched public contract is not proof of off-contract spend.",
            "For split and duplicate indicators, request complete related groups, not just selected payments.",
            "Keep historical opinions separate from current conclusions and explicitly state data limitations.",
        ]
        if any(r.history_ids for r in register.risks if r.risk_id in approved):
            notes.append(
                "Request the current action tracker and independently confirm closure evidence."
            )
        if model:
            result = model.extract(
                agent_text(self.name),
                [
                    {
                        "risks": register.model_dump(mode="json"),
                        "indicators": [i.model_dump(mode="json") for i in analytics.indicators],
                        "history": history.model_dump(mode="json"),
                        "decisions": decisions.model_dump(mode="json"),
                    }
                ],
                Challenges,
            )
            notes.extend(result.notes)
        return notes


class Planner:
    name = "planner"

    def run(self, manifest, rules, analytics, register, decisions):
        approved = {d.risk_id: d for d in decisions.decisions if d.decision in {"approve", "amend"}}
        ranked = sorted(
            [r for r in register.risks if r.risk_id in approved],
            key=lambda r: (-self.score(r, approved[r.risk_id]), r.risk_id),
        )
        if len(ranked) > manifest.auditor_days:
            raise WorkflowError(
                "The day budget cannot cover all approved risks. Increase auditor_days in the manifest "
                "and rerun analysis, or ask the auditor to revise scope; no approved risk is silently omitted."
            )
        rows = {t.transaction_id: t for t in analytics.transactions}
        rules_by_id = {r.rule_id: r for r in rules.rules}
        indicators = {i.indicator_id: i for i in analytics.indicators}
        tests = []
        next_day = 1
        for index, risk in enumerate(ranked):
            days = manifest.auditor_days // len(ranked) + (
                index < manifest.auditor_days % len(ranked)
            )
            population = {
                tid for iid in risk.indicator_ids for tid in indicators[iid].transaction_ids
            }
            sample = sorted(population, key=lambda tid: (-abs(rows[tid].amount), tid))[:10]
            kind = rules_by_id[risk.rule_ids[0]].indicator if risk.rule_ids else "manual_review"
            procedure, evidence = PROCEDURES[kind]
            tests.append(
                TestStep(
                    test_id=f"TEST-{index + 1:03}",
                    risk_id=risk.risk_id,
                    rule_ids=risk.rule_ids,
                    objective=f"Assess the control relevant to: {risk.title}",
                    control="; ".join(rules_by_id[rid].requirement for rid in risk.rule_ids)
                    or "Confirm implementation and current status of the cited historical action.",
                    procedure=procedure,
                    evidence=list(evidence),
                    sample_ids=sample,
                    sample_locations=[
                        f"{rows[tid].source_file} / {rows[tid].source_sheet} / row {rows[tid].source_row}"
                        for tid in sample
                    ],
                    sample_recipe=(
                        "Select up to 10 highest absolute-value flagged rows, tie-break by transaction ID. "
                        "Judgmental selection; no statistical extrapolation. Obtain complete related groups for pattern tests."
                        if population
                        else "No payment population supports this risk. Inspect cited control/action evidence; do not invent a payment sample."
                    ),
                    days=int(days),
                    day_start=next_day,
                    day_end=next_day + int(days) - 1,
                )
            )
            next_day += int(days)
        covered = {rid for test in tests for rid in test.rule_ids}
        excluded = {}
        for rule in rules.rules:
            if rule.rule_id not in covered:
                related = [r.risk_id for r in register.risks if rule.rule_id in r.rule_ids]
                excluded[rule.rule_id] = (
                    "Associated risks were rejected by the auditor: " + ", ".join(related)
                    if related
                    else "No configured indicator triggered. This is not assurance of compliance; reconsider scope with the auditor."
                )
        return Program(
            tests=tests,
            excluded_rules=excluded,
            auditor_days=manifest.auditor_days,
            document_requests=sorted({e for test in tests for e in test.evidence}),
        )

    @staticmethod
    def score(risk, decision):
        return decision.likelihood * decision.impact if decision.decision == "amend" else risk.score

    def revise(self, program, challenges, *, model=None):
        if model and program.tests:
            advice = model.extract(
                agent_text(self.name) + "\nRespond to the challenger. Return qualitative procedure "
                "and evidence additions for every existing test_id; do not calculate or alter "
                "any sample, ID, rating, day count or scope. Preserve mandatory group follow-up.",
                [{"program": program.model_dump(mode="json"), "challenges": challenges}],
                PlanningAdvice,
            )
            if {item.test_id for item in advice.items} != {
                test.test_id for test in program.tests
            } or len(advice.items) != len(program.tests):
                raise WorkflowError("Planner advice does not cover the exact approved test set.")
            by_id = {item.test_id: item for item in advice.items}
            for test in program.tests:
                item = by_id[test.test_id]
                test.procedure += " Additional planning advice: " + item.procedure
                test.evidence = sorted(set(test.evidence + item.evidence))
        for test in program.tests:
            if "Action tracker" not in test.evidence:
                test.evidence.append("Action tracker")
        program.document_requests = sorted({e for test in program.tests for e in test.evidence})
        return program


class QAReviewer:
    name = "qa-reviewer"

    def run(self, case, rules, analytics, history, register, decisions, program):
        from procurement_audit.qa import check_all

        return check_all(case, rules, analytics, history, register, decisions, program)


class TeamLead:
    name = "team-lead"

    def run(self, case, manifest, rules, analytics, history, register, decisions, *, model=None):
        messages = []

        def send(sender, recipient, message):
            messages.append(AgentMessage(sender=sender, recipient=recipient, message=message))

        send(self.name, "planner", "Build the program from approved/amended risks only.")
        send(
            self.name,
            "challenger",
            "Challenge evidence, sample design and alternative explanations.",
        )
        planner, challenger, reviewer = Planner(), Challenger(), QAReviewer()
        with ThreadPoolExecutor(max_workers=2) as pool:
            plan_future = pool.submit(planner.run, manifest, rules, analytics, register, decisions)
            challenge_future = pool.submit(
                challenger.run, register, analytics, history, decisions, model=model
            )
            program, challenges = plan_future.result(), challenge_future.result()
        send(
            "planner",
            "challenger",
            f"Draft ready: {len(program.tests)} tests with exact source rows.",
        )
        for note in challenges:
            send("challenger", "planner", note)
        program = planner.revise(program, challenges, model=model)
        send(
            "planner",
            "qa-reviewer",
            "Group follow-up and alternative explanations included; action tracker added. Verify pack.",
        )
        checks = reviewer.run(case, rules, analytics, history, register, decisions, program)
        send(
            "qa-reviewer",
            "planner",
            "; ".join(f"{c.name}: {'PASS' if c.passed else 'FAIL'}" for c in checks),
        )
        if not all(check.passed for check in checks):
            raise WorkflowError(
                "QA blocked the pack: " + "; ".join(c.details for c in checks if not c.passed)
            )
        send(
            "planner",
            "team-lead",
            "Final pack is ready for human sign-off; no audit conclusions were made.",
        )
        send("qa-reviewer", "team-lead", "All four independent checks passed.")
        send(
            "challenger", "team-lead", "Challenge cycle complete; limitations require human review."
        )
        return program, challenges, checks, messages
