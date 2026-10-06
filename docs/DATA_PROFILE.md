# Data profile and analytical boundaries

Prepared by Codex from the supplied guide data. This records reproducible local preparation, not execution or verification by Claude Code. Human risk approval remains pending.

## Source population

The input files are read-only. Payment dates come from the `Date` column, not the workbook period label. Header locations and source hashes are recorded in `outputs/analytics-full/cleaning-log.json`.

| Workbook | Excel header row | Source rows | Blank expenditure categories |
| --- | ---: | ---: | ---: |
| Over500_2026_P02_-_published.xlsx | 1 | 2,892 | 28 |
| Over500_2026_P03_-_published.xlsx | 2 | 3,547 | 29 |
| Over500_2026_P04_-_published.xlsx | 2 | 4,168 | 30 |

Actual payment range: **2026-05-01 to 2026-07-31**. Observed calendar months: **3**. Annualisation is `total × (12 / months_covered)`, a factor of **4**, and every such value is labelled an **annualised estimate**.

Raw population: **10,607 rows**. After exclusions: **8,534 rows**, **£66,778,104.78**. All sums and comparisons use integer pence or Decimal; displayed GBP values do not drive comparisons.

| Exclusion | Rows | GBP | Reason |
| --- | ---: | ---: | --- |
| redacted_supplier | 2,015 | £2,746,746.71 | Redacted combines unrelated payees; excluded from supplier-level tests. |
| pension_statutory | 12 | £9,235,814.93 | Narrative matches LGPS|PENSION|SUPERANNUATION; statutory pension indicator. |
| inter_authority | 46 | £1,666,587.84 | Public-body supplier or JOINT ARRANGEMENTS, except Private Contractors narrative. |

Excluded rows remain in `spend-excluded.csv`, with their original workbook row identifiers and exclusion reasons. Grants and Transfer Payment narratives are retained. Tagging follows the guide's fixed expressions with first-match precedence. Missing expenditure category is allowed; missing supplier, date or amount, negative amounts, malformed columns and non-penny amounts stop execution.

## Contract notices

The export contains **150 rows**; **141** remain under an exact buyer-identity filter after case and whitespace normalisation. This retains **6** spelling variants of the two allowed identities. Packed fields expand to **210 notice–supplier pairs**, representing **143 distinct normalised suppliers**. Zero-value awards are retained (**7 notices**).

End-date-active notices: **62**; ended before the spend window: **79**. Blank end dates remain eligible. A notice starting after the whole spend window cannot establish coverage and is excluded from matching, while retained in the cleaned notices for review.

Council contract register supplied: **false**.

contracts.csv holds published *notices*, not a contract register. It holds awards published on Contracts Finder in roughly the last five years. A contract awarded earlier (e.g. long-running waste or highways contracts), one advertised only on Find a Tender, a framework call-off recorded under another buyer, or an exempt placement will have no notice here. "No notice found" is therefore an indicator to check against the council's contract register, never evidence of off-contract spend.

Warnings recorded by the scripts:

- Some end-date-active notices start after the spend window. Listed for traceability; these future notices are excluded from matching and spend-vs-award.

## Implemented indicators

| Indicator | Count | Amount (GBP) | Interpretation |
| --- | ---: | ---: | --- |
| threshold_clustering | 732 | £3,138,493.47 | Distinct payments in below-trigger bands; tiers include comparator and baseline bands. |
| split_purchases | 175 | £8,869,866.31 | General-procurement windows across competition thresholds; amounts can overlap across thresholds. |
| high_value_suppliers | 1,083 | £66,778,104.78 | Suppliers above the lowest sourced competition threshold on an annualised estimate basis. |
| duplicates | 698 | £5,769,577.08 | Groups sharing supplier and penny amount within seven days; GBP is value beyond the first instance. |
| off_contract | 634 | £62,786,051.47 | Above-publication-floor suppliers without an exact active notice/register match; near matches remain separate candidates. |
| expired_notice_spend | 7 | £190,366.92 | Exact-match suppliers whose every published notice ended before the spend window. |
| spend_vs_award | 8 | £736,650.97 | Annualised estimate at least 1.25 times the annual award rate for exactly one active, single-supplier, positive-value notice. |

