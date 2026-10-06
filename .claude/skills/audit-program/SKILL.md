---
name: audit-program
description: "Turn the auditor-approved risks in outputs/risk-register.md into the audit planning pack: planning-memo.md, risk-control-matrix.md and audit-program.md (risk \u2192 expected control \u2192 test step \u2192 targeted sample, plus the PBC list), rendered and checked by build_pack.py from the planner's judgments in outputs/audit-plan.json. Loaded by the planner teammate at Phase 3."
---

# audit-program

Produce the pack a human auditor will sign off. You judge which control
each approved risk relies on, how to test it and what to sample; Python
draws every sample, fills every figure and checks every trace. Write your
judgments to `outputs/audit-plan.json`, then let `build_pack.py` render
`planning-memo.md`, `risk-control-matrix.md` and `audit-program.md`.
A plan the script cannot trace is not rendered, by design.

## Inputs and outputs

| | Path |
| --- | --- |
| Approved risks | `outputs/risk-register.md` (a revision) and `outputs/auditor-comments.md` (the decisions) |
| Ratings | `outputs/risk-ratings.json` (scope flags, overrides, `sample_source` per risk) |
| Rules | `outputs/rules.json` (rule IDs, clauses, quotes) |
| Analytics | `outputs/analytics.json` (named metrics) and `outputs/analytics-full/*.csv` (the lists to sample from) |
| Your judgments | `outputs/audit-plan.json` (you write this) |
| Builder | `.claude/skills/audit-program/build_pack.py` |
| Pack | `outputs/planning-memo.md`, `outputs/risk-control-matrix.md`, `outputs/audit-program.md`, `outputs/samples/T-*.csv`, `outputs/pack-figures.json` (script writes these) |

Stop and report if any input is missing. Never edit the inputs.

## Non-negotiable rules

1. **Only approved risks.** Run `build_pack.py --gate` first. It fails
   if any risk in the register has no decision, or if the register is
   not a revision that applied the decisions. Plan exactly the risks it
   lists as approved and in scope: no more, no fewer.
2. **Every control and every test cites a rule** (`[rule:CPR-13]` or the
   `cites` list); a test may also cite a metric (`metric:$.path`). The
   builder rejects an uncited control or test.
3. **You type no numbers from the data.** Figures in memo text are
   `{{$.path}}` placeholders filled from analytics.json; a literal figure
   in prose is a failure. Sample sizes and thresholds in a sample recipe
   are the only digits you write.
4. **Samples are recipes, not lists.** You say which `analytics-full`
   file, which filter, which sort and how many; the builder draws them and
   checks every transaction exists in `spend-clean.csv`. Never copy row
   IDs or supplier names into the plan.
5. **Every rule is accounted for.** A rule in `rules.json` is cited by a
   risk, a control or a test, or listed in `rules_not_tested` with a
   reason. The builder fails on any rule that is neither.
6. **Indicator language.** Tests check controls against patterns; they
   never presume an outcome. No officer, department or supplier is
   characterised.
7. **Nothing from outside the inputs.** No audit methodology from memory
   that the rules do not support, no assumed council processes.

## Procedure

### Step 1: Confirm the gate and read the inputs

```bash
.venv/bin/python .claude/skills/audit-program/build_pack.py --gate
```

Then read the register (the approved risks' statements, evidence and
proposed focus), the decisions and comments, `rules.json`, and
`analytics.json`. Look at each `analytics-full` file you intend to sample
from with `head -3` only: you need its column names, not its rows.

### Step 2: For each approved risk, decide control, test and sample

- **Expected control:** the control the Rules require that, if working,
  would prevent or detect the pattern. Cite the rule(s). Name the owner
  where the Rules name one (the approver or the officer responsible).
- **Test step:** what fieldwork does with the sample: which documents to
  obtain, what to compare, what a pass looks like. Cite the rule and the
  metric the risk rests on. State the evidence to inspect.
