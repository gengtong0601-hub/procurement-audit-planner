"""Flask API and UI. Run: python -m harness.app. Production: gunicorn harness.app:app."""
import hmac
import io
import json
import os
import re
import secrets
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from . import provider, workflow

ROOT = workflow.ROOT
app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=100_000, RUN_ROOT=ROOT / 'runtime/runs')
pool = ThreadPoolExecutor(max_workers=2)
jobs = threading.BoundedSemaphore(2)
locks = {}
locks_guard = threading.Lock()


@app.after_request
def response_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'"
    return response


@app.errorhandler(ValueError)
def invalid(error):
    return jsonify(error=str(error)), 400


def require_live_access():
    expected = os.environ.get('HARNESS_ACCESS_TOKEN', '')
    actual = request.headers.get('Authorization', '').removeprefix('Bearer ')
    if not expected or not hmac.compare_digest(expected, actual):
        raise ValueError('Live mode needs the server access passphrase. Prepared mode remains available.')


def object_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError('Request body must be a JSON object.')
    return payload


def locate(run_id):
    if not re.fullmatch(r'[a-f0-9]{32}', run_id):
        raise ValueError('Invalid run identifier.')
    path = Path(app.config['RUN_ROOT']) / run_id
    if not (path / 'state.json').exists():
        raise ValueError('Run not found. Start a new review.')
    # An unguessable per-run capability is needed for read and write access.
    state = workflow.read_json(path / 'state.json')
    token = request.headers.get('X-Run-Token', '')
    if not hmac.compare_digest(state.get('access_token', '!'), token):
        raise ValueError('This run requires its private review token.')
    return path


def background(run, operation):
    try:
        operation(run)
    except Exception as exc:
        state = workflow.read_json(run / 'state.json')
        state.update(stage='blocked', error=str(exc))
        workflow.write_json(run / 'state.json', state)
        workflow.event(run, 'harness', 'Workflow stopped; see the displayed error. No sign-off allowed.')
    finally:
        jobs.release()


@app.get('/')
def index():
    return render_template('index.html')


@app.get('/health')
def health():
    return jsonify(status='ok')


@app.get('/api/config')
def configuration():
    missing = [p for p in ('rules.json', 'history.json', 'analytics.json', 'risk-ratings.json') if not (ROOT / 'outputs' / p).exists()]
    return jsonify(live_available=provider.available() and bool(os.environ.get('HARNESS_ACCESS_TOKEN')),
                   prepared_available=not missing, missing=missing)


@app.post('/api/runs')
def start():
    payload = object_payload()
    mode = payload.get('mode', 'prepared')
    if mode not in ('prepared', 'live'):
        raise ValueError('Choose prepared or live mode.')
    if mode == 'live':
        require_live_access()
        if not provider.available():
            raise ValueError('Configure the API key and model on the server first.')
    run_root = Path(app.config['RUN_ROOT'])
    run_root.mkdir(parents=True, exist_ok=True)
    if len(list(run_root.iterdir())) >= 50:
        raise ValueError('This teaching deployment has reached its run limit. Ask its owner to archive old runs.')
    if not jobs.acquire(blocking=False):
        raise ValueError('The server is running two workflows. Please try again after one completes.')
    run_id, token = secrets.token_hex(16), secrets.token_urlsafe(32)
    run = run_root / run_id
    try:
        workflow.create_workspace(run, mode)
        state = workflow.read_json(run / 'state.json')
        state['access_token'] = token
        workflow.write_json(run / 'state.json', state)
        pool.submit(background, run, workflow.initialise)
    except Exception:
        jobs.release()
        raise
    return jsonify(id=run_id, token=token), 202


