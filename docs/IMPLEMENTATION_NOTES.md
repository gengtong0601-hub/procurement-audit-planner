# Guide source and implementation differences

The saved guide pages and copyable prompts in `docs/reference/` are the source
for this assignment: https://procurement-audit-planner.vercel.app/ . Author/
licence information was not inferred. These files retain teaching examples;
those examples are not real audit decisions or current evidence.

The extract-rules and audit-program skills, six agent definitions, rule quote
verifier, audit-pack builder and four QA checks plus runner were initialized
from the guide's complete copyable code blocks. Their architecture, ownership,
message protocol and human-gate separation are retained. The source pages only
provide design requirements for step 3.5 (risk-assessment); its SKILL.md and
build_register.py are an original implementation of those requirements.

Local corrections to supplied baseline code:

- Invalid YAML descriptions in four supplied definitions are quoted so native
  loaders can parse colon-containing descriptions.
- Gate checks require a reviewer/date and hash-bound `gate-evidence.json` written
  by a successfully validated risk revision, including hashes of the current
  rules, analytics and history source summaries. A manually typed revision heading
  does not count as applied decisions. The gate blocks rendering immediately.
- Risk revisions compare judgments with `risk-baseline.json`: approved/undecided
  risks cannot change, rejections require removal/reason, amendments require a
  change record, and explicit requested likelihood/impact scores must match.
  Free-text semantic interpretation still requires human/agent review.
- JSON metric paths must match the entire supported path grammar. Invalid
  suffixes are rejected rather than accidentally resolving a prefix.
- Sample paths remain inside analytics-full; transaction sample sizes must be
  positive. Missing expected sample files, missing/empty program/plan, missing
  pack figures, missing register and absent human gate are explicit QA failures.
  Document-only tests may intentionally have no transaction sample.
- Plan validation now blocks before rendering (the supplied script could emit
  documents despite failures); valid pack inputs and outputs receive an integrity
  record checked by trace QA. Duplicate/unsafe control and test IDs are rejected.
- Build errors produce a clear FAIL and nonzero exit. Risks with broken evidence
  are omitted from the blocked draft with a reason, never silently approved.

`tests/test_gates.py` uses temporary synthetic fixtures under tests/ only.
Approval, amendment and rejection there exercise the validators, not the real
council data. Real `outputs/auditor-comments.md` remains undecided until an
explicit human action. Gate evidence hashes bind integrity, not human identity:
reviewer authentication and authorization are harness responsibilities.

The number QA is a guide-style cross-check of values, not a proof that every
figure is attached to the correct concept. Final auditors still review meaning,
coverage, citations and sampling. Public award matching, annualisation and
repeat patterns are indicators with declared limitations, not allegations.