- **Sample recipe:** the file, filter, sort and size. Prefer the risk's
  `sample_source` from the register. Size by score: 10 items for scores
  of 9 and above, 5 for lower, all items when fewer exist. Use the general
  procurement filter where a test splits by tag, unless the risk is about
  placements. A document or enquiry test with no transactions uses
  `{"kind": "none", "note": "..."}`.
- **PBC items:** the documents the client must provide for that test.

### Step 3: Account for every rule

Group the rules no risk, control or test cites under a reason each, e.g.
"definition or scope clause, not a control", "statutory tier; threshold
parameter null", "governance step outside the spend data". Be honest: a
rule that could be tested against the data and is not needs a reason the
auditor would accept.

### Step 4: Write `outputs/audit-plan.json`

```json
{
  "generated_at": "YYYY-MM-DD",
  "memo": {
    "purpose": ["Why this audit, in indicator language."],
    "background": ["{{$.population.rows_after_exclusions}} payments over £500 across {{$.population.months_covered}} months were tested against the Rules [metric:$.population.rows_after_exclusions]."],
    "approach": ["How the risks were identified, rated, approved and turned into tests."],
    "limitations": ["Carried from the register and the analytics caveats."]
  },
  "risks": [
    {
      "id": "R-02",
      "objective": "What the audit must conclude about this risk.",
      "controls": [
        {"id": "C-02.1", "control": "Requirements are aggregated before the procurement route is chosen.", "cites": ["rule:CPR-13", "rule:CPR-14"], "owner": "Head of Service"}
      ],
      "tests": [
        {
          "id": "T-02.1", "control": "C-02.1",
          "step": "For each sampled window, obtain the orders and quotes and confirm the requirement was treated as one purchase.",
          "evidence": "Purchase orders, quotations, contract register entry",
          "cites": ["rule:CPR-13", "metric:$.tests.split_purchases.per_threshold[1].headline_general_procurement.windows"],
          "sample": {"kind": "groups", "source": "split-purchases-windows.csv", "where": {"dominant_tag": "general_procurement", "threshold": 25000}, "order_by": "window_total", "descending": true, "n": 10, "key": "window_id", "ids_column": "row_ids"},
          "pbc": ["Purchase orders and quotations for the sampled windows"]
        }
      ]
    }
  ],
  "rules_not_tested": [
    {"reason": "definition or scope clause, not a control", "rule_ids": ["CPR-01"]}
  ]
}
```

Sample kinds: `rows` (file has `row_id`, e.g. `threshold-clustering.csv`,
`duplicates-rows.csv`), `groups` (file has a `row_ids` list, e.g.
`split-purchases-windows.csv`, `duplicates-groups.csv`), `suppliers`
(supplier-level file such as `high-value-suppliers.csv`,
`expired-notice-spend.csv`, `spend-vs-award.csv`; the builder pulls that
supplier's payments from `spend-clean.csv`, largest first, `per_group_n`
of them), `none`. Filters: `where` (equal or in a list), `where_min`,
`where_max`, `where_not_match` (a column and a regex to exclude, e.g. an
inter-authority payee pattern). `distinct_by` keeps one item per value of a
column (e.g. one window per `supplier_norm`) after sorting.
`exclude_drawn_in` lists earlier tests whose suppliers and rows this
sample must skip, so two tests do not pull the same payments.

### Step 5: Build and validate

```bash
.venv/bin/python .claude/skills/audit-program/build_pack.py
```

The builder checks the gate and the scope, resolves every citation and
placeholder, draws every sample and verifies each transaction, checks
that every control has a test and every rule is accounted for, then
writes the three documents, `outputs/samples/T-*.csv` and
`pack-figures.json` (every figure it computed, for the QA number check).
Fix the plan until it reports no failures. Never edit the rendered files:
the builder overwrites them.

### Step 6: Report

Under 300 words: risks in scope, controls and tests, sampled transactions
and their value, rules cited and not tested, and anything the challenger
or the auditor should look at first.

## Not this skill's job

- Rating or re-rating risks; the register is approved.
- Fieldwork or conclusions; the pack plans tests, it does not perform them.
- Challenging the plan or checking it; the challenger and qa-reviewer do that.