@app.get('/api/runs/<run_id>')
def status(run_id):
    run = locate(run_id)
    state = workflow.read_json(run / 'state.json')
    state.pop('access_token', None)
    out = run / 'outputs'
    ratings = workflow.read_json(out / 'risk-ratings.json') if (out / 'risk-ratings.json').exists() else {'risks': []}
    analytics = workflow.read_json(out / 'analytics.json')
    history = workflow.read_json(out / 'history.json')
    builder = workflow.module_at(run, '.claude/skills/risk-assessment/build_register.py')
    def fill_metrics(text):
        def replace(match):
            found, value = builder.jpath(analytics, match.group(1))
            if not found:
                return '[unresolved metric]'
            return format(value, ',') if isinstance(value, (int, float)) and not isinstance(value, bool) else str(value)
        return builder.PH.sub(replace, text)
    visible_risks = []
    for risk in ratings.get('risks', []) if isinstance(ratings.get('risks'), list) else []:
        try:
            score, matrix_label, band, _ = builder.compute_rating(history['scoring_method'], risk['likelihood']['score'], risk['impact']['score'])
            risk.update(computed_score=score, matrix_label=matrix_label, risk_band=band)
            risk['display_likelihood'] = fill_metrics(risk['likelihood']['justification'])
            risk['display_impact'] = fill_metrics(risk['impact']['justification'])
            visible_risks.append(risk)
        except (KeyError, TypeError, ValueError, AttributeError):
            # A failed live response must leave the error/status readable.
            # The builder reports the reason and prohibits human approval.
            continue
    events = [json.loads(line) for line in (run / 'events.jsonl').read_text().splitlines() if line]
    return jsonify(**state, risks=visible_risks, population=analytics.get('population', {}),
                   events=events, documents=sorted(p.name for p in out.glob('*.md')),
                   parameters=workflow.read_json(out / 'rules.json').get('parameters', {}))


@app.post('/api/runs/<run_id>/decisions')
def decisions(run_id):
    run = locate(run_id)
    with locks_guard:
        lock = locks.setdefault(run_id, threading.Lock())
    with lock:
        workflow.apply_decisions(run, object_payload())
    return jsonify(status='approved')


@app.post('/api/runs/<run_id>/plan')
def plan(run_id):
    run = locate(run_id)
    with locks_guard:
        lock = locks.setdefault(run_id, threading.Lock())
    with lock:
        state = workflow.read_json(run / 'state.json')
        if state['stage'] != 'approved':
            raise ValueError('Complete every risk decision before planning.')
        if state['mode'] == 'live':
            require_live_access()
        if not jobs.acquire(blocking=False):
            raise ValueError('The server is busy. Try again shortly.')
        # Separate busy marker blocks duplicate dispatch while preserving the
        # state expected by build_plan. The API refuses a second submission.
        if state.get('planning_started'):
            jobs.release()
            raise ValueError('Planning is already running.')
        state['planning_started'] = True
        workflow.write_json(run / 'state.json', state)
        pool.submit(background, run, workflow.build_plan)
    return jsonify(status='planning'), 202


@app.post('/api/runs/<run_id>/signoff')
def signoff(run_id):
    run = locate(run_id)
    with locks_guard:
        lock = locks.setdefault(run_id, threading.Lock())
    with lock:
        workflow.sign_off(run, object_payload().get('name'))
    return jsonify(status='complete')


@app.get('/api/runs/<run_id>/documents/<name>')
def document(run_id, name):
    run = locate(run_id)
    allowed = {'risk-register.md', 'auditor-comments.md', 'planning-memo.md', 'risk-control-matrix.md',
               'audit-program.md', 'challenges.md', 'review.md'}
    if name not in allowed or not (run / 'outputs' / name).is_file():
        raise ValueError('Document not available at this stage.')
    return jsonify(name=name, text=(run / 'outputs' / name).read_text())


@app.get('/api/runs/<run_id>/download')
def download(run_id):
    run = locate(run_id)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted((run / 'outputs').rglob('*')):
            if file.is_file():
                archive.write(file, file.relative_to(run))
        archive.write(run / 'events.jsonl', 'events.jsonl')
        state = workflow.read_json(run / 'state.json')
        state.pop('access_token', None)
        archive.writestr('run-status.json', json.dumps(state, indent=2))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='audit-planning-pack.zip', mimetype='application/zip')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '8000')), debug=False)
