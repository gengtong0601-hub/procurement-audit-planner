# Local validation record

Prepared on 2026-10-05 (America/Los_Angeles). This record covers the local
implementation, not native Claude execution, a live API run or deployment.

## Cloud deployment preparation — 2026-10-06

- Imported the supplied handoff; all nine original data files still match the
  SHA-256 manifest.
- Fixed PDF verification portability: rule and history quote checks now always
  use the pinned pypdf extractor. Installing Poppler no longer changes the text
  ordering or creates false source failures.
- **42 tests passed** on Python 3.12.14 (the original 40 plus two regression tests
  with an incompatible `pdftotext` deliberately present on PATH).
- Gunicorn and Chromium: healthy response, prepared review with eight risks,
  visible human-review controls, and no browser JavaScript errors. No real risk
  decision or auditor sign-off was entered.
- Docker image built with Python 3.13. The cloud network required its proxy and
  trusted CA bundle, supplied as an ephemeral BuildKit secret; TLS verification
  stayed enabled. The resulting container ran as UID 1000, returned a successful
  health response and initialized a prepared run to the eight-risk human gate.
- Render blueprint selects the free Docker service without a paid disk or
  mandatory model credentials. Public deployment and external-device verification
  remain pending the owner's Render account and service creation.

This compatibility fix does not change the number checker's existing limitation:
matching a value in evidence is not proof that prose assigned it to the correct
metric. Human review must still check numerical meaning and context.

The sections below preserve the original handoff validation record.

## Automated tests

Final command:

```bash
.venv/bin/python -m pytest -q --basetemp runtime/test-temp
```

**40 passed**: 18 spend/data cases, 12 risk/gate cases, 10 harness cases.
Full result: `docs/qa/test-results.txt`.

Meaningful cases include moving Excel headers, explicit dates, packed
multi-supplier notices, uppercase buyer identity, exact versus near matching,
amount/window boundaries, unresolved parameters, missing input, decision
completeness, real score amendments, rejections, empty approved scope, stale
source inputs, changed plans, malformed JSON, private run tokens and safe
exports. A complete prepared workflow uses copied real evidence and all eight
draft risks, draws samples, passes all four QA checks and signs only as an
explicitly synthetic test reviewer. Tests assert the root human decisions
remain unchanged.

The provider adapter has mocked-response contract tests. No real provider
credential was used. Mocks are not represented as live model verification.

## Source and calculation checks

- Nine original data files match the stored SHA-256 manifest.
- Rule checker: 80 rules, 81 exclusions, four unresolved parameters;
  **ALL CHECKS PASSED**, zero warnings.
- History checker: 106 source-linked items, 81 quotations, four source
  documents; **ALL CHECKS PASSED**.
- Seven independent spot-checks reconcile flagged transactions directly to
  workbook rows and independently recompute selected source totals.
- Register builder: eight risks, zero failures and zero warnings.
- The genuine scope gate intentionally exits with failure: reviewer/date and
  every human decision remain blank, and no approved revision is asserted.

Detailed output: `docs/qa/source-and-gate-checks.txt`. The original input data
was not edited. PDF text and selected source-page images are in
`docs/reference/`; visual checks are listed in `EXTRACTION_NOTES.md`.

## Browser checks

The local application at `http://127.0.0.1:8000` was inspected through a real
browser. The initial page rendered correctly at its default viewport. Starting
a prepared run displayed the correct population, eight risks, unresolved
parameter notice, role activity and working documents. Metric placeholders in
rating justifications resolved to Python-computed values. Blank human input
was rejected. The New review action returned to the start screen. No real
reviewer decision or sign-off was entered through the browser.

JavaScript syntax passed `node --check harness/static/app.js`. No mobile-device
or cross-browser matrix is claimed.

## Outstanding verification

- Teammate: native Claude skill discovery/invocation, actual subagent runs,
  project memory, team messaging/lifecycle and the step-by-step evidence log.
- Human auditor: source spot-checks, unresolved thresholds if needed, every
  risk decision, treatment of open review points, final sign-off.
- Deployment owner: API credentials/model access, real live workflow,
  container build, hosted persistence and external-device smoke test.
- Submitter: publish repository and deployment, then enter their actual URLs.

Docker was unavailable locally, so no container-build success is claimed.
The website's browser checkboxes were not used to certify unperformed Claude
steps. See `CLAUDE_VERIFICATION.md` and `DEPLOYMENT.md` for concrete instructions.
