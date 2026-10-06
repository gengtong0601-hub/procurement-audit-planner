# Source extraction notes / 原始资料提取记录

Prepared by Codex on 2026-10-06 (UTC). These files are substantive, source-grounded preparation for the assignment. They are **not evidence that Claude Code invoked `/extract-rules` or ran `findings-analyst`**, and they are not an auditor's approval. Claude Code execution and human approval must be recorded separately by the teammate.

## Files delivered

- `outputs/rules.json`: 80 testable rules, 81 explicit exclusions, four unresolved statutory parameters.
- `outputs/history.json`: 20 audit/advisory/follow-up rows, 12 sourced risk themes, the council's likelihood and impact scales, every cell of its 5×5 matrix, response bands and appetite statements.
- `docs/reference/pdf-text/`: plain and layout text for all five source PDFs, with form-feed page boundaries.
- `docs/reference/pdf-checks/`: rendered source pages for visual checking.
- `docs/reference/prepare_rules.py` and `prepare_history.py`: reproducible preparation scripts retaining the extraction decisions. Their role is source preparation, not replacing the classroom Claude execution step.

The files in `data/` were read only. No source was altered. Poppler `pdftotext` was unavailable in this environment, so extraction used `pypdf` in plain and layout modes; the rules skill permits this fallback. Page rendering used the bundled `pypdfium2`. Rotated text missing from layout mode (notably strategy Figure 4) was recovered from plain text and checked against the rendered page.

## Rule coverage and important limitations

All **141 numbered clauses** found in pages 1–10 appear exactly once in either `rules` or `excluded`. The four Appendix A rows, five Appendix B rows, six Appendix C rows and final approval paragraph are accounted for, as are the four Appendix B footnotes. IDs are sequential in document order. Rules by primary type: 41 required actions, 30 approvers, eight thresholds and one anti-avoidance rule.

The source does not print statutory amounts for goods/services, works/concessions or light-touch contracts. Those parameters remain `null`, as does the category-dependent relevant Threshold. A teammate/auditor must supply applicable dated figures and their authoritative sources for tests that need them; neither remembered amounts nor invented values were used. The **£25,000 printed process/publication boundary is not relabelled as the statutory goods/services tender Threshold**.

Important source issues are preserved in `rules.json.notes`:

1. Clause 6.15 includes VAT in contract value, but Appendix B expressly says exclusive of VAT.
2. Appendix A leaves exactly £500,000 between two bands. At £2.5 million, the row heading says “or more” but its obligation cell says “in excess of”.
3. Appendix B omits a mandatory process at or below £1,000, leaves exactly £500,000 between B2 and C, and does not settle equality at statutory Threshold boundaries.
4. Appendix C row E specifies below/greater than Threshold but leaves equality unclear.
5. The title and Appendix A retain `Part []` / `Parts []` placeholders. The PDF itself has no printed version date.

The output is an evidence map, not a legal opinion about how to resolve those inconsistencies. Public payments can reveal indicators, but cannot establish whether internal approvals, waivers, tenders or case notes complied.

Useful stable rule pointers:

| Rule | Clause | Meaning |
|---|---|---|
| CPR-13 | 6.16 | No artificial splitting or disaggregation |
| CPR-69 | App B row A | Above £1,000 and below £25,000: at least one quote |
| CPR-70 | App B row B1 | Goods/services from £25,000 up to the unnamed Threshold |
| CPR-71 | App B row B2 | Works/concession/light-touch from £25,000 to below £500,000 |
| CPR-72 | App B row C | Above £500,000 and below relevant Threshold: tender process |
| CPR-77 | App C row D | S151 approval for a permitted extension |
| CPR-78 | App C row E | Variation approvals |
| CPR-79 | App C row F | Individual social-care provider-choice reasons |

## History coverage and limitations

The completed-work documents contain 16 completed audits, three follow-ups and one advisory review. The extraction preserves nine Reasonable Assurance opinions, five Substantial Assurance opinions, two Limited Assurance opinions, one Weak opinion, two separately worded advisory/no-opinion labels, and one advisory review with no printed opinion. Relevance tags are five direct, 13 adjacent and two none; tags are extraction judgements, not new audit conclusions.

- Contract Letting (March 2025), Accounts Payable (December 2025), and Purchase of Residential and Nursing Care Provision (December 2025) have **Reasonable Assurance**.
- Personal Budgets (Direct Payments) has **Limited Assurance**. The appendix does not provide its individual findings or agreed actions.
- The two school follow-ups preserve both the original report opinion and implementation progress. A weak school opinion must not be converted into a repeated procurement finding without supporting detail.
- No supplied paper contains an individual agreed/open/overdue action list with due dates and status. `agreed_actions` is empty, with this gap stated.
- `internal-audit-plan-2025-28.pdf` is a seven-page covering report. Its appendices A–F, including the actual Appendix D plan and Appendix E anti-fraud work plan, are not included. `planned_audits` is empty; team size, target and plan approach are recorded only from the covering report.
- The Strategic/Corporate Risk Register is not supplied. Strategy p.28 explicitly says risk is reported as a Part II confidential report to the Governance Committee. No individual registered risks were invented.

