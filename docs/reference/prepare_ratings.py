"""Prepare cited, unapproved planning judgments; never fabricate human decisions."""
import json
from pathlib import Path
B=Path(__file__).resolve().parents[2]
a=json.loads((B/'outputs/analytics.json').read_text())
rules=json.loads((B/'outputs/rules.json').read_text())
# Resolve positions from source values instead of assuming a stable tier ordering.
quote_band=next(r['threshold_low'] for r in rules['rules'] if r['clause']=='App B row B1')
cluster_i=next(i for i,t in enumerate(a['tests']['threshold_clustering']['tiers']) if t['threshold']==quote_band)
split_i=next(i for i,t in enumerate(a['tests']['split_purchases']['tiers']) if t['threshold']==quote_band)
c=f'$.tests.threshold_clustering.tiers[{cluster_i}]'
s=f'$.tests.split_purchases.tiers[{split_i}]'
def ph(path):return '{{'+path+'}}'
def metric(path):return '[metric:'+path+']'
risks=[]
def add(title,statement,likelihood,lwhy,impact,iwhy,focus,source,sample,control,test,evidence,pbc):
 risks.append(dict(id=f'R-{len(risks)+1:02}',title=title,statement=statement,likelihood=dict(score=likelihood,justification=lwhy),impact=dict(score=impact,justification=iwhy),proposed_focus=focus,recommend_in_scope=True,sample_source=source,prepared_sample=sample,prepared_control=control,prepared_test=test,prepared_evidence=evidence,prepared_pbc=pbc))
add('Procurement route near a printed boundary needs checking',
 'Payments close to a published quotation boundary warrant checking the estimated total requirement and procurement route; proximity does not establish avoidance.',
 2,'The general-procurement subset contains '+ph(c+'.by_tag.general_procurement.rows')+' payments across '+ph(c+'.by_tag.general_procurement.suppliers')+' suppliers '+metric(c+'.by_tag.general_procurement.rows')+' '+metric(c+'.by_tag.general_procurement.suppliers')+'. Likelihood is deliberately below the recurring-pattern baseline because payment proximity alone does not identify contract value or a missing quote [rule:CPR-70].',
 2,'A missed quotation step could expose the Council to challenge, but neither a failed process nor serious consequence has been established. The provisional Minor descriptor reflects low possibility of legal challenge [history:IMPACT-2] [rule:CPR-70].',
 'Check aggregation, contract category, VAT basis, quotations and any authorised exemption before judging the applicable route.',
 'threshold-clustering.csv',dict(kind='rows',source='threshold-clustering.csv',where={'tag':'general_procurement','threshold':quote_band},order_by='amount_pence',descending=True,n=5,distinct_by='supplier_norm'),
 'The documented total requirement determines the quotation route and invitations are retained [rule:CPR-70] [rule:CPR-71].',
 'For each selected payment obtain the purchase order, requirement estimate and quotation file; establish contract category and total commitment, reconcile the VAT treatment, and inspect evidence of the applicable invitations or approved exemption. Do not treat payment value alone as contract value.',
 'Purchase orders, contract value estimates, quotation records, exemption approvals and VAT basis.',
 ['Requirement estimate and purchase order for each selected payment','Quotation invitations, evaluation records and any approved exemption','Documented resolution of the rulebook VAT and boundary ambiguities'])
