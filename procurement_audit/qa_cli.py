"""Entrypoint shared by the four individually callable verification scripts."""

import argparse
import sys
from pathlib import Path

from procurement_audit.decisions import read_decisions
from procurement_audit.models import Program
from procurement_audit.qa import check_numbers, check_quotes, check_samples, check_traceability
from procurement_audit.storage import WorkflowError, outputs, read_json
from procurement_audit.workflow import analysis_artifacts


def main(name):
    parser = argparse.ArgumentParser(description=f"Independent audit QA: {name}")
    parser.add_argument("--case", required=True, type=Path)
    case = parser.parse_args().case.resolve()
    try:
        rules, analytics, history, register = analysis_artifacts(case)
        if name == "quotes":
            result = check_quotes(case, rules, history)
        elif name == "numbers":
            result = check_numbers(case, rules, analytics, register)
        else:
            program = Program.model_validate(read_json(outputs(case) / "program.json"))
            if name == "samples":
                result = check_samples(case, rules, analytics, register, program)
            else:
                result = check_traceability(
                    rules,
                    analytics,
                    history,
                    register,
                    read_decisions(outputs(case) / "auditor-comments.md"),
                    program,
                )
        print(f"PASS {name}: {result}")
        return 0
    except (WorkflowError, ValueError, OSError) as exc:
        print(f"FAIL {name}: {exc}", file=sys.stderr)
        return 1
