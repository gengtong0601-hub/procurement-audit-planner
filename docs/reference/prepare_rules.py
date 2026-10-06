"""Reproducible Codex-prepared source extraction; does not claim Claude execution."""
import json,re,pypdf
from pathlib import Path
BASE=Path(__file__).resolve().parents[2]
pages=(BASE/'docs/reference/pdf-text/contract-rules.plain.txt').read_text().split('\f')
def norm(s): return re.sub(r'\s+',' ',s).strip()
clauses={}
for page,txt in enumerate(pages[:10],1):
 matches=list(re.finditer(r'^\s*(\d+\.\d+(?:\.\d+)*)\s+',txt,re.M))
 for i,m in enumerate(matches):
  body=txt[m.end():matches[i+1].start() if i+1<len(matches) else len(txt)]
  # Remove later section/subsection headings, not words in the obligation.
  body=re.split(r'\n(?:\d+ [A-Z]|(?:Transparency obligations|Preliminaries|Advertising|Contract Value & Aggregation|Financial Thresholds & Procedures|Principles and Evaluation|Submission and Opening of Tenders|Exclusions|Exceptions|Insurances|Sealing|Signature of Documents|Counsel:|Risk Assessment & Performance Bond)\s*\n)',body)[0]
  clauses[m.group(1)]=(page,norm(body))
# Per-clause structured judgments. Quotes are extracted, never retyped.
M={}
def rule(c,action,condition='all contracts',typ='required-action',approver=None,scope='all',low=None,high=None,li=None,hi=None,lr=None,hr=None,ev='council-records',quote=None):
 page,q=clauses[c]
 M[c]=dict(clause=c,page=page,type=typ,scope=scope,condition=condition,threshold_low=low,threshold_low_inclusive=li,threshold_high=high,threshold_high_inclusive=hi,threshold_low_ref=lr,threshold_high_ref=hr,required_action=action,approver=approver,evidence_source=ev,verbatim_quote=quote or q)
