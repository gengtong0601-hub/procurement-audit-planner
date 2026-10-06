import pytest

from procurement_audit.models import (
    Challenges,
    Decision,
    Decisions,
    PlanningAdvice,
    RiskNarratives,
)
from procurement_audit.models import (
    TestAdvice as PlanningStepAdvice,
)
from procurement_audit.storage import WorkflowError, read_json
from procurement_audit.workflow import (
    analysis_artifacts,
    build_pack,
    extract_rules,
    run_analysis,
    save_decisions,
)


def test_model_roles_preserve_python_numbers_and_human_scope(case, monkeypatch):
    calls = []

    class FakeModel:
        def extract(self, instructions, documents, schema):
            calls.append(schema.__name__)
            if schema.__name__ == "RuleBook":
                return schema.model_validate(read_json(case / "inputs/rule-candidates.json"))
            if schema.__name__ == "History":
                return schema.model_validate(read_json(case / "inputs/history-candidates.json"))
            if schema is RiskNarratives:
                return schema(
                    items=[
                        {
                            "risk_id": r["risk_id"],
                            "narrative": "Investigate the indicator and corroborate it against the underlying procurement evidence.",
                        }
                        for r in documents[0]["register"]["risks"]
                    ]
                )
            if schema is Challenges:
                return schema(notes=["Confirm historical action closure with current evidence."])
            if schema is PlanningAdvice:
                return schema(
                    items=[
                        PlanningStepAdvice(
                            test_id=t["test_id"],
                            procedure="Corroborate explanations against contemporaneous approval records.",
                            evidence=["Approval records"],
                        )
                        for t in documents[0]["program"]["tests"]
                    ]
                )
            raise AssertionError(schema)

    monkeypatch.setattr("procurement_audit.workflow.ModelReader", FakeModel)
    before = analysis_artifacts(case)[1]
    extract_rules(case, use_llm=True)
    run_analysis(case, use_llm=True)
    assert analysis_artifacts(case)[1] == before
    register = analysis_artifacts(case)[3]
    save_decisions(
        case,
        Decisions(
            reviewer="Synthetic model test auditor",
            decisions=[
                Decision(
                    risk_id=r.risk_id,
                    decision="approve",
                    comment="Automated synthetic fixture only.",
                )
                for r in register.risks
            ],
        ),
    )
    program = build_pack(case, use_llm=True)
    assert sum(t.days for t in program.tests) == 15
    assert all("Approval records" in t.evidence for t in program.tests)
    assert calls == ["RuleBook", "History", "RiskNarratives", "Challenges", "PlanningAdvice"]


def test_model_cannot_add_unknown_risks(case, monkeypatch):
    class BadModel:
        def extract(self, instructions, documents, schema):
            if schema.__name__ == "History":
                return schema.model_validate(read_json(case / "inputs/history-candidates.json"))
            return RiskNarratives(
                items=[
                    {
                        "risk_id": "RISK-999",
                        "narrative": "A fabricated risk without supporting evidence.",
                    }
                ]
            )

    monkeypatch.setattr("procurement_audit.workflow.ModelReader", BadModel)
    with pytest.raises(WorkflowError, match="exact computed risk set"):
        run_analysis(case, use_llm=True)
