---
name: build-audit-pack
description: Lead a planner, challenger and QA reviewer team to create and check a procurement audit planning pack from explicitly approved risks.
---

# Build audit pack

Inputs: verified analysis artifacts and completed human decisions.
Outputs: `planning-memo.md`, `risk-control-matrix.md`, `audit-program.md`, `challenge.md`, `qa-report.json`, `team-messages.json`, and pending `review.md`.

1. Validate that every risk has a named human auditor's approve/amend/reject decision. Do not auto-approve, including during demonstrations. Amended ratings and rejections require explanations.
2. With native agent-team support, the team lead spawns `planner`, `challenger` and `qa-reviewer`. Planner and challenger work independently, exchange substantive messages, and resolve challenges before QA. All three report to the lead. If that runtime lacks team support, explicitly report the limitation; do not claim native teams ran.
3. The portable Python implementation of this protocol runs with `.venv/bin/python -m procurement_audit.cli plan --case CASE`. Its role workers and message log are deterministic; they are not a claim that Claude Code's experimental native team runtime ran.
4. Plan every approved/amended risk and exclude rejected risks. Preserve risk → rule → required control → test → sample → workbook row links. Explain every omitted rule. Do not silently drop approved risks to fit a time budget.
5. Include sample recipes, exact payment rows, council document requests, limitations and auditor scope decisions. Human amendments govern final priorities.
6. Run all four checks: `scripts/check_quotes.py`, `scripts/check_numbers.py`, `scripts/check_traceability.py`, `scripts/check_samples.py` with `--case CASE`. Fix the generated pack through the Python workflow; never disable a check or edit source data to pass it.
7. Send the auditor the completed pack and wait for the second human gate. `review.md` remains pending until the auditor signs off or returns it for revision through the UI or CLI.

The pack plans fieldwork. It performs no audit tests and reaches no audit findings. Do not publish real flagged payments out of context.