R='STATUTORY_THRESHOLD_RELEVANT'; G='STATUTORY_THRESHOLD_GOODS_SERVICES'; W='STATUTORY_THRESHOLD_WORKS_CONCESSIONS'; L='STATUTORY_THRESHOLD_LIGHT_TOUCH'
rule('3.2','Obtain interpretation of these Rules from the Monitoring Officer or nominated officer.',typ='approver',approver='Monitoring Officer (or any officer nominated by the Monitoring Officer for the purpose)')
rule('3.5','Document consideration of economic, social and environmental wellbeing when procuring the service.','service contract exceeding the Goods & Services Threshold',scope='goods-services',lr=G,li=False)
rule('4.2','Confirm an existing budgetary provision within the Council-approved Budget before entering the contract.')
rule('4.3','Treat the contract award as a Key Decision.','contract award over £500,000',typ='threshold',low=500000,li=False)
rule('4.4','Obtain Appendix A approval before award where the Service Director lacks delegated authority.',approver='roles specified in Appendix A',typ='approver')
rule('5.1.1','Publish expenditure exceeding £500, including supplier and contractor payments.','expenditure exceeding £500',typ='threshold',low=500,li=False,ev='spend-data')
rule('5.2','Publish details of every invitation to tender for goods or services exceeding £5,000.','goods or services invitation to tender over £5,000',typ='threshold',low=5000,li=False,scope='goods-services')
rule('5.2.1','Publish a register of contracts in progress and awarded with value, duration and supplier.',ev='contracts-register')
rule('5.3','Report contract information to the relevant board monthly in the required format.')
rule('6.10','Advertise above-threshold opportunities on the CDP before other media, except further competitions under compliant frameworks.','above relevant Procurement Legislation threshold, except compliant framework further competition',lr=R,li=False)
rule('6.11','Publicise contracts of potential cross-border interest so tenderers from other member states can participate.','contract of potential cross border interest')
rule('6.14','Obtain approval and issuance of CDP notices by the Service Lead for Procurement and Commissioning or delegate.','CDP notices',typ='approver',approver='Service Lead for Procurement and Commissioning or their delegate')
rule('6.16','Do not artificially split or disaggregate contracts to avoid the legislation or Rules.',typ='anti-avoidance',ev='spend-data')
rule('6.19','Issue an electronic Invitation to Tender and receive tenders through the Council Procurement Portal.','contract estimated above the appropriate Threshold',lr=R,li=False)
rule('6.20','Specify tender format in the Portal and invitation and lock electronic tenders securely until opening date and time.')
rule('6.21','Reject late tenders unless the Monitoring Officer confirms exceptional circumstances and other tenders remain unopened.','late tender',typ='approver',approver='Monitoring Officer')
rule('6.22','Have a Procurement Officer open electronic tenders and retain the e-tendering audit record.',approver='Procurement Officer')
rule('6.24','Evaluate all quotes and tenders using criteria notified in advance.')
rule('6.26','Award on most advantageous best value rather than price alone unless the Service Director approves an exception in advance.','quote or tender award',typ='approver',approver='relevant Service Director')
rule('7.2.2','Record reasons in writing for the Executive Director or Chief Executive discretionary waiver.','waiver for contracts of more than £24,999.99 under 7.2',typ='approver',approver='relevant Executive Director and/or the Chief Executive',low=25000,li=True)
rule('7.3','Seek waivers only in advance and exceptional circumstances from the Monitoring Officer and/or S.151 Officer.','waiver or exception request',typ='approver',approver='Monitoring Officer and/or the S.151 Officer')
rule('7.4.1','Obtain S.151 Officer approval of the exception.','contracts up to the Threshold',typ='approver',approver='S.151 Officer',hr=R,hi=True)
rule('7.4.2','Have the S.151 Officer consult the Monitoring Officer and Executive Director and secure a board-approved exception report, or report retrospectively for the stated urgency exception.','contracts above relevant Threshold and up to £500,000',typ='approver',approver='S.151 Officer; Monitoring Officer; appropriate Executive Director; relevant board',lr=R,li=False,high=500000,hi=True)
rule('7.4.3','Obtain an Executive recommendation by S.151 and Monitoring Officers supported by a report approved by the relevant board and Corporate Board.','contracts over £500,000',typ='approver',approver='S.151 Officer; Monitoring Officer; Executive; relevant board; Corporate Board',low=500000,li=False)
rule('7.5.1','Fully document all exceptions or waivers.','all exceptions or waivers')
rule('7.5.2','Submit a written exception report with reasons to the relevant board in advance through the named director.','competitive process not excluded by Procurement Legislation')
rule('7.5.3','Obtain recorded S.151 approval confirming the reasons are genuinely exceptional.','all exceptions or waivers',typ='approver',approver='S.151 Officer')
rule('8.2','Seek advice confirming entitlement, coverage and compliance before using a Purchasing Scheme.','Purchasing Scheme used')
rule('9.1','Have the relevant Service Director produce the written procurement report.','above-Threshold awarded contract subject to Procurement Legislation',lr=R,li=False)
rule('9.2','Retain the procurement report for three years.','report under 9.1')
rule('9.3','Retain procurement procedure documentation for three years from award.',quote='Such documentation must be kept for three years from the award of the contract.')
rule('10.2','Use written contracts in a form approved by the Monitoring Officer or delegated officer.','contracts detailed in Appendix B',typ='approver',approver='Monitoring Officer or their delegated officer')
rule('10.3','Have Legal Services retain all sealed contract documents.','sealed contracts')
rule('10.4','Formally notify the procurement lead or nominated officer of every award for recording on the Council Contract Register.',ev='contracts-register')
rule('10.6','Have the Service Director prepare amendments to the Standard Form and obtain Monitoring Officer approval.','Standard Form of Agreement amended',typ='approver',approver='Monitoring Officer or their delegated officer')
for c,action in [('10.7.1','Include the works, supplies, goods, services and other deliverables.'),('10.7.2','Include the time for performance.'),('10.7.3','Include quality requirements and standards.'),('10.7.4','Require appropriate contractor insurance.'),('10.7.5','Include consequences for non-compliance with obligations.'),('10.7.6','Require contractor compliance with relevant legislation including equalities and health and safety.'),('10.7.7','Include personal-data clauses and complete a Data Protection Impact Assessment for all contracts.'),('10.7.8','Include cancellation and recovery rights for improper conduct or a Bribery Act offence.'),('10.7.9.1','Include payment within 30 days from the invoice being valid and undisputed.'),('10.7.9.2','Flow the payment obligations down through subcontracts.'),('10.7.10','Include specifications or briefs addressing delivery, quality, sustainability, efficiency and enforceability.')]:
 rule(c,action,'all contracts, as a minimum where appropriate under 10.7')