The method is usable, but source discrepancies remain visible:

- Strategy §4.3 says Medium (2), while Table 1 says Medium (3); the structured scale records the table.
- Major and Medium percentage-of-budget bands overlap. The Major monetary band lacks a printed range separator; Negligible prints £17.5k without a monetary inequality. These are not silently repaired.
- Table 4 response bands are Low up to 3, Moderate 4–6, Medium–High 8–12 and Extreme 15–25.
- Figure 4 says the Corporate Risk Register includes scores **9 or above**, whereas Table 4 directs adding Extreme risks scored 15–25. Both statements are retained.
- Matrix cells use the label High where Table 4 says Medium–High. Numeric boundaries agree for all attainable products.

## Verification performed

The project quote verifier returned:

```text
PDF: 15 pages
rules.json: 80 rules, 81 excluded, 4 parameters
ALL CHECKS PASSED (80 rules, 81 excluded, 0 warning(s))
```

The history extraction builder validates every authored quote against its stated page before writing. The independent `scripts/verify_history.py` (guide implementation with the documented `pypdf` fallback) returned: **106 sourced items, 81 quotes, four documents; ALL CHECKS PASSED**.

Visual spot-checks were made on actual rendered source pages, not only extracted text:

| Source | Page | Check |
|---|---:|---|
| Contract Rules | 5 | Clause 6.16 anti-splitting wording and value definition including VAT |
| Contract Rules | 11 | Appendix A £500,000 and £2.5million band gaps and placeholder text |
| Contract Rules | 12 | Appendix B one/three/five quote or tender requirements and VAT heading |
| Q3 completed-work appendix | 1 | Accounts Payable Reasonable Assurance and Direct Payments Limited Assurance |
| Risk Management Strategy | 14 | Impact scale, Medium typo and monetary/budget-band text |
| Risk Management Strategy | 19 | RAG bands, colour shading and responses |
| Risk Management Strategy | 21 | Figure 4 score 9 or above |

These checks do not replace the human spot-check required by the guide. The teammate should independently inspect at least one prose rule, one appendix rule, one monetary boundary, one audit opinion, one scale entry and one response band.

## Claude Code handoff / 交给 teammate 的验证内容

1. In Claude Code, confirm `extract-rules` is discovered and invoke `/extract-rules`. Preserve these prepared outputs first, compare the new output and record its transcript and quote-verifier result. This confirms actual Claude Skill execution.
2. Run `findings-analyst` in Claude Code; compare source IDs, opinions, gaps and scoring method, and record its independent history-verifier result.
3. Resolve required statutory values using a dated, cited authoritative source and the auditor's decision. Do not overwrite null extraction parameters with guesses just to make a workflow green.
4. Keep the listed source inconsistencies in the risk-register header or review notes. Do not treat absent internal documents as evidence of non-compliance.
5. Auditor risk approval and final sign-off remain human tasks. No preparatory output here records either as complete.

## Draft risk preparation / 风险登记表初稿

Codex also prepared `outputs/risk-ratings.json` and ran the provided register builder after the final analytics refresh (including case-insensitive exact buyer-name matching). The resulting `outputs/risk-register.md` contains **eight draft recommendations**, not approved scope. The builder reported **eight kept, zero failures, zero warnings**. The decision table's reviewer, date, decisions and comments are all blank. `outputs/gate-evidence.json` has `ready: false` and binds the current rules, analytics, history, judgments, register and comments by hash.

The recommendations cover procurement-route proximity, aggregation, repeated payment patterns, public notice coverage, notice expiry, spend-to-award comparison, waiver/delegation records, and placement exemption records. The council's matrix determines the displayed scores and bands; judgments use source citations and computed-value placeholders. These are conservative planning judgments: no repeated-finding uplift is claimed without a matching detailed finding, and no payment population is treated as proven loss.

`prepared_sample`, `prepared_control`, `prepared_test`, `prepared_evidence` and `prepared_pbc` are **teaching/demo preparation only**. They do not authorise an audit plan. Their sample recipes were checked in memory against actual CSV headers and transaction IDs without producing a planning pack or sample files. All six transaction recipes selected existing transactions; two governance tests deliberately use document/enquiry recipes. An automated scan of drafted titles, statements, justifications and proposed focus found no supplier names. The source quotes remain unchanged even when they contain ordinary words also used by supplier names.

The teammate should have Claude Code run `risk-assessor` independently, review the rubric and citations, and compare its judgments before the human auditor records any decision. The initial baseline remains a draft, and any subsequent approved-source change requires a fresh valid gate check.
