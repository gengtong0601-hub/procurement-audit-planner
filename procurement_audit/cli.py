"""Run all assignment stages from Python without depending on a web UI."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from procurement_audit.demo import create_demo
from procurement_audit.models import Signoff
from procurement_audit.storage import WorkflowError
from procurement_audit.workflow import (
    build_pack,
    case_status,
    extract_rules,
    run_analysis,
    sign_off,
    verify_pack,
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Procurement Audit Planner — Python Skills + Agents"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ["demo", "extract-rules", "analyse", "plan", "check", "status", "sign-off"]:
        command_parser = sub.add_parser(command)
        command_parser.add_argument("--case", type=Path, required=True)
        if command in {"extract-rules", "analyse", "plan"}:
            command_parser.add_argument(
                "--llm", action="store_true", help="Use configured LLM for source reading."
            )
        if command == "check":
            command_parser.add_argument(
                "--only", choices=["quotes", "numbers", "traceability", "samples"]
            )
        if command == "sign-off":
            command_parser.add_argument("--reviewer", required=True)
            command_parser.add_argument(
                "--decision", choices=["sign_off", "return_for_revision"], required=True
            )
            command_parser.add_argument("--comment", required=True)
    args = parser.parse_args(argv)
    case = args.case.resolve()
    try:
        if args.command == "demo":
            create_demo(case)
            extract_rules(case)
            register = run_analysis(case)
            print(
                f"Synthetic demonstration created. {len(register.risks)} risks await HUMAN review."
            )
            print(f"Review and edit: {case / 'outputs/auditor-comments.md'}")
        elif args.command == "extract-rules":
            rules = extract_rules(case, use_llm=args.llm)
            print(f"Verified {len(rules.rules)} source-quoted rules; saved outputs/rules.json.")
        elif args.command == "analyse":
            register = run_analysis(case, use_llm=args.llm)
            print(
                f"Analysed sources; {len(register.risks)} risks await decisions in auditor-comments.md."
            )
        elif args.command == "plan":
            program = build_pack(case, use_llm=args.llm)
            print(
                f"Created planning memo, matrix and program: {len(program.tests)} tests. Awaiting human sign-off."
            )
        elif args.command == "check":
            checks = verify_pack(case)
            for check in checks:
                if not args.only or check.name == args.only:
                    print(f"PASS {check.name}: {check.details}")
        elif args.command == "status":
            result = case_status(case)
            print(json.dumps({k: result[k] for k in ["stage", "stale", "files"]}, indent=2))
        elif args.command == "sign-off":
            sign_off(
                case, Signoff(reviewer=args.reviewer, decision=args.decision, comment=args.comment)
            )
            print("Recorded human decision in outputs/review.md and outputs/signoff.json.")
    except (WorkflowError, ValidationError, OSError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