rule('11.1','Obtain written authorisation before relaxing full indemnities.','relaxation of full indemnities',typ='approver',approver='Monitoring Officer and S.151 Officer or their nominated officers')
rule('11.3','Include the performance bond in the Invitation to Tender in a Legal Services approved form.','performance bond required',typ='approver',approver='Legal Services')
for c,a in [('11.4.1','Prepare a written risk assessment.'),('11.4.2','Seek approval from the Service Director for Finance and Property.'),('11.4.3','Keep the risk assessment on the contract file for inspection.')]:
 rule(c,a,'performance bond not considered necessary under 11.4',typ='approver' if c=='11.4.2' else 'required-action',approver='Service Director for Finance and Property' if c=='11.4.2' else None)
for c,a in [('11.5.1','Set adequate insurance levels in consultation with the finance/property director or nominated officer.'),('11.5.2','Ensure the contractor holds insurance and maintains current or renewed policies in consultation with the finance/property director.'),('11.5.3','Confirm contractor status under the Inland Revenue Construction Industry Tax Deduction Scheme in consultation with the finance/property director.'),('11.5.4','Set professional indemnity cover case by case in consultation with the finance/property director.')]:
 rule(c,a,'risk assessment identifies need for insurance; construction/professional services conditions apply to respective subclauses',approver='Service Director for Finance and Property or nominated officer')
rule('11.6','Keep the Common Seal safely in the Monitoring Officer’s custody.')
rule('11.7','Affix the Seal only to an approved document or proposal.','use of the Seal',typ='approver',approver='Council or Executive; appropriate Committee; officer with delegated powers')
rule('11.8','Have the Monitoring Officer or designated officer attest and witness sealing in writing.','affixing the Seal',typ='approver',approver='Monitoring Officer or duly designated officer')
rule('11.9','Keep a consecutively numbered sealing record signed by the person attesting.')
rule('11.10','Affix the Seal to every document requiring sealing, including the specified petitions, mortgages and transfers.','documents required to be sealed')
rule('11.11','Seal all above-Threshold goods, services, works and concession contracts.','contract value above the Threshold',lr=R,li=False)
rule('11.12','Have the Monitoring Officer or authorised officer sign documents necessary for legal proceedings unless a stated exception applies.','document necessary for legal proceedings',typ='approver',approver='Monitoring Officer or duly authorised officer')
rule('11.13','Keep a register of documents executed without a required seal and use the Monitoring Officer or designated signatory.','execution of document not required by law to be sealed',typ='approver',approver='Monitoring Officer or designated officer')
rule('11.14','Use only the Monitoring Officer or nominated officer to select and instruct Counsel.',typ='approver',approver='Monitoring Officer (or nominated officer)')
# Appendix cells copied from the page, preserving punctuation.
def cell(page,start,end=None):
 t=norm(pages[page-1]); a=t.index(start); return t[a:t.index(end,a) if end else len(t)].strip()
