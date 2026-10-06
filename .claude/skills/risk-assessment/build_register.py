#!/usr/bin/env python3
"""Guide step 3.5: validate cited judgments, render register, preserve human gate.
Original implementation; see docs/IMPLEMENTATION_NOTES.md. Python stdlib only.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

CITE = re.compile(r'\[(rule|metric|history):((?:[^\[\]]|\[\d+\])+)\]')
PH = re.compile(r'\{\{(\$[^}]+)\}\}')
PATH = re.compile(r'^\$(?:\.[A-Za-z_][\w-]*|\[\d+\])*$')
RID = re.compile(r'^R-\d{2,}$')
ADVERSE = re.compile(r'limited|weak|unsatisfactory|no assurance|inadequate', re.I)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jpath(obj, path):
    if not PATH.fullmatch(path):
        return False, None
    cur = obj
    try:
        for key, idx in re.findall(r'\.([A-Za-z_][\w-]*)|\[(\d+)\]', path[1:]):
            cur = cur[int(idx)] if idx else cur[key]
        return True, cur
    except (KeyError, IndexError, TypeError):
        return False, None


def history_index(obj, result=None):
    result = result if result is not None else {}
    if isinstance(obj, dict):
        if isinstance(obj.get('id'), str):
            if obj['id'] in result:
                raise ValueError('duplicate history id: ' + obj['id'])
            result[obj['id']] = obj
        for v in obj.values():
            history_index(v, result)
    elif isinstance(obj, list):
        for v in obj:
            history_index(v, result)
    return result


def decisions(path):
    out = {'reviewer': '', 'date': '', 'rows': OrderedDict()}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        if line.startswith('Reviewer:'):
            out['reviewer'] = line.split(':', 1)[1].strip()
        if line.startswith('Date:'):
            out['date'] = line.split(':', 1)[1].strip()
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) >= 6 and RID.fullmatch(c[0]):
            if c[0] in out['rows']:
                raise ValueError('duplicate auditor decision: ' + c[0])
            out['rows'][c[0]] = {'title': c[1], 'now': c[2], 'scope': c[3],
                              'decision': c[4].lower(), 'comment': '|'.join(c[5:]).strip()}
    return out


def safe(text):
    return str(text).replace('|', '/').replace('\n', ' ')


def fmt(value):
    return f'{value:,}' if isinstance(value, int) else f'{value:,.2f}' if isinstance(value, float) else str(value)


def matrix_label(method, likelihood, impact):
    """Accept explicit matrix rows or cells, never infer council cells from products."""
    matrix = method.get('matrix', method.get('combination', {}).get('matrix', []))
    cells = matrix.get('cells', matrix.get('rows', [])) if isinstance(matrix, dict) else matrix
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        if cell.get('likelihood') == likelihood and cell.get('impact') == impact:
            return cell.get('label', cell.get('rating'))
        if cell.get('likelihood') == likelihood and isinstance(cell.get('labels'), list):
            return cell['labels'][impact - 1]
    return None


def compute_rating(method, likelihood, impact):
    score = likelihood * impact
    if not method.get('usable'):
        label = 'Low' if score <= 4 else 'Medium' if score <= 9 else 'High' if score <= 16 else 'Very high'
        return score, label, label, 'Fallback: 1–5 scales; score bands ≤4 Low, ≤9 Medium, ≤16 High, otherwise Very high. Council method unavailable.'
    label = matrix_label(method, likelihood, impact)
    band = None
    for row in method.get('bands', []):
        lo = row.get('min_score', row.get('score_min', row.get('min')))
        hi = row.get('max_score', row.get('score_max', row.get('max')))
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo <= score <= hi:
            if band is not None:
                raise ValueError('overlapping selected risk bands')
            band = row.get('label', row.get('name', row.get('band', row.get('level'))))
    if not label or not band:
        raise ValueError(f'usable council method lacks explicit matrix cell/band for likelihood={likelihood}, impact={impact}')
    return score, label, band, method.get('selection_note', 'Council matrix labels and selected Table 4 score bands are reported separately; any discrepancy must be disclosed in history.json.')


def validate(risk, rule_ids, analytics, histories):
    errors, warnings = [], []
    rid = risk.get('id', '?')
    if not RID.fullmatch(str(rid)):
        errors.append('id must be R- followed by at least two digits')
    for key in ('title', 'statement', 'proposed_focus'):
        if not isinstance(risk.get(key), str) or not risk[key].strip():
            errors.append(key + ' must be nonempty text')
    if not isinstance(risk.get('recommend_in_scope'), bool):
        errors.append('recommend_in_scope must be boolean')
    if not risk.get('recommend_in_scope', True) and not risk.get('scope_reason'):
        errors.append('out-of-scope recommendation requires scope_reason')
    for key in ('likelihood', 'impact'):
        part = risk.get(key, {})
        if not isinstance(part, dict):
            errors.append(key + ' must have score and justification'); continue
        n = part.get('score')
        if type(n) is not int or not 1 <= n <= 5:
            errors.append(key + '.score must be integer 1–5')
        text = part.get('justification', '')
        if not isinstance(text, str):
            errors.append(key + '.justification must be text'); continue
        good = 0
        for kind, ref in CITE.findall(text):
            if kind == 'rule':
                ok = ref in rule_ids
            elif kind == 'history':
                ok = ref in histories
            else:
                found, value = jpath(analytics, ref)
                ok = found and value is not None and not isinstance(value, (list, dict))
            if ok:
                good += 1
            else:
                errors.append(key + ': unresolved citation [' + kind + ':' + ref + ']')
        if not good:
            errors.append(key + ': requires at least one resolved citation')
    for key, text in all_text(risk):
        if key in ('id', 'sample_source', 'theme', 'requested_by', 'history_id'):
            continue
        for ref in PH.findall(text):
            found, val = jpath(analytics, ref)
            if not found or val is None or isinstance(val, (dict, list)):
                errors.append(key + ': unresolved scalar placeholder ' + ref)
        stripped = CITE.sub('', PH.sub('', text))
        if re.search(r'£\s?\d|\b\d+(?:[,.]\d+)*\b', stripped):
            warnings.append(key + ': literal figure in prose; use a metric placeholder')
    uplift = risk.get('repeat_finding')
    if uplift:
        item = histories.get(uplift.get('history_id')) if isinstance(uplift, dict) else None
        base = uplift.get('base_likelihood') if isinstance(uplift, dict) else None
        opinion = item.get('assurance_opinion', item.get('opinion', '')) if item else ''
        if not item or not ADVERSE.search(str(opinion)):
            errors.append('repeat_finding must reference an audit with an adverse assurance opinion')
        if type(base) is not int or not 1 <= base <= 5 or risk.get('likelihood', {}).get('score') != min(5, (base or 0) + 1):
            errors.append('repeat finding must uplift likelihood by one, capped at five')
        if item and ('[history:' + uplift['history_id'] + ']') not in risk.get('likelihood', {}).get('justification', ''):
            errors.append('repeat finding must be cited in likelihood justification')
    return errors, warnings


def all_text(obj):
    if isinstance(obj, dict):
        for key, val in obj.items():
            if isinstance(val, str):
                yield key, val
            else:
                yield from all_text(val)
    elif isinstance(obj, list):
        for val in obj:
            yield from all_text(val)


def check_revision(ratings, kept, baseline, dec):
    errors = []
    current = {r['id']: r for r in kept}
    old = {r['id']: r for r in baseline['risks']}
    excluded = {r.get('id'): r for r in ratings.get('excluded', []) if isinstance(r, dict)}
    rev = ratings.get('revision')
    if not isinstance(rev, dict) or type(rev.get('number')) is not int or rev['number'] < 1:
        return ['recorded decisions require revision.number >= 1']
    changed = {r.get('id'): r for r in rev.get('changes', []) if isinstance(r, dict)}
    if len(changed) != len(rev.get('changes', [])):
        errors.append('revision.changes contains duplicate IDs or malformed entries')
    if set(current) - set(old):
        errors.append('new risks require a new assessment and human review; cannot be introduced during this gate revision')
    for rid, original in old.items():
        row = dec['rows'].get(rid, {})
        action = row.get('decision', '')
        if action not in ('', 'approve', 'amend', 'reject'):
            errors.append(rid + ': decision must be approve/amend/reject'); continue
        if action in ('', 'approve'):
            if current.get(rid) != original:
                errors.append(rid + ': unchanged/approved risk was changed without an amendment')
            if rid in changed:
                errors.append(rid + ': revision lists an unrequested change')
        elif action == 'reject':
            if rid in current or rid not in excluded or not excluded[rid].get('reason'):
                errors.append(rid + ': rejection must remove risk and retain an exclusion reason')
            if not row.get('comment'):
                errors.append(rid + ': rejection needs human reason')
            if changed.get(rid, {}).get('action') != 'rejected':
                errors.append(rid + ': missing rejected revision entry')
        elif action == 'amend':
            if rid not in current or not row.get('comment'):
                errors.append(rid + ': amendment needs retained risk and human comment'); continue
            change = changed.get(rid, {})
            if change.get('action') != 'amended' or not change.get('summary'):
                errors.append(rid + ': missing amended revision entry/summary')
            if current[rid] == original:
                errors.append(rid + ': amendment was not applied')
            for dim in ('likelihood', 'impact'):
                request = re.search(dim + r'(?:\s+score)?\s*(?:to|=|:)?\s*([1-5])\b', row['comment'], re.I)
                if request and current[rid][dim]['score'] != int(request[1]):
                    errors.append(rid + ': requested ' + dim + ' score was not applied')
    if set(changed) - set(old):
        errors.append('revision.changes references an unknown risk')
    if set(dec['rows']) - set(old):
        errors.append('auditor-comments contains a risk not in the original register')
    return errors


def run(a):
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    # Each attempt invalidates prior gate evidence until all artifacts are revalidated.
    gate = out / 'gate-evidence.json'
    gate.write_text(json.dumps({'ready': False, 'reason': 'validation incomplete'}, indent=2) + '\n')
    rating_path = Path(a.ratings)
    ratings = json.loads(rating_path.read_text())
    rules = json.loads(Path(a.rules).read_text())
    analytics = json.loads(Path(a.analytics).read_text())
    history = json.loads(Path(a.history).read_text())
    if not isinstance(ratings, dict) or not isinstance(ratings.get('risks'), list):
        raise ValueError('ratings.risks must be an array')
    if not ratings['risks'] and not ratings.get('revision'):
        raise ValueError('initial ratings.risks must be a nonempty array')
    if not isinstance(rules.get('rules'), list) or not rules['rules']:
        raise ValueError('rules.rules must be a nonempty array')
    if not isinstance(history.get('scoring_method'), dict):
        raise ValueError('history.scoring_method required (use usable:false for a documented gap)')
    if not analytics:
        raise ValueError('analytics must not be empty')
    rules_by_id = {r['rule_id']: r for r in rules['rules']}
    histories = history_index(history)
    comments = out / 'auditor-comments.md'
    dec = decisions(comments)
    kept, failures, warnings, computed = [], [], [], {}
    seen = set()
    for risk in ratings['risks']:
        if not isinstance(risk, dict):
            failures.append('risk must be an object'); continue
        errs, warns = validate(risk, rules_by_id, analytics, histories)
        rid = risk.get('id', '?')
        if rid in seen:
            errs.append('duplicate risk id')
        seen.add(rid)
        warnings += [rid + ': ' + w for w in warns]
        if not errs:
            try:
                computed[rid] = compute_rating(history['scoring_method'], risk['likelihood']['score'], risk['impact']['score'])
            except ValueError as exc:
                errs.append(str(exc))
        if errs:
            failures += [rid + ': ' + e for e in errs]
        else:
            kept.append(risk)
    baseline_path = out / 'risk-baseline.json'
    active = any(r['decision'] for r in dec['rows'].values())
    if active:
        if not baseline_path.exists():
            failures.append('human revision needs the original risk-baseline.json')
        else:
            failures += check_revision(ratings, kept, json.loads(baseline_path.read_text()), dec)
    elif ratings.get('revision'):
        failures.append('revision supplied but no human decisions are recorded')
    if active and (not dec['reviewer'] or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', dec['date'])):
        failures.append('recorded decisions require reviewer and ISO YYYY-MM-DD date')
    def fill(text):
        return PH.sub(lambda m: fmt(jpath(analytics, m[1])[1]), text)
    md = ['# Procurement audit risk register', '']
    if not active:
        md += ['**DRAFT — scope recommendations only; no auditor decisions recorded.**', '']
    rev = ratings.get('revision', {})
    if active and not failures:
        md += [f"*Revision {rev['number']}, following auditor comments by {safe(dec['reviewer'])} dated {safe(dec['date'])}.*", '']
        for change in rev.get('changes', []):
            md.append(f"- {change['id']}: {change['action']} — {safe(change.get('summary', 'Human rejection applied'))}")
    notes = sorted({v[3] for v in computed.values()})
    md += ['', *notes, '', 'Risk indicators to investigate; no finding of wrongdoing is made.', '', '## Summary', '',
           '| Risk | Title | L | I | Score | Matrix label | Band | Auditor override | Proposed scope |',
           '|---|---|---|---|---|---|---|---|---|']
    for r in kept:
        score, label, band, _ = computed[r['id']]
        md.append(f"| {r['id']} | {safe(r['title'])} | {r['likelihood']['score']} | {r['impact']['score']} | {score} | {label} | {band} | {'yes' if r.get('auditor_override') else 'no'} | {'yes' if r['recommend_in_scope'] else 'no'} |")
    for r in kept:
        md += ['', f"## {r['id']}: {safe(r['title'])}", '', fill(r['statement']), '',
               '**Likelihood.** ' + fill(r['likelihood']['justification']), '',
               '**Impact.** ' + fill(r['impact']['justification']), '',
               '**Proposed focus.** ' + fill(r['proposed_focus']), '', '**Evidence.**']
        refs = sorted(set(CITE.findall(json.dumps(r))))
        for kind, ref in refs:
            if kind == 'rule':
                src = rules_by_id[ref]
                md.append(f'- [rule:{ref}] clause {src.get("clause", "?")}, p. {src.get("page", "?")}: "{safe(src["verbatim_quote"])}"')
            elif kind == 'metric':
                md.append(f'- [metric:{ref}] {fmt(jpath(analytics, ref)[1])}')
            else:
                src = histories[ref]
                md.append(f'- [history:{ref}] {safe(src.get("source", src.get("source_document", "See history.json")))}; page {safe(src.get("pdf_page", src.get("page", src.get("source_page", "see cited item"))))}')
    md += ['', '## Excluded', '']
    md += [f"- {x.get('id', 'Theme')}: {safe(x.get('reason', ''))}" for x in ratings.get('excluded', [])]
    md += ['- Validation: ' + f for f in failures]
    md += ['', '## Auditor decisions', '', 'No decisions recorded; the auditor must complete auditor-comments.md.' if not active else 'Recorded decisions:']
    if active:
        md += [f"- {rid}: {r['decision'] or 'undecided'} — {safe(r['comment'])}" for rid, r in dec['rows'].items()]
    if failures or warnings:
        md += ['', '**VALIDATION BLOCKED — not ready for approval or planning.**']
    register = out / 'risk-register.md'
    register.write_text('\n'.join(md) + '\n')
    rows = OrderedDict(dec['rows'])
    for r in kept:
        score, label, _, _ = computed[r['id']]
        old = rows.get(r['id'], {})
        rows[r['id']] = {'title': r['title'], 'now': f'{score} / {label}', 'scope': 'yes' if r['recommend_in_scope'] else 'no', 'decision': old.get('decision', ''), 'comment': old.get('comment', '')}
    lines = ['# Auditor decisions', '', 'Reviewer: ' + dec['reviewer'], 'Date: ' + dec['date'], '',
             'Complete each Decision with approve, amend, or reject. Amend/reject requires a comment. Only the human auditor supplies decisions.', '',
             '| Risk | Title | Current rating | Proposed scope | Decision | Comment |', '|---|---|---|---|---|---|']
    lines += ['| ' + ' | '.join(safe(v) for v in (rid, r['title'], r['now'], r['scope'], r['decision'], r['comment'])) + ' |' for rid, r in rows.items()]
    comments.write_text('\n'.join(lines) + '\n')
    clean = not failures and not warnings
    if clean and not active:
        baseline_path.write_text(json.dumps({'risks': kept}, indent=2) + '\n')
    closed = clean and active and bool(rows) and all(r['decision'] in ('approve', 'amend', 'reject') for r in rows.values())
    gate.write_text(json.dumps({'ready': closed, 'revision': rev.get('number'),
                               'sha256': {str(p.resolve()): digest(p) for p in (rating_path, register, comments, Path(a.rules), Path(a.analytics), Path(a.history))},
                               'reason': 'All recorded human decisions applied' if closed else 'Risk validation or human decisions incomplete'}, indent=2) + '\n')
    for f in failures:
        print('FAIL', f)
    for w in warnings:
        print('WARN', w)
    print(f'SUMMARY risks kept: {len(kept)}, excluded by validation: {len(ratings["risks"]) - len(kept)}, failures={len(failures)}, warnings={len(warnings)}, gate={"closed" if closed else "open"}')
    return 0 if clean else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('ratings', nargs='?', default='outputs/risk-ratings.json')
    ap.add_argument('--rules', default='outputs/rules.json')
    ap.add_argument('--analytics', default='outputs/analytics.json')
    ap.add_argument('--history', default='outputs/history.json')
    ap.add_argument('--out-dir', default='outputs')
    a = ap.parse_args()
    try:
        return run(a)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('FAIL input:', str(exc))
        return 1


if __name__ == '__main__':
    sys.exit(main())
