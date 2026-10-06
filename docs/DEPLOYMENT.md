# Part B: independent harness deployment

The web application lives in `harness/`. It runs without VS Code or Claude Code.
Python builds/validates outputs; an optional Claude Messages API provider supplies
live agent judgments. It is a custom harness, not an emulation of Claude Code's
experimental native team process.

## Current delivery boundary

The application is prepared for the repository
`gengtong0601-hub/procurement-audit-planner`. The repository's Render button opens
free-plan service creation; owner sign-in is required. No hosting account has
been changed and no deployed website URL is claimed before Render creates it.
The local prepared-evidence demonstration
is not proof that Part B's live agent workflow has passed. Complete the live API
and deployed smoke tests below before submitting Part B.

## Local run

Use Python 3.11 or newer (validated with 3.12 locally and 3.13 in Docker). From the project root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m harness.app
```

Open `http://127.0.0.1:8000`. The server binds to loopback for local work.
`runtime/runs/` stores independent workspaces. Each browser run has a random
capability token kept in session storage; it is needed for reads and writes.
Source data and root `outputs/` remain unchanged. Losing the browser's token
means the owner must retrieve the run directly from server storage.

## Two execution modes

**Prepared evidence demonstration** uses the checked-in source extractions,
computed analytics and explicitly labeled draft judgments. The risk register,
human scope revision, sampling, pack rendering, QA and sign-off operate on a
new isolated workspace. Planning and the challenge point use deterministic
teaching templates. This mode makes no live model calls and does not prove
native Claude execution.

**Live Claude API agents** requires three server environment values:

- `ANTHROPIC_API_KEY`: your own API credential; never put it in browser code.
- `ANTHROPIC_MODEL`: a model your account can access; no assumed model is set.
- `HARNESS_ACCESS_TOKEN`: a long private access passphrase that authorizes
  model usage. Enter this passphrase, not the API key, in the website.

The application does not automatically read `.env`. Set these variables in the
hosting dashboard or your shell. `.env.example` documents the names only.

Live flow:

1. Verify the prepared rule extraction against the original PDF. Fresh rule
   extraction via `/extract-rules` is deliberately a separate Part A activity.
2. In parallel, rerun deterministic full-population spend analysis and let the
   findings role extract committee evidence through the Claude API.
3. The risk-assessor role reads Skills and source evidence; Python validates
   citations and calculates ratings. Any invalid response blocks progress.
4. The user explicitly reviews every risk. The harness records reviewer,
   date, changes and a validated revision. No blanket approval is supplied.
5. Planner and challenger exchange bounded rounds through the harness. Python
   builds the pack and draws exact transaction samples. The checker runs four
   reproducible QA scripts. Any failure blocks sign-off.
6. A human reads the pack and explicitly signs. Download includes outputs and
   activity events, without the run token or API credentials.

This independent orchestration is separate from Part A's native Claude
`SendMessage`/teammate lifecycle evidence. Do not describe one as the other.
Source PDFs are public course data. Starting live mode sends the relevant public
evidence, judgment files and recorded review comments to the configured Claude
API service. Do not enter confidential review notes in a public course demo.

## Container deployment

Docker is the portable deployment path:

```bash
docker build -t procurement-audit-studio .
docker run --rm -p 8000:8000 -v audit-runs:/app/runtime procurement-audit-studio
```

The Dockerfile accepts an optional BuildKit `build_ca` secret for an organization's
trusted CA bundle when building behind its HTTPS proxy. Normal hosting needs no
secret. TLS verification remains enabled; the bundle is not stored in the image.

For live mode, provide the three environment variables through the platform's
secret store or `--env-file` from a private untracked file. Use HTTPS at the
hosting platform. The container runs as an unprivileged user. The server uses
one process with eight web threads and at most two background jobs. Do not add
multiple workers without replacing in-memory locks with a shared job queue.

`render.yaml` is a **free-plan** Render blueprint without a persistent disk or
required model credentials. The default prepared workflow is available as soon
as the service is live. Free services can sleep and use ephemeral storage, so
download the pack before a restart or redeploy. Persistence requires a hosting
plan/storage option chosen by the owner; no paid resource is created by this
configuration. Do not deploy the Flask development server as production.

## State and operational limits

- Mount persistent storage at `/app/runtime`; otherwise runs vanish on restart.
- Run count is limited to fifty; archive old runs deliberately on the server.
- Restarting the server during a job leaves a partial run. Start a fresh run;
  job resumption and distributed workers are outside this teaching harness.
- Two jobs at a time and two challenge rounds bound workload. Provider failure,
  malformed JSON, unverified quotes, unresolved challenges or QA errors stop
  the run rather than producing a misleading successful pack.
- Real-account API cost, model availability, network behavior and a hosted
  end-to-end smoke test are unverified without the team's credentials.

## Submission smoke test

1. Publish the repository without `.venv`, `.env`, `runtime`, credentials or
   incidental logs. Include data provenance and the Claude verification record.
2. Deploy the container and check `/health` returns `{"status":"ok"}`.
3. On the actual public URL, start a prepared run; approve/amend/reject explicit
   risks; inspect revision; build; verify QA; sign and download the pack.
4. Configure live credentials and perform the same workflow in **live mode**.
   Check actual provider usage and saved events. Retain evidence of model calls,
   independent roles, blocking failure behavior and output traceability.
5. Test on another device without relying on the developer's local server or
   local files. On the free ephemeral service, download completed packs before
   restarting. If persistent storage is configured, restart and confirm a
   completed run persists.
6. Fill the two final URLs in README. Do not mark the assignment complete while
   native Claude validation or the deployed live workflow remains unverified.