add('Related requirements may not have been aggregated',
 'Recurring payments within the analytical window may represent related requirements that need an aggregation and procurement-route review.',
 3,'The selected printed boundary has '+ph(s+'.headline.windows')+' general-procurement windows across '+ph(s+'.by_tag.general_procurement.suppliers')+' suppliers '+metric(s+'.headline.windows')+' '+metric(s+'.by_tag.general_procurement.suppliers')+'. This is a recurring-pattern planning indicator under the no-artificial-splitting rule; it is not evidence that these payments share a procurement requirement [rule:CPR-13].',
 3,'If related requirements were improperly separated, lost competition or external criticism could fit the council’s provisional Medium compliance/reputation descriptors [history:IMPACT-3] [rule:CPR-13] [rule:CPR-70]. Flagged spend is not a loss estimate.',
 'Confirm which payments belong to a single requirement, identify legitimate recurring or distinct services, then test aggregate value and route.',
 'split-purchases.csv',dict(kind='groups',source='split-purchases.csv',where={'tag':'general_procurement','threshold':quote_band},order_by='total_gbp',descending=True,n=10,distinct_by='supplier_norm',key='window_id',ids_column='row_ids'),
 'Related requirements are assessed together and are not artificially split to avoid the applicable process [rule:CPR-13] [rule:CPR-70].',
 'Inspect the orders, service periods, requisitions and contract file for every selected window; determine whether the payments concern one requirement or separate legitimate needs, then compare documented aggregate value with the procurement route and approvals.',
 'Requisitions, orders, service descriptions, contract files, quote/tender evidence and approval records.',
 ['Requisitions and purchase orders for all payments in each sampled window','Service-period and requirement descriptions explaining recurrence','Contract, quotation or tender file and any waiver approval'])
add('Repeated payment patterns require invoice validation',
 'Equal-value payments to the same normalised supplier at different payment-run times may reflect legitimate recurring charges or duplicates; invoice-level reconciliation is required.',
 3,'There are '+ph('$.tests.duplicates.tiers.different_time.by_tag.general_procurement.rows')+' general-procurement groups involving '+ph('$.tests.duplicates.tiers.different_time.by_tag.general_procurement.suppliers')+' suppliers in the different-time subset [metric:$.tests.duplicates.tiers.different_time.by_tag.general_procurement.rows] [metric:$.tests.duplicates.tiers.different_time.by_tag.general_procurement.suppliers]. Recurrence supports a planning review, while the Accounts Payable Reasonable Assurance opinion and absent invoice identifiers limit any conclusion [history:AUD-15].',
 3,'Confirmed duplicate payments could require recovery and attract external criticism, consistent with a provisional Medium descriptor [history:IMPACT-3]. The amount after the first payment is only an indicator; valid and undisputed invoice terms remain the contractual reference [rule:CPR-44].',
 'Compare invoice identifiers, service periods, credit notes and ledger records; keep same-timestamp batching separate from repeat payment runs.',
 'duplicates.csv',dict(kind='groups',source='duplicates.csv',where={'tag':'general_procurement','tier':'different_time'},order_by='excess_gbp',descending=True,n=10,distinct_by='supplier_norm',key='group_id',ids_column='row_ids'),
 'Contract payment terms relate to valid, undisputed invoices; sampled payments are reconciled to the underlying obligation before concluding that a repeat is a duplicate [rule:CPR-44] [rule:CPR-36].',
 'Reconcile every payment in each selected group to invoice number, service period, purchase order, contract payment terms and credits; classify distinct legitimate charges separately from any repeated settlement of the same obligation and request management explanation.',
 'Invoices, supplier ledger, credit notes, purchase orders, delivery or service confirmation and contract payment terms.',
 ['Underlying invoices and ledger entries for the sampled groups','Related credit notes and any recovery records','Contract payment terms and evidence supporting the billed service periods'])
add('Published notice coverage needs reconciliation to the contract register',
 'General-procurement suppliers above the printed publication boundary without an exact active notice match require contract-register reconciliation; missing notices do not establish off-contract spend.',
 2,'The proxy reports '+ph('$.tests.off_contract.headline.count')+' general-procurement suppliers without an exact match [metric:$.tests.off_contract.headline.count]. Likelihood is reduced below the recurring-pattern baseline because public notices are incomplete and the Council contract register is not supplied [metric:$.contracts.register_present]. Near matches, legacy awards and lawful exemptions require review [rule:CPR-08] [history:AUD-01].',
 3,'If award recording or contract documentation were missing, external scrutiny and a reasonable possibility of legal challenge could fit the provisional Medium descriptor [history:IMPACT-3] [rule:CPR-34]. The unmatched payment population is not evidence of such a failure or financial loss.',
 'Obtain the actual register and contracts, confirm near matches, then identify awards and publication duties by category and date.',
 'off-contract.csv',dict(kind='suppliers',source='off-contract.csv',where={'dominant_tag':'general_procurement','match_class':['none','near_ratio','near_contain']},order_by='total_gbp',descending=True,n=5,per_group_n=2),
 'All awards are notified for recording on the Council Contract Register and required contract information is published [rule:CPR-34] [rule:CPR-08].',
 'Reconcile each selected supplier and sampled payment to the Council register and signed contract; confirm any near-name match, legacy award, framework call-off or exemption, and inspect required award notification and publication evidence. Record unresolved coverage as an evidence gap.',
 'Council contract register, signed contracts, award notifications, framework call-off records and published notice identifiers.',
 ['Current Council contract register and award notifications','Signed contracts or call-off records for sampled payments','Explanation and supporting records for unmatched or near-matched suppliers'])