def app(c,page,q,action,condition,typ='approver',approver=None,scope='all',low=None,li=None,high=None,hi=None,lr=None,hr=None,ev='council-records'):
 clauses[c]=(page,q);rule(c,action,condition,typ,approver,scope,low,high,li,hi,lr,hr,ev)
app('App A row 1',11,cell(11,'Relevant Service Director (or such officers','Above the relevant'),'Obtain award by the Service Director or officer nominated in writing.','up to relevant Threshold',approver='Relevant Service Director or officers nominated in writing',hr=R,hi=True)
app('App A row 2',11,cell(11,'Relevant Service Director (following','Above £500,000'),'Obtain director award following S151 and Monitoring Officer recommendation and a board-approved written report.','above relevant threshold and less than £500,000',approver='Relevant Service Director; S151 officer; Monitoring Officer; relevant board',lr=R,li=False,high=500000,hi=False)
app('App A row 3',11,cell(11,'The award of these contracts','£2.5million or more'),'Follow Key Decision delegation, consultations, recommendations, board report and Call-In/Forward Plan requirements.','above £500,000 and less than £2.5million',approver='relevant Service Director; Portfolio Holder; Executive Director; S151 officer; Monitoring Officer; relevant board',low=500000,li=False,high=2500000,hi=False)
app('App A row 4',11,cell(11,'Contracts with a value in excess'),'Obtain Executive approval and quarterly procurement reports with the stated delegated award consultations.','table band £2.5million or more; cell says in excess of £2.5million (discrepancy)',approver='Executive; Service Director; Portfolio Holder; S.151 Officer; Monitoring Officer',low=2500000,li=True)
app('App B row A',12,'At least one quote must be sought from an appropriate source.','Seek at least one quote from an appropriate source.','above £1,000 and less than £25,000 (exclusive of VAT)',typ='threshold',low=1000,li=False,high=25000,hi=False,ev='spend-data')
app('App B row B1',12,cell(12,'Invitations to quote must be sent','B2 Works,'),'Invite at least three quotes via the Portal, including SME/VCSE and local suppliers where appropriate and possible, and publish a CDP contract notice.','goods/services: £25,000 or more and less than the Threshold (exclusive of VAT)',typ='threshold',scope='goods-services',low=25000,li=True,hr=G,hi=False,ev='spend-data')
# B2 phrase carries a space after ****; source includes complete advertising cell.
p12=norm(pages[11]); start=p12.index('Invitations to quote must be sent',p12.index('B2 Works,')); end=p12.index('C Works,',start)
app('App B row B2',12,p12[start:end].strip(),'Invite at least three quotes via the Portal, including SME/VCSE and local suppliers where appropriate and possible, and publish a CDP contract notice.','works/concession/light touch: £25,000 or more and less than £500,000 (exclusive of VAT)',typ='threshold',scope='works-concession-light-touch',low=25000,li=True,high=500000,hi=False,ev='spend-data')
app('App B row C',12,cell(12,'Full competitive tender process','D Goods and'),'Run a full competitive process and seek at least five written tenders via the Portal.','works/concession/light touch: above £500,000 and less than relevant Threshold (exclusive of VAT)',typ='threshold',scope='works-concession-light-touch',low=500000,li=False,hr=R,hi=False,ev='spend-data')
app('App B row D',12,cell(12,'Procurement Legislation Procedures apply'),'Run a full competitive tender under the legislation with at least five written tenders where appropriate via the Portal.','all listed categories above relevant Threshold (exclusive of VAT)',typ='threshold',lr=R,li=False,ev='spend-data')
app('App C row A',14,'Prior written approval from the Monitoring Officer is required and where applicable prior approval has been granted by the relevant board.','Obtain prior written Monitoring Officer approval and applicable board approval.','contract excluded under Procurement Legislation',approver='Monitoring Officer; relevant board where applicable')
app('App C row B',14,'Key decisions must be recorded and the relevant process under PSR followed','Record key decisions and follow the relevant PSR process.','contract governed by Provider Selection Regime',typ='required-action')
app('App C row C',14,'Prior written approval from the Monitoring Officer is required and where applicable prior approval has been granted by the relevant board.','Obtain prior written Monitoring Officer approval and applicable board approval.','Purchasing Scheme without further competition because competition undertaken for Council or public sector body',approver='Monitoring Officer; relevant board where applicable')
app('App C row D',14,'Approval of the S151 Officer','Obtain S151 Officer approval of the permitted extension.','existing contract provides for the extension',approver='S151 Officer',ev='council-records')
app('App C row E',14,cell(14,'For contract value below the'),'Obtain prior written Monitoring Officer and S151 approval below Threshold, or relevant-board approval on a recommended report above Threshold.','variation provided for by existing contract or modification permitted by legislation; below/greater than Threshold approval differs',approver='Monitoring Officer; S151 Officer; relevant board above Threshold')
app('App C row F',15,cell(15,'Service Directors must ensure','In the interests of clarity'),'Maintain reasons for provider choice on the individual case notes.','social care services under Appendix C row F(a)-(f)',typ='required-action',approver='Service Directors')
app('App C final paragraph',15,cell(15,'In the interests of clarity'),'Obtain relevant-board approval for exempt contracts above the Threshold.','exemption applied and annual or total value more than the Threshold',approver='relevant board',lr=R,li=False)
# Exclusions enumerate every remaining numbered clause and appendix footnote.
reasons={}
def exclude(cs,reason):
 for c in cs.split(): reasons[c]=reason
