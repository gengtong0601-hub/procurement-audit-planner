# Procurement audit risk register

**DRAFT — scope recommendations only; no auditor decisions recorded.**


Response bands use Table 4 (p.19): Extreme 15–25, Medium - High 8–12, Moderate 4–6, Low up to 3. Figure 4 (p.21) separately states Corporate Risk Register inclusion at score 9 or above. The discrepancy is preserved, not silently resolved; auditor review is required.

Risk indicators to investigate; no finding of wrongdoing is made.

## Summary

| Risk | Title | L | I | Score | Matrix label | Band | Auditor override | Proposed scope |
|---|---|---|---|---|---|---|---|---|
| R-01 | Procurement route near a printed boundary needs checking | 2 | 2 | 4 | Moderate | Moderate | no | yes |
| R-02 | Related requirements may not have been aggregated | 3 | 3 | 9 | High | Medium - High | no | yes |
| R-03 | Repeated payment patterns require invoice validation | 3 | 3 | 9 | High | Medium - High | no | yes |
| R-04 | Published notice coverage needs reconciliation to the contract register | 2 | 3 | 6 | Moderate | Moderate | no | yes |
| R-05 | Payments following published expiry need extension evidence | 2 | 3 | 6 | Moderate | Moderate | no | yes |
| R-06 | Spend-to-award differences need scope and variation review | 2 | 3 | 6 | Moderate | Moderate | no | yes |
| R-07 | Waiver and delegated-authority records require direct inspection | 1 | 3 | 3 | Low | Low | no | yes |
| R-08 | Placement exemptions need documented reasons for provider selection | 1 | 3 | 3 | Low | Low | no | yes |

## R-01: Procurement route near a printed boundary needs checking

Payments close to a published quotation boundary warrant checking the estimated total requirement and procurement route; proximity does not establish avoidance.

**Likelihood.** The general-procurement subset contains 10 payments across 7 suppliers [metric:$.tests.threshold_clustering.tiers[3].by_tag.general_procurement.rows] [metric:$.tests.threshold_clustering.tiers[3].by_tag.general_procurement.suppliers]. Likelihood is deliberately below the recurring-pattern baseline because payment proximity alone does not identify contract value or a missing quote [rule:CPR-70].

**Impact.** A missed quotation step could expose the Council to challenge, but neither a failed process nor serious consequence has been established. The provisional Minor descriptor reflects low possibility of legal challenge [history:IMPACT-2] [rule:CPR-70].

**Proposed focus.** Check aggregation, contract category, VAT basis, quotations and any authorised exemption before judging the applicable route.

**Evidence.**
- [history:IMPACT-2] risk-management-strategy-2024-27.pdf; page 14
- [metric:$.tests.threshold_clustering.tiers[3].by_tag.general_procurement.rows] 10
- [metric:$.tests.threshold_clustering.tiers[3].by_tag.general_procurement.suppliers] 7
- [rule:CPR-70] clause App B row B1, p. 12: "Invitations to quote must be sent via the Procurement Portal to at least three appropriate sources, including at least one SME* or VCSE* organisation and one local supplier ****(where appropriate and possible**). A contract notice must be published on the CDP"
- [rule:CPR-71] clause App B row B2, p. 12: "Invitations to quote must be sent via the Procurement Portal to at least three appropriate sources, including at least one SME* or VCSE* organisation and one local supplier **** (where appropriate and possible**). A contract notice must be published on the CDP"

## R-02: Related requirements may not have been aggregated

Recurring payments within the analytical window may represent related requirements that need an aggregation and procurement-route review.

**Likelihood.** The selected printed boundary has 64 general-procurement windows across 42 suppliers [metric:$.tests.split_purchases.tiers[1].headline.windows] [metric:$.tests.split_purchases.tiers[1].by_tag.general_procurement.suppliers]. This is a recurring-pattern planning indicator under the no-artificial-splitting rule; it is not evidence that these payments share a procurement requirement [rule:CPR-13].

**Impact.** If related requirements were improperly separated, lost competition or external criticism could fit the council’s provisional Medium compliance/reputation descriptors [history:IMPACT-3] [rule:CPR-13] [rule:CPR-70]. Flagged spend is not a loss estimate.

**Proposed focus.** Confirm which payments belong to a single requirement, identify legitimate recurring or distinct services, then test aggregate value and route.

**Evidence.**
- [history:IMPACT-3] risk-management-strategy-2024-27.pdf; page 14
- [metric:$.tests.split_purchases.tiers[1].by_tag.general_procurement.suppliers] 42
- [metric:$.tests.split_purchases.tiers[1].headline.windows] 64
- [rule:CPR-13] clause 6.16, p. 5: "There shall be no artificial splitting or disaggregation of a contract to avoid the application of the provisions of the Procurement Legislation and/or these Rules."
- [rule:CPR-70] clause App B row B1, p. 12: "Invitations to quote must be sent via the Procurement Portal to at least three appropriate sources, including at least one SME* or VCSE* organisation and one local supplier ****(where appropriate and possible**). A contract notice must be published on the CDP"