add('Payments following published expiry need extension evidence',
 'Payments after all exactly matched published notices have ended warrant checking whether a valid renewal, replacement or authorised extension covers the service.',
 2,'The analysis identifies '+ph('$.tests.expired_notice_spend.count')+' suppliers whose matched notices ended before the spend window [metric:$.tests.expired_notice_spend.count]. The rating is below the recurring-pattern baseline because an unobserved newer contract may exist; approval remains an internal-record question [rule:CPR-77].',
 3,'An unsupported extension could weaken contract enforceability or attract legal challenge; this is provisionally aligned to the Medium compliance descriptor [history:IMPACT-3] [rule:CPR-77]. Notice expiry itself does not establish an expired contract.',
 'Inspect original extension clauses, the current contract and documented approval before treating notice dates as contractual expiry.',
 'expired-notice-spend.csv',dict(kind='suppliers',source='expired-notice-spend.csv',where={'dominant_tag':'general_procurement'},order_by='total_gbp',descending=True,n=5,per_group_n=2),
 'A permitted contractual extension is supported by the required finance-officer approval [rule:CPR-77].',
 'For each selected supplier trace the payments to the current contract; inspect original extension rights, any replacement agreement and the recorded extension approval, distinguishing public-notice staleness from an unsupported extension.',
 'Original contract, extension clause, renewal or replacement agreement, approval record and payment linkage.',
 ['Current and predecessor contracts for the selected suppliers','Extension or renewal approvals and effective dates','Record linking sampled payments to the governing agreement'])
add('Spend-to-award differences need scope and variation review',
 'Annualised payment estimates above the annual rate implied by a matched award warrant reconciling scope, timing and any approved variation.',
 2,'There are '+ph('$.tests.spend_vs_award.count')+' eligible supplier indicators [metric:$.tests.spend_vs_award.count]. Likelihood is reduced below the recurring-pattern baseline because annualisation, award estimates and multi-contract scope may explain the difference; this does not establish a variation [rule:CPR-78].',
 3,'If a material change lacked the prescribed approval, it could raise a reasonable possibility of legal challenge under the Medium descriptor [history:IMPACT-3] [rule:CPR-78]. No estimate of contractual overspend or loss is asserted.',
 'Reconcile payments to contract scope, duration and award value, then verify any modification and its required approval.',
 'spend-vs-award.csv',dict(kind='suppliers',source='spend-vs-award.csv',where={'dominant_tag':'general_procurement'},order_by='ratio',descending=True,n=5,per_group_n=2),
 'Contract modifications are within the permitted scope and carry the approval required for the relevant value category [rule:CPR-78].',
 'Reconcile selected payments to the award scope and payment schedule; compare actual period expenditure with the contract basis rather than assuming annualisation proves overspend, and inspect change control, modification grounds and the applicable approval.',
 'Signed contract, award-value basis, invoices, payment schedule, change-control log and approval reports.',
 ['Award-value calculation, scope and payment schedule','Variation or change-control records with approvals','Explanation of timing or scope differences behind the annualised indicator'])
