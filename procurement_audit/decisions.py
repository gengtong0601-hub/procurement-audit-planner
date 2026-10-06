"""Human gate one: every risk must receive an explicit auditor decision."""

import re
from pathlib import Path

from procurement_audit.models import Decision, Decisions, Register
from procurement_audit.storage import WorkflowError, write_text


def render_decisions(decisions: Decisions) -> str:
    lines = ["# Auditor comments", "", f"Reviewer: {decisions.reviewer}", ""]
    for item in decisions.decisions:
        lines.extend(
            [
                f"## {item.risk_id}",
                f"Decision: {item.decision}",
                f"Likelihood: {item.likelihood or ''}",
                f"Impact: {item.impact or ''}",
                "Comment: " + item.comment.replace("\n", " "),
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def read_decisions(path: Path) -> Decisions:
    if not path.is_file():
        raise WorkflowError(
            "Missing auditor-comments.md. A human must decide each risk before planning."
        )
    content = path.read_text(encoding="utf-8")
    reviewer = re.search(r"^Reviewer: (.+)$", content, re.MULTILINE)
    if not reviewer:
        raise WorkflowError("auditor-comments.md needs a Reviewer line.")
    parsed = []
    for risk_id, body in re.findall(
        r"^## (RISK-\d+)\n(.*?)(?=^## |\Z)", content, re.MULTILINE | re.DOTALL
    ):
        fields = {}
        for label in ["Decision", "Likelihood", "Impact", "Comment"]:
            match = re.search(rf"^{label}:[ \t]*(.*)$", body, re.MULTILINE)
            if not match:
                raise WorkflowError(f"Missing {label} for {risk_id}.")
            fields[label] = match.group(1).strip()
        try:
            parsed.append(
                Decision(
                    risk_id=risk_id,
                    decision=fields["Decision"],
                    comment=fields["Comment"],
                    likelihood=int(fields["Likelihood"]) if fields["Likelihood"] else None,
                    impact=int(fields["Impact"]) if fields["Impact"] else None,
                )
            )
        except ValueError as exc:
            raise WorkflowError(f"Invalid decision for {risk_id}: {exc}") from exc
    return Decisions(reviewer=reviewer.group(1).strip(), decisions=parsed)


def validate_gate(register: Register, decisions: Decisions):
    actual = [d.risk_id for d in decisions.decisions]
    expected = {r.risk_id for r in register.risks}
    if set(actual) != expected or len(actual) != len(expected):
        raise WorkflowError(
            "A unique decision is required for every risk; unknown IDs are not allowed."
        )
    if decisions.reviewer == "PENDING" or any(d.decision == "pending" for d in decisions.decisions):
        raise WorkflowError(
            "Human gate is pending: enter a reviewer and approve, amend or reject every risk."
        )


def write_pending(register: Register, path: Path):
    write_text(
        path,
        render_decisions(
            Decisions(
                reviewer="PENDING",
                decisions=[Decision(risk_id=r.risk_id, decision="pending") for r in register.risks],
            )
        ),
    )
