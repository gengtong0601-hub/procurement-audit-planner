"""Persistent stage orchestration, source freshness, human gates and pack integrity."""

import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from procurement_audit.agents.analysis import FindingsAnalyst, RiskAssessor, SpendAnalyst
from procurement_audit.agents.team import TeamLead
from procurement_audit.decisions import (
    read_decisions,
    render_decisions,
    validate_gate,
    write_pending,
)
from procurement_audit.llm import ModelReader, skill_text
from procurement_audit.models import (
    Analytics,
    Decisions,
    History,
    Program,
    Register,
    RuleBook,
    Signoff,
)
from procurement_audit.qa import check_all
from procurement_audit.reporting import pack_markdown, register_markdown
from procurement_audit.sources import source_bundle, verify_citations, verify_rule_thresholds
from procurement_audit.storage import (
    WorkflowError,
    digest,
    load_manifest,
    outputs,
    read_json,
    source_hashes,
    write_json,
    write_text,
)

PACK_FILES = [
    "planning-memo.md",
    "risk-control-matrix.md",
    "audit-program.md",
    "program.json",
    "qa-report.json",
    "challenge.md",
    "team-messages.json",
]


def ensure_fresh(case: Path):
    expected = read_json(outputs(case) / "analysis-state.json")
    if expected["sources"] != source_hashes(case):
        raise WorkflowError(
            "Source files changed after analysis. Rerun analysis and obtain fresh auditor decisions."
        )
    for name, value in expected["artifacts"].items():
        path = outputs(case) / name
        if not path.is_file() or digest(path) != value:
            raise WorkflowError(
                f"Analysis artifact changed: {name}. Rerun analysis before planning."
            )


def extract_rules(case: Path, *, use_llm=False):
    manifest = load_manifest(case)
    rules = (
        ModelReader().extract(
            skill_text("extract-rules"), source_bundle(case, [manifest.contract_rules]), RuleBook
        )
        if use_llm
        else RuleBook.model_validate(read_json(case / "inputs/rule-candidates.json"))
    )
    if len({r.rule_id for r in rules.rules}) != len(rules.rules):
        raise WorkflowError("Rule IDs must be unique.")
    verify_citations(case, rules.rules, {manifest.contract_rules})
    verify_rule_thresholds(rules)
    write_json(outputs(case) / "rules.json", rules)
    write_json(
        outputs(case) / "rules-state.json",
        {
            "source_hash": digest(case / "inputs" / manifest.contract_rules),
            "artifact_hash": digest(outputs(case) / "rules.json"),
        },
    )
    return rules