add('Waiver and delegated-authority records require direct inspection',
 'Public payment and notice data cannot establish whether exceptions were requested in advance, justified and approved by the correct delegated authority.',
 1,'This is a rule-only governance gap without current evidence of failed approvals [rule:CPR-21] [rule:CPR-25] [rule:CPR-27]. Contract Letting previously received Reasonable Assurance and the supplied appendix contains no detailed finding to support an adverse uplift [history:AUD-01].',
 3,'An unauthorised waiver could expose the procurement process to external criticism or legal challenge, provisionally matching the Medium descriptor [history:IMPACT-3] [rule:CPR-27]. Consequence information is not available.',
 'Request the waiver register and delegation records, establish the population, and inspect advance timing, reasons and the relevant approval trail.',
 None,dict(kind='none',note='Document/enquiry test; obtain the waiver population and authority records before selecting internal cases.'),
 'Exceptions are sought in advance, documented and approved by the authorised roles; contract award authority follows the applicable delegation [rule:CPR-21] [rule:CPR-25] [rule:CPR-27] [rule:CPR-05].',
 'Obtain the waiver and exception population and current delegated-authority records; inspect documented reasons, timing, report approval and authorisation, referring unresolved threshold boundaries for human interpretation before reaching a compliance conclusion.',
 'Waiver register, exception reports, approval timestamps and delegated-authority records.',
 ['Waiver and exception register covering the payment period','Reports, reasons and dated authorisations for the selected internal cases','Applicable delegated-authority records and auditor-resolved statutory thresholds'])
add('Placement exemptions need documented reasons for provider selection',
 'Care and education placement payments need a separate review of exemption eligibility and documented provider-selection reasons; routine recurrence must not be treated as procurement splitting.',
 1,'The population includes '+ph('$.population.tags.care_or_education_placement.rows')+' tagged placement payments [metric:$.population.tags.care_or_education_placement.rows], but tags do not prove exemption status or missing records. The case-note requirement is therefore rated as a rule-only gap [rule:CPR-79]. Residential and nursing care had Reasonable Assurance; the separate Direct Payments Limited Assurance opinion supplies no matching detailed finding, so no repeat uplift is applied [history:AUD-18] [history:AUD-16].',
 3,'If provider-selection reasons were absent, the decision could attract external scrutiny consistent with the Medium reputation descriptor [history:IMPACT-3] [rule:CPR-79]. No deficient care, personal harm or financial loss is inferred.',
 'Determine actual exemption category and inspect provider-selection reasons and applicable approval, with appropriate handling of personal information.',
 None,dict(kind='none',note='Document/enquiry test; request a privacy-conscious case index and select internal records after confirming exemption category.'),
 'Eligible individual placement arrangements retain the reasons for provider selection on the individual case notes [rule:CPR-79].',
 'Obtain an anonymised placement case index and establish which cases fall within the stated exemption; inspect the recorded reasons for provider selection and any applicable board approval without inferring a missing record from payment recurrence.',
 'Anonymised case index, exemption assessment, redacted provider-selection reasons and applicable approval records.',
 ['Anonymised placement case index and exemption categorisation','Redacted case-note evidence explaining provider selection','Applicable approval records without unnecessary personal information'])
obj=dict(generated_at='2026-10-06',preparation=dict(producer='Codex source-grounded preparation',status='draft awaiting Claude Code validation and auditor decisions',claude_code_verified=False,human_scope_approved=False,prepared_fields_use='Teaching/demo recipes only; not a planning pack and not human-authorised fieldwork.'),risks=risks,excluded=[dict(theme='Statutory-threshold-specific compliance conclusions',reason='The rulebook leaves statutory parameters null; category, applicable legislation and authoritative dated amounts require auditor input before that conclusion can be tested.'),dict(theme='Repeated adverse procurement finding uplift',reason='The supplied appendices contain adverse opinions but no matching recurring procurement issue with detailed findings; a school follow-up or Direct Payments opinion alone does not prove the same procurement failure.'),dict(theme='Individual overdue action follow-up',reason='No action list with due dates and status is supplied; missing actions are recorded as a source gap rather than invented.'),dict(theme='Supplier-specific wrongdoing',reason='The data supports planning indicators only; no accusation or misconduct conclusion is supported.')])
(B/'outputs/risk-ratings.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print('Wrote',len(risks),'draft risks; no human decisions or planning outputs were created.')
