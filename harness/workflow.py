"""File-backed orchestration with explicit human gates and reproducible computation.

The web harness owns execution. Claude API roles supply judgments; checked-in
Python computes figures and validates their work. Native Claude Code team
messaging remains a separate Part A verification.
"""
import copy
import csv
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

from .provider import generate_json

ROOT = Path(__file__).resolve().parents[1]


def csv_columns(path):
    with Path(path).open(newline='', encoding='utf-8') as stream:
        return next(csv.reader(stream), [])


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def event(run, role, message):
    with (run / 'events.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'at': datetime.now(timezone.utc).isoformat(), 'role': role, 'message': message}) + '\n')


def command(run, relative, *args, required=True):
    process = subprocess.run([sys.executable, str(run / relative), *map(str, args)], cwd=run,
                             capture_output=True, text=True, timeout=240)
    message = (process.stdout + process.stderr)[-18000:]
    (run / 'logs').mkdir(exist_ok=True)
    (run / 'logs' / (Path(relative).stem + '.log')).write_text(message, encoding='utf-8')
    if process.returncode and required:
        raise ValueError(f'{Path(relative).name} stopped the workflow:\n{message[-7000:]}')
    return process.returncode, message


def create_workspace(run, mode):
    required = ['rules.json', 'history.json', 'analytics.json', 'risk-ratings.json']
    missing = [name for name in required if not (ROOT / 'outputs' / name).exists()]
    if missing:
        raise ValueError('Prepared evidence is not complete: ' + ', '.join(missing))
    run.mkdir(parents=True)
    for folder in ('.claude', 'scripts'):
        shutil.copytree(ROOT / folder, run / folder, ignore=shutil.ignore_patterns('__pycache__', 'agent-memory'))
    shutil.copytree(ROOT / 'data', run / 'data')
    (run / 'outputs').mkdir()
    for name in required:
        shutil.copy2(ROOT / 'outputs' / name, run / 'outputs' / name)
    shutil.copytree(ROOT / 'outputs/analytics-full', run / 'outputs/analytics-full')
    shutil.copy2(ROOT / 'CLAUDE.md', run / 'CLAUDE.md')
    write_json(run / 'state.json', {'mode': mode, 'stage': 'preparing', 'error': None})
    event(run, 'harness', 'Created isolated run. No reviewer decisions copied.')


def module_at(run, relative):
    spec = importlib.util.spec_from_file_location('audit_builder_' + run.name, run / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def agent_instructions(run, agent, skill=None):
    chunks = [(run / '.claude/agents' / (agent + '.md')).read_text()]
    if skill:
        chunks.append((run / '.claude/skills' / skill / 'SKILL.md').read_text())
    return '\n\n'.join(chunks)


def evidence(run):
    return {name: read_json(run / 'outputs' / (name + '.json'))
            for name in ('rules', 'analytics', 'history')}


def initialise(run):
    state = read_json(run / 'state.json')
    command(run, '.claude/skills/extract-rules/verify_quotes.py', 'outputs/rules.json', 'data/contract-rules.pdf')
    event(run, 'extract-rules', 'Verified the prepared rule extraction against the original PDF; no fresh model extraction claimed.')
    command(run, 'scripts/verify_history.py', 'outputs/history.json', 'data/committee')
    if state['mode'] == 'live':
        # Public data and checked rules are fixed case-study inputs; recompute the
        # spend analysis and reassess committee evidence in independent branches.
        def spend():
            command(run, 'scripts/clean.py')
            command(run, 'scripts/analyse.py')
            event(run, 'spend-analyst', 'Recomputed full-population indicators using Python.')

        def findings():
            from pypdf import PdfReader
            papers = {p.name: [{'page': n, 'text': page.extract_text() or ''}
                              for n, page in enumerate(PdfReader(p).pages, 1)]
                      for p in sorted((run / 'data/committee').glob('*.pdf'))}
            result = generate_json(agent_instructions(run, 'findings-analyst'),
                                   {'task': 'Extract history using the existing schema. Preserve quotes and page evidence, not prior conclusions.',
                                    'schema_example': read_json(run / 'outputs/history.json'), 'papers': papers})
            write_json(run / 'outputs/history.json', result)
            command(run, 'scripts/verify_history.py', 'outputs/history.json', 'data/committee')
            event(run, 'findings-analyst', 'Claude extracted committee evidence; source verifier passed.')

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(spend), pool.submit(findings)]
            for future in futures:
                future.result()
        ratings = generate_json(agent_instructions(run, 'risk-assessor', 'risk-assessment'),
                                {'task': 'Create an initial risk-ratings.json. No human decisions or revision. Use the example shape, but source every judgment from the current evidence.',
                                 'example_shape': read_json(run / 'outputs/risk-ratings.json'), **evidence(run)})
        ratings.pop('revision', None)
        write_json(run / 'outputs/risk-ratings.json', ratings)
        event(run, 'risk-assessor', 'Claude supplied source-linked risk judgments; Python will validate and score them.')
    else:
        event(run, 'harness', 'Prepared evidence mode: replaying Codex-prepared judgments and computed evidence; no live Claude calls.')
    command(run, '.claude/skills/risk-assessment/build_register.py')
    state['stage'] = 'risk-review'
    write_json(run / 'state.json', state)


def decision_text(value, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError('A nonempty text field is required (maximum ' + str(limit) + ' characters).')
    if any(c in value for c in ('|', '\n', '\r')):
        raise ValueError('Reviewer fields cannot contain line breaks or table separators.')
    return value.strip()


def apply_decisions(run, payload):
    state = read_json(run / 'state.json')
    if state['stage'] != 'risk-review':
        raise ValueError('Risk decisions can only be recorded once at the risk-review stage. Start a new run to change scope.')
    reviewer = decision_text(payload.get('reviewer'), 120)
    ratings = read_json(run / 'outputs/risk-ratings.json')
    original = {r['id']: r for r in ratings['risks']}
    decisions = payload.get('decisions')
    if not isinstance(decisions, list) or len(decisions) != len(original):
        raise ValueError('One explicit decision is required for every risk.')
    ids = [d.get('id') for d in decisions if isinstance(d, dict)]
    if len(ids) != len(set(ids)) or set(ids) != set(original):
        raise ValueError('Decision IDs must match the register exactly, without duplicates.')
    revised = copy.deepcopy(ratings)
    changes, retained, rows = [], [], []
    for item in decisions:
        rid, action = item['id'], item.get('decision')
        if action not in ('approve', 'amend', 'reject'):
            raise ValueError(rid + ': choose approve, amend, or reject.')
        raw_comment = item.get('comment', '')
        if not isinstance(raw_comment, str):
            raise ValueError(rid + ': comment must be text.')
        comment = raw_comment.strip()
        if comment:
            comment = decision_text(comment)
        if action != 'approve' and not comment:
            raise ValueError(rid + ': amendments and rejections require your reason.')
        risk = copy.deepcopy(original[rid])
        if action == 'amend':
            if all(item.get(dim) == original[rid][dim]['score'] for dim in ('likelihood', 'impact')):
                raise ValueError(rid + ': amend must change at least one score; choose approve to retain the rating.')
            for dimension in ('likelihood', 'impact'):
                n = item.get(dimension)
                if type(n) is not int or not 1 <= n <= 5:
                    raise ValueError(rid + ': amendment scores must be integers from one to five.')
                risk[dimension]['score'] = n
            # Keep human numerical requests in the decision log, not analytical prose.
            comment += f"; likelihood to {risk['likelihood']['score']}; impact to {risk['impact']['score']}"
            risk['auditor_override'] = True
            changes.append({'id': rid, 'action': 'amended', 'summary': 'Auditor supplied revised likelihood and impact; see auditor-comments.md.'})
        if action == 'reject':
            revised.setdefault('excluded', []).append({'id': rid, 'reason': comment})
            changes.append({'id': rid, 'action': 'rejected', 'summary': comment})
        else:
            retained.append(risk)
        rows.append([rid, risk['title'], 'see register', 'yes' if risk.get('recommend_in_scope', True) else 'no', action, comment])
    # All validation above precedes persistence of human decisions.
    revised['risks'] = retained
    revised['revision'] = {'number': 1, 'changes': changes}
    text = ['# Auditor decisions', '', 'Reviewer: ' + reviewer, 'Date: ' + date.today().isoformat(), '',
            '| Risk | Title | Current rating | Proposed scope | Decision | Comment |', '|---|---|---|---|---|---|']
    text += ['| ' + ' | '.join(str(x) for x in row) + ' |' for row in rows]
    names = ('auditor-comments.md', 'risk-ratings.json', 'risk-register.md', 'risk-baseline.json', 'gate-evidence.json')
    before = {name: (run / 'outputs' / name).read_bytes() if (run / 'outputs' / name).exists() else None for name in names}
    try:
        (run / 'outputs/auditor-comments.md').write_text('\n'.join(text) + '\n')
        write_json(run / 'outputs/risk-ratings.json', revised)
        command(run, '.claude/skills/risk-assessment/build_register.py')
        command(run, '.claude/skills/audit-program/build_pack.py', '--gate')
    except Exception:
        # Validation failure must not partially apply decisions or damage the
        # original evidence a reviewer is still considering.
        for name, content in before.items():
            path = run / 'outputs' / name
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        raise
    state['stage'] = 'approved'
    state['reviewer'] = reviewer
    write_json(run / 'state.json', state)
    event(run, 'human', 'Reviewer explicitly decided every risk; validated revision closed the scope gate.')


def prepared_plan(run):
    """Transparent rule-based teaching baseline; never represented as a live agent."""
    ratings = read_json(run / 'outputs/risk-ratings.json')
    rules = read_json(run / 'outputs/rules.json')['rules']
    by_id = {r['rule_id']: r for r in rules}
    risks, used = [], set()
    for r in ratings['risks']:
        if not r.get('recommend_in_scope', True):
            continue
        refs = list(dict.fromkeys(re.findall(r'\[rule:(CPR-\d+)\]', json.dumps(r))))
        if not refs:
            raise ValueError(r['id'] + ': prepared plan needs a cited rule.')
        rule = by_id[refs[0]]
        used.update(refs)
        num = r['id'].split('-')[1]
        control, test = 'C-' + num + '.1', 'T-' + num + '.1'
        n = 10 if r['likelihood']['score'] * r['impact']['score'] >= 9 else 5
        recipe = copy.deepcopy(r.get('prepared_sample', {'kind': 'none', 'note': 'Inspect the named council records; no public transaction sample supports this control.'}))
        if recipe['kind'] != 'none':
            recipe['n'] = n
        risks.append({'id': r['id'], 'objective': r['proposed_focus'],
                      'controls': [{'id': control, 'control': r.get('prepared_control', 'Apply the sourcing route, authorisation and documentation requirements specified by the cited procurement rule.'), 'owner': rule.get('approver') or 'Responsible officer; confirm with council', 'cites': ['rule:' + x for x in refs]}],
                      'tests': [{'id': test, 'control': control,
                                 'step': r.get('prepared_test', 'Obtain the records for the sampled procurement and compare its approvals, competition evidence and recorded rationale with the cited rule. Record exceptions for investigation without presuming wrongdoing.'),
                                 'evidence': r.get('prepared_evidence', 'Procurement file, original invoices, approvals, quotation records and current contract register'),
                                 'cites': ['rule:' + x for x in refs], 'sample': recipe,
                                 'pbc': r.get('prepared_pbc', ['Procurement and approval records for this test', 'Current contract register and relevant amendments'])} ]})
    return {'generated_at': date.today().isoformat(),
            'memo': {'purpose': ['Plan an evidence-led procurement control review of the supplied council case study.'],
                     'background': ['The analysis covers {{$.population.rows_after_exclusions}} retained payments over {{$.population.months_covered}} months [metric:$.population.rows_after_exclusions].'],
                     'approach': ['Prepared demonstration: baseline judgments and deterministic sample recipes, followed by explicit human scope decisions. No live Claude team execution is claimed.'],
                     'limitations': ['Published notices are not a complete contract register. Redacted payees cannot be linked as one supplier. Payment-run dates are not invoice dates. Undefined statutory thresholds are not filled from memory. This pack plans fieldwork; it does not reach findings.']},
            'risks': risks,
            'rules_not_tested': [{'reason': 'Not selected by the reviewer-approved case-study scope; further council records or defined statutory parameters are needed. Auditor must review this scope limitation.',
                                 'rule_ids': [r['rule_id'] for r in rules if r['rule_id'] not in used]}]}


def write_challenges(run, challenges):
    lines = ['# Challenges', '', '| No | Type | Risk | Challenge | Evidence | Ask | Response | Status |', '|---|---|---|---|---|---|---|---|']
    allowed = {'resolved', 'for the auditor', 'declined', 'open'}
    if not isinstance(challenges, list) or not challenges:
        raise ValueError('The challenger must produce at least one evidenced review point.')
    for i, item in enumerate(challenges, 1):
        if item.get('status') not in allowed:
            raise ValueError('Unknown challenge status.')
        values = [str(i)] + [str(item.get(k, '')).replace('|', '/').replace('\n', ' ') for k in
                            ('severity', 'risk', 'challenge', 'evidence', 'auditor_action', 'response', 'status')]
        if not item.get('evidence'):
            raise ValueError('Challenge has no evidence reference.')
        lines.append('| ' + ' | '.join(values) + ' |')
    (run / 'outputs/challenges.md').write_text('\n'.join(lines) + '\n')


def build_plan(run):
    state = read_json(run / 'state.json')
    if state['stage'] != 'approved':
        raise ValueError('Complete the risk review before planning.')
    command(run, '.claude/skills/audit-program/build_pack.py', '--gate')
    payload = {**evidence(run), 'risk_ratings': read_json(run / 'outputs/risk-ratings.json'),
               'auditor_decisions': (run / 'outputs/auditor-comments.md').read_text(),
               'available_csv_columns': {p.name: csv_columns(p) for p in (run / 'outputs/analytics-full').glob('*.csv')}}
    plan = prepared_plan(run) if state['mode'] == 'prepared' else generate_json(
        agent_instructions(run, 'planner', 'audit-program'),
        {'task': 'Return audit-plan.json exactly in the skill schema. Decisions are fixed. All figures use placeholders.', **payload})
    write_json(run / 'outputs/audit-plan.json', plan)
    command(run, '.claude/skills/audit-program/build_pack.py')
    event(run, 'planner', 'PACK READY v1: deterministic pack builder validated scope and drew samples.')
    if state['mode'] == 'prepared':
        challenges = [{'risk': 'Scope', 'challenge': 'Unresolved statutory parameters limit testing, and notice matching does not establish contract coverage.',
                       'severity': 'Review', 'evidence': 'CPR-01; analytics.json limitations',
                       'response': 'Limitations and rules not tested are disclosed in the pack.',
                       'auditor_action': 'Confirm scope and obtain internal records before fieldwork.', 'status': 'for the auditor'}]
        write_challenges(run, challenges)
        event(run, 'challenger', 'Prepared review point logged for the auditor. No independent model challenge claimed.')
    else:
        for round_no in (1, 2):
            result = generate_json(agent_instructions(run, 'challenger'),
                                   {'task': 'Review the plan. Return {challenges:[{risk,challenge,severity,evidence,response,auditor_action,status}]}. status is open, resolved, declined or for the auditor. Raise specific evidence-backed weaknesses; do not mark a planner correction resolved before reading the revised plan.',
                                    'round': round_no, 'audit_plan': plan, **payload})
            challenges = result.get('challenges', [])
            write_challenges(run, challenges)
            event(run, 'challenger', f'Review round {round_no} returned evidence-backed challenges.')
            if not any(c.get('status') == 'open' for c in challenges):
                break
            if round_no == 2:
                raise ValueError('Unresolved challenge after two rounds; the pack remains blocked for review.')
            plan = generate_json(agent_instructions(run, 'planner', 'audit-program'),
                                 {'task': 'Revise audit-plan.json to address challenger feedback without changing human scope.',
                                  'audit_plan': plan, 'messages_from_challenger': challenges, **payload})
            write_json(run / 'outputs/audit-plan.json', plan)
            command(run, '.claude/skills/audit-program/build_pack.py')
            event(run, 'planner', 'PACK READY v2: revised in response to challenger messages.')
    code, report = command(run, 'scripts/checks/run_checks.py', required=False)
    verdict = 'READY FOR SIGN-OFF' if code == 0 else 'BLOCKED'
    provenance = 'Prepared demonstration; no live Claude execution.' if state['mode'] == 'prepared' else 'Independent Claude API harness; not a native Claude Code agent team.'
    (run / 'outputs/review.md').write_text('# QA review\n\n' + provenance + '\n\n```text\n' + report + '\n```\n\n## Verdict\n\n' + verdict + '\n\n## Human sign-off\n\nName: \nDate: \nDecision: pending\n')
    state['stage'] = 'sign-off' if code == 0 else 'blocked'
    state['qa_verdict'] = verdict
    write_json(run / 'state.json', state)
    event(run, 'qa-reviewer', verdict + ': results saved in review.md.')
    return verdict


def sign_off(run, name):
    name = decision_text(name, 120)
    state = read_json(run / 'state.json')
    if state['stage'] != 'sign-off':
        raise ValueError('Sign-off requires all automated checks to pass.')
    command(run, 'scripts/checks/run_checks.py')  # recheck current files, not cached status
    path = run / 'outputs/review.md'
    text = path.read_text().split('## Human sign-off', 1)[0]
    path.write_text(text + f'## Human sign-off\n\nName: {name}\nDate: {date.today().isoformat()}\nDecision: sign off\n')
    state['stage'] = 'complete'
    state['signed_by'] = name
    state['signed_at'] = datetime.now(timezone.utc).isoformat()
    state['review_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(run / 'state.json', state)
    event(run, 'human', 'Human signed off the checked planning pack; this is not an audit conclusion.')
