---
name: analyse-procurement
description: Coordinate spend, historical findings and risk assessment sub-agents to produce a traceable procurement risk register for human approval.
---

# Analyse procurement

Inputs: verified `rules.json`, all declared spend workbooks, contracts CSV and committee PDFs.
Outputs: `analytics.json`, `history.json`, `risk-register.json`, `risk-register.md`, `auditor-comments.md`.

Delegate spend to `spend-analyst` and committee papers to `findings-analyst`; they are independent and may run concurrently. Wait for both verified outputs before invoking `risk-assessor`.

Run `.venv/bin/python -m procurement_audit.cli analyse --case CASE`. Add `--llm` for model-assisted source reading. The default consumes human-reviewed `history-candidates.json` and verifies its quotes. Preserve filenames, sheets and Excel row numbers on every transaction. Use Python for the entire population; do not ask a model to compute metrics.

The risk register must use the fixed, disclosed likelihood × impact scale, state its judgmental limitations and cite rules, indicator IDs and/or verified history IDs. Past audit opinions are historical evidence, not new findings.

Stop at the human gate. The auditor must approve, amend or reject every risk in `outputs/auditor-comments.md` or the web UI. Never fill in an auditor decision on the auditor's behalf. Missing inputs, unverified quotations and malformed records stop the run. Reruns archive previous outputs and reset human decisions because the evidence may have changed.