exclude('1.1 1.2 1.3','legal basis or external legislation listing; no standalone testable obligation')
exclude('1.4 1.5 1.6 1.6.1 1.6.2','definition or scope text; no standalone obligation')
exclude('2.1 2.2 2.3','purpose statement; no testable obligation')
exclude('3.1 3.1.1 3.1.2 3.3 3.6','scope or structural cross-reference; substantive tests captured in applicable rules')
exclude('3.4','principles and external Council policies whose content is not in this PDF')
exclude('4.1 4.1.1 4.1.2 4.1.3 4.1.3.1 4.1.3.2 4.1.3.3','general authority list; specific delegated authorities captured in App A rows 1–4')
exclude('5.1','introductory publication principle; concrete requirements captured in 5.1.1, 5.2 and 5.2.1')
exclude('6.1 6.1.1 6.1.2 6.1.3 6.1.4 6.1.5 6.1.6 6.2','delegation to external legislation, Constitution, intranet or policies not provided')
exclude('6.3 6.9 6.12','permissible procedure or option; no standalone mandatory action')
exclude('6.4','minimum suitability/capability standards are not stated; cannot test compliance without external standard')
exclude('6.5 6.6','reference to intranet thresholds or legal transition advice; no values or standalone testable obligation')
exclude('6.7 6.18','general principles without a concrete objective acceptance criterion')
exclude('6.8 6.13 6.17','discretionary should/advice wording, not a mandatory concrete obligation')
exclude('6.15','definition of Total Contract Value, spanning pages 4–5; VAT inconsistency with Appendix B recorded in notes')
exclude('6.23','heading only')
exclude('6.25 7.6','external legislation requirements not provided in the PDF')
exclude('7.1 7.7','cross-reference to specific App C rules captured separately')
exclude('7.2 7.2.1','waiver eligibility circumstances; approval and record requirements captured in 7.2.2–7.5.3')
exclude('7.4 7.5 10.7 10.7.9 11.4','parent heading for mandatory subclauses captured individually')
exclude('7.5.4','duplicate approval obligation captured in 7.3, 7.4.1–7.4.3 and 7.5.3')
exclude('8.1 8.1.1 8.1.2 8.1.3 8.1.4 8.1.5 8.1.6 8.1.7','definition/examples of Purchasing Schemes')
exclude('8.2.1 8.2.2 8.2.3','advice-confirmation scope included in parent 8.2 required-action rule')
exclude('8.3','exemption scope and discretionary advice; approvals captured in App C row C')
exclude('10.1','should wording; mandatory written-contract requirement captured in 10.2')
exclude('10.5','standard clauses are in an external Standard Form not supplied')
exclude('11.2','discretionary should consider bond; mandatory bond-form and no-bond controls captured in 11.3–11.4.3')
exclude('11.5','parent conditional insurance trigger and discretionary assessment; mandatory subclauses captured individually')
exclude('11.10.1 11.10.2 11.10.3','specific document examples included in the 11.10 sealing obligation')
rules=[];excluded=[]
for c,(p,q) in clauses.items():
 if c in M:
  r=M[c];r={'rule_id':f'CPR-{len(rules)+1:02}',**r};rules.append(r)
 else:
  assert c in reasons,c
  excluded.append(dict(clause=c,page=p,reason=reasons[c]))