def run_analysis(case: Path, *, use_llm=False):
    manifest = load_manifest(case)
    out = outputs(case)
    rules = RuleBook.model_validate(read_json(out / "rules.json"))
    state = read_json(out / "rules-state.json")
    if state != {
        "source_hash": digest(case / "inputs" / manifest.contract_rules),
        "artifact_hash": digest(out / "rules.json"),
    }:
        raise WorkflowError("Rules or their source changed. Rerun extract-rules before analysis.")
    verify_citations(case, rules.rules, {manifest.contract_rules})
    with tempfile.TemporaryDirectory(prefix="audit-stage-", dir=case) as temporary:
        stage = Path(temporary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            spend = pool.submit(SpendAnalyst().run, case, rules, stage)
            findings = pool.submit(
                FindingsAnalyst().run, case, rules, stage, model=ModelReader() if use_llm else None
            )
            analytics, history = spend.result(), findings.result()
        register = RiskAssessor().run(
            rules, analytics, history, stage, model=ModelReader() if use_llm else None
        )
        if analytics.source_hashes != source_hashes(case):
            raise WorkflowError(
                "Sources changed during analysis. Keep the inputs stable and rerun."
            )
        write_text(
            stage / "risk-register.md", register_markdown(register, analytics, history, rules)
        )
        # Preserve the previous complete run and auditor decisions before replacing stage outputs.
        if (out / "analysis-state.json").exists():
            archive = case / "archives" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            shutil.copytree(out, archive)
        for name in PACK_FILES + ["pack-state.json", "review.md", "signoff.json"]:
            (out / name).unlink(missing_ok=True)
        for path in stage.iterdir():
            shutil.copy2(path, out / path.name)
        write_pending(register, out / "auditor-comments.md")
        write_json(
            out / "analysis-state.json",
            {
                "sources": source_hashes(case),
                "mode": "llm-extraction" if use_llm else "reviewed-candidates",
                "artifacts": {
                    name: digest(out / name)
                    for name in [
                        "rules.json",
                        "analytics.json",
                        "history.json",
                        "risk-register.json",
                        "risk-register.md",
                    ]
                },
            },
        )
    return register


def analysis_artifacts(case: Path):
    ensure_fresh(case)
    out = outputs(case)
    return (
        RuleBook.model_validate(read_json(out / "rules.json")),
        Analytics.model_validate(read_json(out / "analytics.json")),
        History.model_validate(read_json(out / "history.json")),
        Register.model_validate(read_json(out / "risk-register.json")),
    )


def save_decisions(case: Path, decisions: Decisions):
    *_, register = analysis_artifacts(case)
    validate_gate(register, decisions)
    out = outputs(case)
    if (out / "pack-state.json").exists():
        archive = case / "archives" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        shutil.copytree(out, archive)
    write_text(out / "auditor-comments.md", render_decisions(decisions))
    for name in PACK_FILES + ["pack-state.json", "review.md", "signoff.json"]:
        (out / name).unlink(missing_ok=True)


def build_pack(case: Path, *, use_llm=False):
    manifest = load_manifest(case)
    rules, analytics, history, register = analysis_artifacts(case)
    out = outputs(case)
    decisions = read_decisions(out / "auditor-comments.md")
    validate_gate(register, decisions)
    program, challenges, checks, messages = TeamLead().run(
        case,
        manifest,
        rules,
        analytics,
        history,
        register,
        decisions,
        model=ModelReader() if use_llm else None,
    )
    write_json(out / "program.json", program)
    for name, content in pack_markdown(
        manifest, rules, analytics, history, register, decisions, program, challenges
    ).items():
        write_text(out / name, content)
    write_text(
        out / "challenge.md",
        "# Challenger review\n\n" + "\n".join("- " + note for note in challenges) + "\n",
    )
    write_json(out / "qa-report.json", [check.model_dump(mode="json") for check in checks])
    write_json(
        out / "team-messages.json", [message.model_dump(mode="json") for message in messages]
    )
    write_json(
        out / "pack-state.json",
        {
            "decision_hash": digest(out / "auditor-comments.md"),
            "mode": "llm-assisted" if use_llm else "deterministic",
            "artifacts": {name: digest(out / name) for name in PACK_FILES},
        },
    )
    write_text(
        out / "review.md",
        "# Auditor sign-off\n\nStatus: PENDING\n\n"
        "Review the three planning documents, challenger comments and all four QA checks. "
        "Then record sign-off or return for revision using the UI or sign-off CLI command.\n",
    )
    (out / "signoff.json").unlink(missing_ok=True)
    return program


def verify_pack(case: Path):
    rules, analytics, history, register = analysis_artifacts(case)
    out = outputs(case)
    state = read_json(out / "pack-state.json")
    if state["decision_hash"] != digest(out / "auditor-comments.md"):
        raise WorkflowError("Auditor decisions changed. Rebuild the planning pack before sign-off.")
    for name, value in state["artifacts"].items():
        if not (out / name).is_file() or digest(out / name) != value:
            raise WorkflowError(f"Planning artifact changed: {name}. Rebuild and review the pack.")
    decisions = read_decisions(out / "auditor-comments.md")
    program = Program.model_validate(read_json(out / "program.json"))
    checks = check_all(case, rules, analytics, history, register, decisions, program)
    if not all(check.passed for check in checks):
        raise WorkflowError("QA failed: " + "; ".join(c.details for c in checks if not c.passed))
    return checks


def sign_off(case: Path, signoff: Signoff):
    verify_pack(case)
    timestamp = datetime.now(UTC).isoformat()
    out = outputs(case)
    write_json(
        out / "signoff.json",
        {
            **signoff.model_dump(),
            "recorded_at": timestamp,
            "pack_hash": digest(out / "pack-state.json"),
        },
    )
    write_text(
        out / "review.md",
        f"# Auditor sign-off\n\nStatus: {signoff.decision}\n\n"
        f"Reviewer: {signoff.reviewer}\n\nRecorded at: {timestamp}\n\n"
        f"Comment: {signoff.comment}\n\n"
        "This decision concerns the planning pack only. It does not express an audit opinion.\n",
    )


def case_status(case: Path):
    manifest = load_manifest(case)
    out = outputs(case)
    result = {
        "manifest": manifest.model_dump(mode="json"),
        "stage": "inputs",
        "files": [],
        "stale": False,
    }
    if (out / "rules.json").exists():
        result["stage"] = "rules"
    if (out / "analysis-state.json").exists():
        result["stage"] = "risk_review"
        try:
            ensure_fresh(case)
        except WorkflowError as exc:
            result.update(stale=True, error=str(exc))
        for key, name in [
            ("register", "risk-register.json"),
            ("analytics", "analytics.json"),
            ("history", "history.json"),
        ]:
            result[key] = read_json(out / name)
        result["rules"] = read_json(out / "rules.json")
        result["decisions"] = read_decisions(out / "auditor-comments.md").model_dump(mode="json")
    if (out / "pack-state.json").exists():
        result["stage"] = "signoff"
        try:
            verify_pack(case)
        except WorkflowError as exc:
            result.update(stale=True, error=str(exc))
        result["program"] = read_json(out / "program.json")
        result["checks"] = read_json(out / "qa-report.json")
        result["messages"] = read_json(out / "team-messages.json")
    if (out / "signoff.json").exists() and not result["stale"]:
        signoff = read_json(out / "signoff.json")
        result["signoff"] = signoff
        result["stage"] = (
            "signed_off" if signoff["decision"] == "sign_off" else "revision_requested"
        )
    if out.exists():
        result["files"] = sorted(
            p.name for p in out.iterdir() if p.is_file() and p.suffix in {".json", ".md"}
        )
    return result