## R-03: Repeated payment patterns require invoice validation

Equal-value payments to the same normalised supplier at different payment-run times may reflect legitimate recurring charges or duplicates; invoice-level reconciliation is required.

**Likelihood.** There are 37 general-procurement groups involving 22 suppliers in the different-time subset [metric:$.tests.duplicates.tiers.different_time.by_tag.general_procurement.rows] [metric:$.tests.duplicates.tiers.different_time.by_tag.general_procurement.suppliers]. Recurrence supports a planning review, while the Accounts Payable Reasonable Assurance opinion and absent invoice identifiers limit any conclusion [history:AUD-15].

**Impact.** Confirmed duplicate payments could require recovery and attract external criticism, consistent with a provisional Medium descriptor [history:IMPACT-3]. The amount after the first payment is only an indicator; valid and undisputed invoice terms remain the contractual reference [rule:CPR-44].

**Proposed focus.** Compare invoice identifiers, service periods, credit notes and ledger records; keep same-timestamp batching separate from repeat payment runs.

**Evidence.**
- [history:AUD-15] audit-completed-work-2025-26-q3.pdf; page 1
- [history:IMPACT-3] risk-management-strategy-2024-27.pdf; page 14
- [metric:$.tests.duplicates.tiers.different_time.by_tag.general_procurement.rows] 37
- [metric:$.tests.duplicates.tiers.different_time.by_tag.general_procurement.suppliers] 22
- [rule:CPR-36] clause 10.7.1, p. 8: "the works, supplies /goods, services, material, matters or things to be carried out or supplied;"
- [rule:CPR-44] clause 10.7.9.1, p. 8: "any payment due from the Council is made no later than 30 days from the date on which the relevant invoice is regarded as valid and undisputed; and"

## R-04: Published notice coverage needs reconciliation to the contract register

General-procurement suppliers above the printed publication boundary without an exact active notice match require contract-register reconciliation; missing notices do not establish off-contract spend.

**Likelihood.** The proxy reports 191 general-procurement suppliers without an exact match [metric:$.tests.off_contract.headline.count]. Likelihood is reduced below the recurring-pattern baseline because public notices are incomplete and the Council contract register is not supplied [metric:$.contracts.register_present]. Near matches, legacy awards and lawful exemptions require review [rule:CPR-08] [history:AUD-01].

**Impact.** If award recording or contract documentation were missing, external scrutiny and a reasonable possibility of legal challenge could fit the provisional Medium descriptor [history:IMPACT-3] [rule:CPR-34]. The unmatched payment population is not evidence of such a failure or financial loss.

**Proposed focus.** Obtain the actual register and contracts, confirm near matches, then identify awards and publication duties by category and date.

**Evidence.**
- [history:AUD-01] audit-completed-work-2024-25-annual.pdf; page 1
- [history:IMPACT-3] risk-management-strategy-2024-27.pdf; page 14
- [metric:$.contracts.register_present] 0
- [metric:$.tests.off_contract.headline.count] 191
- [rule:CPR-08] clause 5.2.1, p. 3: "A register of contracts, including those in progress and those awarded, with key information such as the contract value, duration and supplier."
- [rule:CPR-34] clause 10.4, p. 8: "The relevant Service Director must formally notify the Service Lead f or Commissioning and Procurement (or nominated officer) of the award of all contracts for the purpose of it being recorded on the Council Contract Register."

## R-05: Payments following published expiry need extension evidence

Payments after all exactly matched published notices have ended warrant checking whether a valid renewal, replacement or authorised extension covers the service.

**Likelihood.** The analysis identifies 7 suppliers whose matched notices ended before the spend window [metric:$.tests.expired_notice_spend.count]. The rating is below the recurring-pattern baseline because an unobserved newer contract may exist; approval remains an internal-record question [rule:CPR-77].

**Impact.** An unsupported extension could weaken contract enforceability or attract legal challenge; this is provisionally aligned to the Medium compliance descriptor [history:IMPACT-3] [rule:CPR-77]. Notice expiry itself does not establish an expired contract.

**Proposed focus.** Inspect original extension clauses, the current contract and documented approval before treating notice dates as contractual expiry.

**Evidence.**
- [history:IMPACT-3] risk-management-strategy-2024-27.pdf; page 14
- [metric:$.tests.expired_notice_spend.count] 7
- [rule:CPR-77] clause App C row D, p. 14: "Approval of the S151 Officer"

## R-06: Spend-to-award differences need scope and variation review

Annualised payment estimates above the annual rate implied by a matched award warrant reconciling scope, timing and any approved variation.

**Likelihood.** There are 8 eligible supplier indicators [metric:$.tests.spend_vs_award.count]. Likelihood is reduced below the recurring-pattern baseline because annualisation, award estimates and multi-contract scope may explain the difference; this does not establish a variation [rule:CPR-78].

