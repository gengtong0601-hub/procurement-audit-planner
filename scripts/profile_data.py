#!/usr/bin/env python3
"""Write a compact, reproducible source profile without exposing full datasets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def profile(full: Path, analytics: Path, output: Path) -> None:
    log = json.loads((full / "cleaning-log.json").read_text())
    result = json.loads(analytics.read_text())
    c = result["contracts"]
    p = result["population"]
    lines = ["# Data profile and analytical boundaries", "",
             "Prepared by Codex from the supplied guide data. This records reproducible local preparation, not execution or verification by Claude Code. Human risk approval remains pending.", "",
             "## Source population", "",
             "The input files are read-only. Payment dates come from the `Date` column, not the workbook period label. Header locations and source hashes are recorded in `outputs/analytics-full/cleaning-log.json`.", "",
             "| Workbook | Excel header row | Source rows | Blank expenditure categories |",
             "| --- | ---: | ---: | ---: |"]
    for file in log["files"]:
        lines.append(f"| {file['file']} | {file['header_row']} | {file['rows']:,} | {file['blank_expenditure_category']:,} |")
    lines += ["", f"Actual payment range: **{p['date_min']} to {p['date_max']}**. Observed calendar months: **{p['months_covered']}**. Annualisation is `total × (12 / months_covered)`, a factor of **{p['annualisation_factor']:g}**, and every such value is labelled an **annualised estimate**.", "",
              f"Raw population: **{p['rows_raw']:,} rows**. After exclusions: **{p['rows_after_exclusions']:,} rows**, **£{p['total_gbp']:,.2f}**. All sums and comparisons use integer pence or Decimal; displayed GBP values do not drive comparisons.", "",
              "| Exclusion | Rows | GBP | Reason |", "| --- | ---: | ---: | --- |"]
    for name, item in p["excluded"].items():
        lines.append(f"| {name} | {item['rows']:,} | £{item['gbp']:,.2f} | {item['reason']} |")
    lines += ["", "Excluded rows remain in `spend-excluded.csv`, with their original workbook row identifiers and exclusion reasons. Grants and Transfer Payment narratives are retained. Tagging follows the guide's fixed expressions with first-match precedence. Missing expenditure category is allowed; missing supplier, date or amount, negative amounts, malformed columns and non-penny amounts stop execution.", "",
              "## Contract notices", "",
              f"The export contains **{c['rows_in_file']:,} rows**; **{c['rows_for_council']:,}** remain under an exact buyer-identity filter after case and whitespace normalisation. This retains **{c['normalised_buyer_variants_kept']:,}** spelling variants of the two allowed identities. Packed fields expand to **{c['notice_supplier_pairs']:,} notice–supplier pairs**, representing **{c['distinct_suppliers']:,} distinct normalised suppliers**. Zero-value awards are retained (**{c['zero_value_awards']:,} notices**).",
              "", f"End-date-active notices: **{c['active_in_window']:,}**; ended before the spend window: **{c['ended_before_window']:,}**. Blank end dates remain eligible. A notice starting after the whole spend window cannot establish coverage and is excluded from matching, while retained in the cleaned notices for review.", "",
              f"Council contract register supplied: **{str(c['register_present']).lower()}**.", "", c["caveat"], "", "Warnings recorded by the scripts:", ""]
    lines.extend(f"- {warning}" for warning in c["warnings"] + p["warnings"])
    lines += ["", "## Implemented indicators", "", "| Indicator | Count | Amount (GBP) | Interpretation |", "| --- | ---: | ---: | --- |"]
    meanings = {"threshold_clustering": "Distinct payments in below-trigger bands; tiers include comparator and baseline bands.",
                "split_purchases": "General-procurement windows across competition thresholds; amounts can overlap across thresholds.",
                "high_value_suppliers": "Suppliers above the lowest sourced competition threshold on an annualised estimate basis.",
                "duplicates": "Groups sharing supplier and penny amount within seven days; GBP is value beyond the first instance.",
                "off_contract": "Above-publication-floor suppliers without an exact active notice/register match; near matches remain separate candidates.",
                "expired_notice_spend": "Exact-match suppliers whose every published notice ended before the spend window.",
                "spend_vs_award": "Annualised estimate at least 1.25 times the annual award rate for exactly one active, single-supplier, positive-value notice."}
    for name, test in result["tests"].items():
        if test.get("skipped"):
            lines.append(f"| {name} | Skipped | — | {test['reason']} |")
        else:
            lines.append(f"| {name} | {test['count']:,} | £{test['gbp']:,.2f} | {meanings[name]} |")
    lines += ["", "The figures above are indicators for investigation, not confirmed issues or allegations. Counts across tests and thresholds must not be added as if they represent unique transactions. The placement tag is reported separately because recurring care and education fees are often legitimate.", "",
              "## Deliberate and reviewable method choices", "",
              "- Spend text dates use explicit month/day/year formats; notice dates use day/month/year, and publication timestamps use ISO. Calendar dates drive windows; original millisecond payment-run timestamps determine duplicate tiers.",
              "- Numeric rule thresholds and their boundary inclusivity are extracted from `rules.json`. A lower bound that excludes the threshold itself triggers at the next penny. Explicit competition classification can distinguish tender-publication rules from rules requiring competition.",
              "- Split windows span `[anchor date, anchor date + 30 days)`. All same-day payments enter together. Overlapping candidates are resolved per supplier and threshold by highest total first, then earliest anchor, discarding shared row sets. Distinct non-overlapping windows remain.",
              "- Duplicate windows use a calendar difference of at most seven days. Non-overlapping groups are selected by highest total, then earliest anchor. A group containing differing timestamps is classified as `different_time`; an identical-timestamp group is `same_timestamp`. The tiers never double count a row.",
              "- Near-name matches use the guide's ratio and distinctive-token rules. They never count as exact matches. The spend source has no Companies House identifier; the parser preserves identifiers on notices and the matcher supports exact identifiers when a future source supplies them.",
              "- Notice end-date coverage follows the guide. One additional temporal guard prevents a contract starting after the entire spend period from matching earlier payments. Notices that start within the period remain a supplier-level proxy; this does not establish every payment's contract coverage.",
              "- Whole-term award annualisation uses inclusive contract days divided by 365.25. Zero awards, multiple active notices, multi-supplier notices, and missing durations cannot support this ratio and are counted as exclusions. Award values can be estimates or maxima.",
              "- Buyer matching accepts exactly `West Berkshire Council` and `West Berkshire` after stripping/collapsing whitespace and casefolding. Consequently `WEST BERKSHIRE COUNCIL` is the same buyer, as in the guide Setup replay. This deliberately improves upon a literal case-sensitive string comparison and prevents avoidable missing-notice signals. No substring or fuzzy buyer matching is allowed; other councils and notices merely mentioning West Berkshire are excluded. Original spellings and counts remain in the cleaning log.",
              "- Only the supplied statutory parameters may enable statutory tiers. Null values are retained as null and the dependent tiers are marked skipped. No legal threshold is guessed.",
              "", "## Verification and reproducibility", "", "Run from the repository root:", "", "```sh", "python scripts/clean.py", "python scripts/analyse.py", "python scripts/selfcheck.py", "python scripts/profile_data.py", "python -m unittest discover -s tests -p test_analytics.py -v", "```", "",
              "All source paths and output directories can be overridden using `--data`, `--output`, `--full`, `--rules`, or `--analytics` as shown by each command's `--help`. The optional council register uses a documented mapping to `supplier_name,start_date,end_date,value_gbp` with ISO dates and optional `company_number`; unknown layouts stop until an explicit mapping is supplied.", "",
              "The independent self-check reads the cleaned CSVs directly and re-derives one flagged item per available indicator. Its full source-row lists and arithmetic are in `outputs/analytics-full/selfcheck.json`. Edge-case tests cover date ambiguity, input rejection, exact penny arithmetic, packed suppliers, zero awards, missing notices, threshold boundaries, overlap handling, match classes and award eligibility.", "",
              "Claude Code must still run the spend-analyst itself, inspect the near-match list and mapping warnings, reproduce these outputs, and report its own checks. A successful Python test run does not demonstrate Claude sub-agent invocation, memory behavior, skill loading, inter-agent messages, or human approval.", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", type=Path, default=Path("outputs/analytics-full"))
    parser.add_argument("--analytics", type=Path, default=Path("outputs/analytics.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/DATA_PROFILE.md"))
    args = parser.parse_args()
    profile(args.full, args.analytics, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
