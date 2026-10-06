---
name: risk-assessment
description: Merge verified rules, analytics and committee history into a cited procurement risk register using reproducible scoring and a preserved human decision gate. Loaded by the risk-assessor after the two analysts complete.
---

# Risk assessment

Apply the guide's step 3.5. This original implementation is paired with
`build_register.py`. The agent writes judgments; Python validates citations,
fills all numeric placeholders, multiplies likelihood × impact and renders the
register. Do not type computed figures into prose. Indicators are questions for
fieldwork, never accusations. Read summaries only; do not read transaction lists.

## Step 1: Confirm inputs

Read `outputs/rules.json`, `outputs/analytics.json`, `outputs/history.json`, and
`outputs/auditor-comments.md` if present. Stop for missing/malformed inputs.
Review gaps, exclusions, optional-contract skipped tests and metric caveats.
A null statutory threshold remains unknown; do not source it from memory.

## Step 2: Work through the themes

| Theme | Evidence to consider | Sampling route |
|---|---|---|
| Procurement route/threshold proximity | Threshold clustering, printed CPR thresholds | threshold-clustering.csv |
| Aggregation and possible splitting | Anti-avoidance rule, split windows; separate care/works tags | split-purchases.csv |
| Notice coverage | High-value suppliers without a matched notice, only when contracts provided | off-contract.csv |
| Duplicates | Exact supplier and amount within the observed window; investigate invoices | duplicates.csv |
| Expired published awards | Expired-notice indicator, incomplete public award coverage | expired-notice-spend.csv |
| Award value/variation | Annualised spend comparison, award denominator caveats | spend-vs-award.csv |
| Governance/document controls | Approvals, waivers, contract recording and relevant rules without observable spend metrics | document/enquiry |
| Previous assurance/follow-up | Relevant adverse audit opinions; distinguish actual actions from unpublished gaps | source-backed theme |

Check actual filenames and metric paths in the current outputs. Do not rate a
missing/unsupported theme just to fill this table. Record it in `excluded`.

Use a repeatable likelihood rubric, then explain any departure: one for a
rule-only control with no adverse evidence; two for an isolated indicator; three
for a recurring indicator across suppliers/periods; four for pervasive current
indicators with corroborating evidence; five only when direct current evidence
supports the council's highest definition. These are planning judgments, not
statistical probabilities. Cite a real rule, scalar metric or history item in
each justification. A repeat finding on the same theme with adverse assurance
raises the baseline likelihood by one, capped at five; cite that audit, record
`repeat_finding`, and state the uplift in words.

Assign impact using the council's sourced impact descriptors. Do not treat
spend totals as proven loss. Explain which descriptor and evidence support the
score; acknowledge unavailable consequence data. Score one through five.

Use the explicit `history.scoring_method.combination.matrix` cells and Table 4
bands, not an invented product-to-label mapping. `build_register.py` reports the
matrix label and score band separately. Preserve the Table 4 / Figure 4 corporate
register threshold conflict in the header using `selection_note`. If no usable
method is recorded, the builder discloses its fallback scales and bands.

## Step 3: Citation and numeric syntax

- `[rule:CPR-01]` resolves to an existing rule ID.
- `[metric:$.tests.duplicates.count]` resolves to a scalar current metric.
- `[history:AUD-01]` resolves to an item with that ID in history.json.
- `{{$.tests.duplicates.count}}` is filled by Python; never type that count.
- Score fields, IDs and sample source paths are structural data, not prose.
- Never put supplier names in titles, statements, justifications or focus.
- Project memory contains procedure only. It never supplies evidence or scores.

## Step 4: Write judgments and handle revisions

Write `outputs/risk-ratings.json` in this format, using current valid evidence:

```json
{
  "risks": [{
    "id": "R-01",
    "title": "Procurement requirements may not be aggregated",
    "statement": "Related payments warrant checking the procurement route.",
    "likelihood": {"score": 2, "justification": "An observed pattern requires investigation [rule:CPR-01]."},
    "impact": {"score": 3, "justification": "A missed route could weaken competition [rule:CPR-01]."},
    "proposed_focus": "Compare related requirements with approvals and quotations.",
    "recommend_in_scope": true,
    "sample_source": "split-purchases.csv"
  }],
  "excluded": []
}
```

This example demonstrates shape only; its IDs/scores are not evidence. An
out-of-scope recommendation requires `scope_reason`. Optional repeat evidence:
`"repeat_finding": {"history_id": "AUD-01", "base_likelihood": 2}`; this requires
an adverse `assurance_opinion` or `opinion` on that item. An auditor-set score
unsupported by evidence must be marked `"auditor_override": true` and explained.

The first clean build saves `risk-baseline.json` and a blank decision table.
Only the auditor supplies decisions and reviewer/date. Preserve all existing
rows and comments, including rejected risks. Blank means undecided. Do not
execute the guide's example approve/amend/reject instructions as real decisions.

For a revision: keep approved and undecided risks byte-for-byte equivalent in
the judgment structure; amend only as the human comment requests; remove each
rejected risk from `risks` and retain `{ "id": "R-..", "reason": "human reason" }`
in `excluded`. Add a top-level block:

```json
"revision": {
  "number": 1,
  "changes": [{"id": "R-01", "action": "amended", "summary": "Applied the auditor's requested likelihood change."}]
}
```

Rejected changes use `action: "rejected"`. Explicit comments `likelihood to 3`,
`impact=4` etc. are validated numerically. Semantic interpretation of free-text
amendments still needs the human/Claude review. No new risks enter this gate
revision; new scope requires a fresh assessment and human review. Do not edit
`risk-baseline.json` or `gate-evidence.json` to bypass checks.

## Step 5: Render and validate

```bash
.venv/bin/python .claude/skills/risk-assessment/build_register.py outputs/risk-ratings.json
```

Fix every FAIL and WARN. A malformed risk is excluded from the draft register
with a reason and a nonzero exit; this is a blocked draft. Do not claim success
based only on files existing. Builder options `--rules`, `--analytics`,
`--history`, `--out-dir` support isolated test fixtures and harness sessions.
The builder preserves decisions and generates `gate-evidence.json` bound to the
actual current ratings, comments and register. Planning requires all decisions
plus a clean applied revision, not merely a markdown revision heading.

## Step 6: Report

Read the output for sense. Check that risk statements contain no supplier names,
that no unsupported numbers appeared, and that caveats reflect inputs. Report
kept/excluded themes, scoring method and discrepancy, limitations, output paths,
and validation results in under four hundred words. Request the auditor's
individual decisions; never infer approval from silence or tutorial examples.
