# Validation record

Validated locally using Python 3.12 and the committed uv lockfile:

- 25 automated tests passed. Coverage includes the complete synthetic workflow, explicit human gates, amendments/rejections, verified quotes and thresholds, credits, rolling-window boundaries, missing/malformed inputs, stale/modified artifacts, budget constraints, mocked model-role contracts and the HTTP API/export.
- Each of the four standalone QA scripts passed against a generated synthetic pack: quotations, numbers, traceability and samples.
- Ruff lint and formatting checks passed; browser JavaScript syntax check passed.
- A real Chromium browser exercised new demo → five risk decisions → generated pack → document/source-row view → explicit return-for-revision review. No JavaScript page errors occurred. A 390-pixel mobile viewport had no horizontal page overflow.
- A Python wheel built successfully and contains the skill packages, agent definitions, templates and static assets.

The automated browser/test decisions are labeled synthetic and do not represent an actual auditor's approval. The human demonstration case remains pending. One upstream Starlette deprecation warning about its current HTTPX test adapter is emitted; no tests fail.

Not validated: live model-provider calls, native Claude Code agent teams, original council datasets, exact replay of all 27 lesson prompts, production hosting or Part B deployment. The GitHub workflow is supplied; local results do not establish that hosted CI has run.