**Impact.** If a material change lacked the prescribed approval, it could raise a reasonable possibility of legal challenge under the Medium descriptor [history:IMPACT-3] [rule:CPR-78]. No estimate of contractual overspend or loss is asserted.

**Proposed focus.** Reconcile payments to contract scope, duration and award value, then verify any modification and its required approval.

**Evidence.**
- [history:IMPACT-3] risk-management-strategy-2024-27.pdf; page 14
- [metric:$.tests.spend_vs_award.count] 8
- [rule:CPR-78] clause App C row E, p. 14: "For contract value below the Threshold prior written approval from the Monitoring Officer and S151 Officer is required. For contract value greater than the Threshold, approval of the relevant board, following the submission of an extension report to the relevant board with recommendation from Monitoring Officer and S151 Officer"

## R-07: Waiver and delegated-authority records require direct inspection

Public payment and notice data cannot establish whether exceptions were requested in advance, justified and approved by the correct delegated authority.

**Likelihood.** This is a rule-only governance gap without current evidence of failed approvals [rule:CPR-21] [rule:CPR-25] [rule:CPR-27]. Contract Letting previously received Reasonable Assurance and the supplied appendix contains no detailed finding to support an adverse uplift [history:AUD-01].

**Impact.** An unauthorised waiver could expose the procurement process to external criticism or legal challenge, provisionally matching the Medium descriptor [history:IMPACT-3] [rule:CPR-27]. Consequence information is not available.

**Proposed focus.** Request the waiver register and delegation records, establish the population, and inspect advance timing, reasons and the relevant approval trail.

**Evidence.**
- [history:AUD-01] audit-completed-work-2024-25-annual.pdf; page 1
- [history:IMPACT-3] risk-management-strategy-2024-27.pdf; page 14
- [rule:CPR-05] clause 4.4, p. 3: "Where a Service Director does not have delegated authority to enter into a contract, approval in accordance with Appendix A is required before the contract can be awarded."
- [rule:CPR-21] clause 7.3, p. 6: "Only the Monitoring Officer and/or the S.151 Officer may grant a waiver or an exception to these Rules, subject to exception v alues and delegation thresholds detailed in these Rules and/or elsewhere in the Constitution. An officer who seeks a waiver of these Rules shall do so only in advance and only in exceptional circumstances."
- [rule:CPR-25] clause 7.5.1, p. 6: "be fully documented;"
- [rule:CPR-27] clause 7.5.3, p. 7: "be subject to approval by the S.151 Officer who shall record they have considered the reasons for the waiver and that they are satisfied that the circumstances justifying the waiver are genuinely exceptional (applications for wa ivers which are a result of poor contract planning will rarely be considered genuinely exceptional);"

## R-08: Placement exemptions need documented reasons for provider selection

Care and education placement payments need a separate review of exemption eligibility and documented provider-selection reasons; routine recurrence must not be treated as procurement splitting.

**Likelihood.** The population includes 5,839 tagged placement payments [metric:$.population.tags.care_or_education_placement.rows], but tags do not prove exemption status or missing records. The case-note requirement is therefore rated as a rule-only gap [rule:CPR-79]. Residential and nursing care had Reasonable Assurance; the separate Direct Payments Limited Assurance opinion supplies no matching detailed finding, so no repeat uplift is applied [history:AUD-18] [history:AUD-16].

**Impact.** If provider-selection reasons were absent, the decision could attract external scrutiny consistent with the Medium reputation descriptor [history:IMPACT-3] [rule:CPR-79]. No deficient care, personal harm or financial loss is inferred.

**Proposed focus.** Determine actual exemption category and inspect provider-selection reasons and applicable approval, with appropriate handling of personal information.

**Evidence.**
- [history:AUD-16] audit-completed-work-2025-26-q3.pdf; page 1
- [history:AUD-18] audit-completed-work-2025-26-q3.pdf; page 1
- [history:IMPACT-3] risk-management-strategy-2024-27.pdf; page 14
- [metric:$.population.tags.care_or_education_placement.rows] 5,839
- [rule:CPR-79] clause App C row F, p. 15: "Service Directors must ensure that a record of the reasons for the choice of provider is maintained on the individual’s case notes."

## Excluded

- Theme: The rulebook leaves statutory parameters null; category, applicable legislation and authoritative dated amounts require auditor input before that conclusion can be tested.
- Theme: The supplied appendices contain adverse opinions but no matching recurring procurement issue with detailed findings; a school follow-up or Direct Payments opinion alone does not prove the same procurement failure.
- Theme: No action list with due dates and status is supplied; missing actions are recorded as a source gap rather than invented.
- Theme: The data supports planning indicators only; no accusation or misconduct conclusion is supported.

## Auditor decisions

No decisions recorded; the auditor must complete auditor-comments.md.
