# Real council data contract

Create `CASE/inputs/` and preserve source provenance (URL, download date, any preprocessing). The current adapter expects the canonical headers below. If publisher columns differ, add and test an explicit adapter retaining original filename, sheet and Excel row. Never describe rewritten workbook rows as original publisher references.

```json
{
  "council": "Council name",
  "currency": "GBP",
  "period_start": "2025-01-01",
  "period_end": "2025-12-31",
  "contract_rules": "contract-rules.pdf",
  "spend": [{"file": "spend.xlsx", "sheet": "Payments"}],
  "contracts": "contracts.csv",
  "committee_papers": ["committee-papers.pdf"],
  "auditor_days": 15,
  "synthetic": false
}
```

Save this as `manifest.json`. Paths must stay inside `inputs/`; every declared source is required.

## Spend workbook

First-row headers: `transaction_id`, `supplier`, `department`, `category`, `payment_date`, `amount`, `invoice_number`, `contract_id`.

IDs must be nonblank and unique across workbooks. Supplier/department/category are nonblank. Dates must be Excel dates or ISO `YYYY-MM-DD`, inside the audit period. Amounts are finite numbers with at most two decimals; credits and zero rows remain in the population. Invoice and contract IDs may be blank; blank invoices do not enter duplicate matching.

Every nonempty row is validated. Bad records stop processing rather than being silently skipped. Formula cells require cached values. Up to 100,000 rows per case are supported, assuming one currency and consistent amount/category meanings. Original Excel row numbers are preserved.

## Contracts CSV

UTF-8 headers: `contract_id,supplier,category,start_date,end_date`. All fields are required; IDs are unique; dates are ISO. Matching uses exact ID, supplier and category plus inclusive validity dates. An incomplete public register is an alternative explanation for unmatched payments, not proof of a breach.

## PDFs and reviewed proposals

Every PDF page must have extractable text. Empty/image-only pages require verified OCR before processing. `page` is a one-based physical PDF page; quote verification normalizes whitespace only.

Rule/history proposals follow `procurement_audit/models.py`. Generate examples with the demo command. A rule has `RULE-NNN`, clause, requirement, source_file, page, quote, indicator and optional threshold. Threshold values must appear in the verified quote. Unsupported testable obligations use `manual_review`; do not invent a detector or ignore the obligation.

Historical items have `HIST-NNN`, category (`audit_opinion`, `open_action`, `registered_risk`, `coverage`), description, rule_ids and source citation. Every paper needs a quoted coverage entry. Empty history is not assumed to mean no issues. Describe status as of the historical document, not as verified current fact.

Use reviewed `rule-candidates.json` / `history-candidates.json`, or configure `--llm`. Both routes verify source quotations. Quote checks do not establish extraction completeness or correct interpretation; human review is necessary.

## Algorithms and explicit assumptions

| Indicator | Computed criterion |
|---|---|
| Threshold clustering | Payment in `[90% × threshold, threshold)`; near-threshold candidates, not statistical significance |
| Split purchases | Same supplier/department/category; two or more positive below-threshold payments within an inclusive 30-day window, total at least the threshold |
| Off-contract | No exact supplier/category/ID/date match in the supplied register |
| Duplicates | Same supplier, nonblank invoice and positive amount; all group members included |

Payments may differ from commitments; matching is exact after whitespace trimming. Each indicator sums absolute values of unique matched rows. Indicator values overlap and must not be added as losses. Net spend includes credits; gross spend sums absolute values. Python `Decimal` computes all figures.

For indicator risks, likelihood uses flagged-row share; impact uses flagged gross-value share. Shares below 1%, 5%, 10%, 25%, and at least 25% map to scores 1–5. Overall score is likelihood × impact. Manual/history-only risks have a disclosed provisional 3 × 3 judgment for human approval/amendment. These are illustrative planning conventions, not legal requirements or calibrated probabilities.

Samples contain up to ten largest absolute-value flagged rows, ties by transaction ID. Procedures request complete related groups for split/duplicate follow-up. Manual risks have documentary evidence rather than invented payment rows. Samples are judgmental and support no statistical extrapolation.
