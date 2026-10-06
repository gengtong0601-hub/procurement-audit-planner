"""The three analysis sub-agents and their explicit file handoffs."""

from decimal import Decimal
from pathlib import Path

from procurement_audit.analytics import analyse
from procurement_audit.llm import agent_text
from procurement_audit.models import History, Register, Risk, RiskNarratives, RuleBook
from procurement_audit.sources import source_bundle, verify_citations
from procurement_audit.storage import WorkflowError, load_manifest, read_json, write_json


class SpendAnalyst:
    name = "spend-analyst"

    def run(self, case: Path, rules: RuleBook, destination: Path):
        analytics = analyse(case, rules)
        write_json(destination / "analytics.json", analytics)
        return analytics


class FindingsAnalyst:
    name = "findings-analyst"

    def run(self, case: Path, rules: RuleBook, destination: Path, *, model=None):
        manifest = load_manifest(case)
        if model:
            history = model.extract(
                agent_text(self.name),
                source_bundle(case, manifest.committee_papers)
                + [{"verified_rules": rules.model_dump(mode="json")}],
                History,
            )
        else:
            history = History.model_validate(read_json(case / "inputs/history-candidates.json"))
        verify_citations(case, history.items, set(manifest.committee_papers))
        rule_ids = {r.rule_id for r in rules.rules}
        if len({h.item_id for h in history.items}) != len(history.items):
            raise WorkflowError("Audit history IDs must be unique.")
        if any(not set(h.rule_ids) <= rule_ids for h in history.items):
            raise WorkflowError("History items refer to unknown rules.")
        covered = {h.source_file for h in history.items}
        if covered != set(manifest.committee_papers):
            raise WorkflowError("Every supplied committee paper needs a cited coverage entry.")
        write_json(destination / "history.json", history)
        return history


def band(share: Decimal) -> int:
    """Fixed illustrative five-point scale, subject to explicit auditor amendment."""
    for index, cutoff in enumerate(["0.01", "0.05", "0.10", "0.25"], 1):
        if share < Decimal(cutoff):
            return index
    return 5


class RiskAssessor:
    name = "risk-assessor"

    def run(self, rules, analytics, history, destination: Path, *, model=None):
        risks = []
        rules_by_id = {r.rule_id: r for r in rules.rules}
        for indicator in analytics.indicators:
            if not indicator.count:
                continue
            likelihood = band(Decimal(indicator.count) / analytics.row_count)
            impact = (
                band(indicator.gross_value / analytics.gross_spend) if analytics.gross_spend else 1
            )
            related = [h.item_id for h in history.items if indicator.rule_id in h.rule_ids]
            risks.append(
                Risk(
                    risk_id=f"RISK-{len(risks) + 1:03}",
                    title=indicator.kind.replace("_", " ").capitalize(),
                    rule_ids=[indicator.rule_id],
                    indicator_ids=[indicator.indicator_id],
                    history_ids=related,
                    likelihood=likelihood,
                    impact=impact,
                    score=likelihood * impact,
                    rating_rationale=(
                        f"Likelihood {likelihood}: {indicator.count}/{analytics.row_count} payment rows. "
                        f"Impact {impact}: {indicator.gross_value}/{analytics.gross_spend} gross spend. "
                        f"Computed by analytics.py and agents/analysis.py; source {indicator.indicator_id}."
                    ),
                    narrative=f"Investigate compliance with {rules_by_id[indicator.rule_id].clause}. "
                    + indicator.description
                    + " This is a planning indicator, not an audit finding.",
                )
            )
        represented_history = {hid for risk in risks for hid in risk.history_ids}
        for item in history.items:
            if (
                item.category in {"open_action", "registered_risk"}
                and item.item_id not in represented_history
            ):
                risks.append(
                    Risk(
                        risk_id=f"RISK-{len(risks) + 1:03}",
                        title=item.description,
                        rule_ids=item.rule_ids,
                        indicator_ids=[],
                        history_ids=[item.item_id],
                        likelihood=3,
                        impact=3,
                        score=9,
                        rating_rationale=(
                            f"{item.item_id}: an open action or registered risk warrants review. "
                            "Provisional planning judgment is 3 × 3; the auditor must approve or amend it."
                        ),
                        narrative="Confirm current status and supporting evidence; no new audit conclusion is reached.",
                    )
                )
        for rule in rules.rules:
            if rule.indicator == "manual_review":
                risks.append(
                    Risk(
                        risk_id=f"RISK-{len(risks) + 1:03}",
                        title=rule.requirement,
                        rule_ids=[rule.rule_id],
                        indicator_ids=[],
                        history_ids=[],
                        likelihood=3,
                        impact=3,
                        score=9,
                        rating_rationale=f"{rule.rule_id}: manual control cannot be assessed from payments. "
                        "Provisional 3 × 3 judgment requires auditor approval or amendment.",
                        narrative="Request evidence and assess the control during fieldwork.",
                    )
                )
        register = Register(
            risks=risks,
            method="score = likelihood × impact. Shares <1%, <5%, <10%, <25%, and ≥25% map to "
            "1–5. Likelihood uses flagged-row share; impact uses gross-value share. "
            "This is an illustrative planning rubric, not a calibrated probability estimate. "
            "Evidence-only risks start at a disclosed provisional 3 × 3 for human review.",
        )
        if model and risks:
            narratives = model.extract(
                agent_text(self.name) + "\nReturn qualitative narrative for each existing risk_id. "
                "Do not add risks, calculate figures or reproduce numbers in the narrative. "
                "Numeric evidence and ratings are attached separately by Python.",
                [
                    {
                        "register": register.model_dump(mode="json"),
                        "rules": rules.model_dump(mode="json"),
                        "history": history.model_dump(mode="json"),
                    }
                ],
                RiskNarratives,
            )
            expected = {r.risk_id for r in risks}
            if {item.risk_id for item in narratives.items} != expected or len(
                narratives.items
            ) != len(risks):
                raise WorkflowError(
                    "Model risk narratives do not cover the exact computed risk set."
                )
            by_id = {item.risk_id: item.narrative for item in narratives.items}
            for risk in register.risks:
                risk.narrative = by_id[risk.risk_id]
        write_json(destination / "risk-register.json", register)
        return register