for c,reason in [('App B footnote *','SME and VCSE definitions'),('App B footnote **','principle of non-preference and discretionary barrier-reduction intention; no record or action test'),('App B footnote ***','external threshold definitions; monetary values not provided'),('App B footnote ****','external local supplier policy definition not provided')]: excluded.append(dict(clause=c,page=13,reason=reason))
obj=dict(source=dict(file='data/contract-rules.pdf',title='Contract Rules',version=None,pages=15,extracted_on='2026-10-06',extraction_tool=f'pypdf {pypdf.__version__}; plain and layout (Poppler unavailable)'),parameters={x:dict(value=None,description=d,defined_by='1.4 and App B footnote ***',note='Not stated in the PDF; auditor must supply an applicable dated value and source before statutory-threshold dependent analysis.') for x,d in [(G,'Applicable statutory goods and services Threshold'),(W,'Applicable statutory works and concession Threshold'),(L,'Applicable statutory light-touch Threshold'),(R,'Relevant category-specific statutory Threshold; resolve category and applicable legislation before use')]},notes=['Source title shows Part [] without a part number; Appendix A row 3 leaves Parts [] (Call-In) and [] (Forward Plan) placeholders. No version/date printed in the source PDF; source manifest may supply publication context.','6.15 (pp.4–5) defines total contract value including Value Added Tax; Appendix B (p.12) labels total value exclusive of VAT. Both are preserved; auditor must resolve application before concluding non-compliance.','Appendix A leaves exactly £500,000 between row 2 (<£500,000) and row 3 (>£500,000). Row 4 band says £2.5million or more but cell says in excess of £2.5million.','Appendix B row A begins above £1,000; no mandatory process is stated at or below £1,000. Rows B2 and C omit exactly £500,000. Rows B1/C below Threshold and D above Threshold leave equality unspecified.','Appendix C row E specifies below and greater than Threshold, leaving equality unspecified.','6.11 retains other member states wording; do not silently reinterpret its legal context.','All statutory Threshold parameters remain null; printed £1,000 / £25,000 / £500,000 / £2.5million amounts are preserved with inclusivity flags.','Page numbers are one-based PDF pages; quotes use pypdf plain extraction and preserve source extraction artefacts. Human visual checks and Claude skill execution remain pending as documented separately.'],rules=rules,excluded=excluded)
# Explicit applicability prevents a publication-only rule being mistaken for a competition trigger.
for r in obj['rules']:
 if r['clause']=='5.2': r['competition_triggering']=False
 if r['clause'].startswith('App B row '): r['competition_triggering']=True
(BASE/'outputs').mkdir(exist_ok=True)
(BASE/'outputs/rules.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print(len(rules),'rules',len(excluded),'excluded')
for r in rules:
 if r['clause'].startswith('App'):print(r['rule_id'],r['clause'])
