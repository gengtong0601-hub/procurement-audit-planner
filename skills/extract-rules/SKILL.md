---
name: extract-rules
description: Extract every testable procurement rule from a council's Contract Procedure Rules PDF, retaining clause references and verified verbatim quotations.
---

# Extract rules

Inputs: `inputs/manifest.json` and its declared Contract Procedure Rules PDF.
Output: `outputs/rules.json` with a verification state file.

1. Read every page of the declared PDF. Stop if it is missing, unreadable or image-only; do not invent OCR text.
2. Identify every testable obligation, prohibition, threshold and required approval. Preserve exceptions and scope in `requirement`. Do not limit extraction to the four automated indicator families.
3. For each rule, record a unique `RULE-NNN` ID, clause, source filename, one-based PDF page and verbatim quote. Whitespace may be normalized; wording and punctuation may not be changed.
4. Map supported tests to `threshold_clustering`, `split_purchases`, `off_contract` or `duplicates`. Use `manual_review` for every other testable rule. A duplicate-payment rule must actually exist in the supplied source; never invent one to enable a detector.
5. Thresholds must come from the quoted rule. Multiple thresholds require separate, clearly scoped rules. The supplied detector assumes one currency and simple monetary thresholds; preserve complex exceptions as manual review rules.
6. Use the JSON schema in `procurement_audit.models.RuleBook`. Save reviewed proposals to `inputs/rule-candidates.json`, then run `.venv/bin/python -m procurement_audit.cli extract-rules --case CASE`.
7. Alternatively run the same command with `--llm` to use the configured model adapter. The model output is never accepted until Python verifies every quote against the cited source page.
8. Inspect extraction notes and coverage against every PDF page. Literal quote verification does not prove that all obligations were extracted correctly. Stop and report incomplete coverage.

Never calculate spend totals, risk metrics or sample sizes with the model. Never rewrite source documents to make a quote pass verification.