The figures above are indicators for investigation, not confirmed issues or allegations. Counts across tests and thresholds must not be added as if they represent unique transactions. The placement tag is reported separately because recurring care and education fees are often legitimate.

## Deliberate and reviewable method choices

- Spend text dates use explicit month/day/year formats; notice dates use day/month/year, and publication timestamps use ISO. Calendar dates drive windows; original millisecond payment-run timestamps determine duplicate tiers.
- Numeric rule thresholds and their boundary inclusivity are extracted from `rules.json`. A lower bound that excludes the threshold itself triggers at the next penny. Explicit competition classification can distinguish tender-publication rules from rules requiring competition.
- Split windows span `[anchor date, anchor date + 30 days)`. All same-day payments enter together. Overlapping candidates are resolved per supplier and threshold by highest total first, then earliest anchor, discarding shared row sets. Distinct non-overlapping windows remain.
- Duplicate windows use a calendar difference of at most seven days. Non-overlapping groups are selected by highest total, then earliest anchor. A group containing differing timestamps is classified as `different_time`; an identical-timestamp group is `same_timestamp`. The tiers never double count a row.
- Near-name matches use the guide's ratio and distinctive-token rules. They never count as exact matches. The spend source has no Companies House identifier; the parser preserves identifiers on notices and the matcher supports exact identifiers when a future source supplies them.
- Notice end-date coverage follows the guide. One additional temporal guard prevents a contract starting after the entire spend period from matching earlier payments. Notices that start within the period remain a supplier-level proxy; this does not establish every payment's contract coverage.
- Whole-term award annualisation uses inclusive contract days divided by 365.25. Zero awards, multiple active notices, multi-supplier notices, and missing durations cannot support this ratio and are counted as exclusions. Award values can be estimates or maxima.
- Buyer matching accepts exactly `West Berkshire Council` and `West Berkshire` after stripping/collapsing whitespace and casefolding. Consequently `WEST BERKSHIRE COUNCIL` is the same buyer, as in the guide Setup replay. This deliberately improves upon a literal case-sensitive string comparison and prevents avoidable missing-notice signals. No substring or fuzzy buyer matching is allowed; other councils and notices merely mentioning West Berkshire are excluded. Original spellings and counts remain in the cleaning log.
- Only the supplied statutory parameters may enable statutory tiers. Null values are retained as null and the dependent tiers are marked skipped. No legal threshold is guessed.

## Verification and reproducibility

Run from the repository root:

```sh
python scripts/clean.py
python scripts/analyse.py
python scripts/selfcheck.py
python scripts/profile_data.py
python -m unittest discover -s tests -p test_analytics.py -v
```

All source paths and output directories can be overridden using `--data`, `--output`, `--full`, `--rules`, or `--analytics` as shown by each command's `--help`. The optional council register uses a documented mapping to `supplier_name,start_date,end_date,value_gbp` with ISO dates and optional `company_number`; unknown layouts stop until an explicit mapping is supplied.

The independent self-check reads the cleaned CSVs directly and re-derives one flagged item per available indicator. Its full source-row lists and arithmetic are in `outputs/analytics-full/selfcheck.json`. Edge-case tests cover date ambiguity, input rejection, exact penny arithmetic, packed suppliers, zero awards, missing notices, threshold boundaries, overlap handling, match classes and award eligibility.

Claude Code must still run the spend-analyst itself, inspect the near-match list and mapping warnings, reproduce these outputs, and report its own checks. A successful Python test run does not demonstrate Claude sub-agent invocation, memory behavior, skill loading, inter-agent messages, or human approval.
