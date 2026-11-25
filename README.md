# CodeLens

[![CI](https://github.com/ChandraKanth0212/codelens/actions/workflows/ci.yml/badge.svg)](https://github.com/ChandraKanth0212/codelens/actions/workflows/ci.yml)

**Understand every change. Review with confidence.**

An open-source, self-hosted pull request review assistant. CodeLens runs deterministic checks on changed Python, JavaScript, and TypeScript code and presents evidence in a focused review workspace. Optional AI explains rule metadata; humans make every decision.

**Status:** 0.1.0 untagged beta. Repository-scoped local user access. A reproducible demo is included. Live GitHub App setup requires your credentials; this repository does not claim production adoption or a completed third-party security audit.

## What works

- HMAC-SHA256 GitHub webhooks, repository/installation authorization, delivery and commit deduplication.
- A PostgreSQL outbox, Redis/RQ queue, background worker, bounded crash recovery, explicit run states, and retention cleanup.
- Commit-pinned source retrieval, added-line mapping, path validation, generated/sensitive file exclusions, and byte/file limits.
- Real Ruff and ESLint adapters with fixed configuration. No PR scripts, project plugins, or repository dependencies are executed.
- Selected offline detect-secrets detectors with redacted results. This is **not** a comprehensive secrets scanner.
- React dashboard with review selection, filters, severity labels, feedback, integration status, and light/dark themes.
- Optional, schema-validated AI advisory findings using rule metadata and opaque locations. Disabled by default.
- Authentication, database migrations, automated tests, Docker Compose, and GitHub Actions.

## Quick start: Docker

Requirements: Docker Engine with Compose v2, Python 3.11+ for the secret-generation helper.

```sh
git clone https://github.com/ChandraKanth0212/codelens.git
cd codelens
python scripts/setup.py
docker compose up --build -d
```

Open **http://localhost:8000**. Copy `CODELENS_ADMIN_TOKEN` from your local `.env`, sign in, and select **Run sample review**. The worker reviews synthetic Python and TypeScript files through the real adapters. You should see an undefined Python name, `eval`, an unused import, a TypeScript unused variable, and loose equality. The sample is labelled and contains no real repository or credential data.

```sh
docker compose logs worker
docker compose down
```

The local Compose database password is a development-only value on an unexposed database service. For deployment, replace it, terminate HTTPS at a reverse proxy, and follow [SECURITY.md](SECURITY.md). GitHub Actions verifies fresh Compose startup and synthetic reviews. Live App integration still requires your credentials and validation.

## Quick start: without Docker

Requirements: Python 3.13, Node.js 22.13+, npm. Redis 7 is used by Compose/RQ, not the direct development worker. Docker Compose is the recommended setup; the direct worker below is a developer-only shortcut without RQ isolation.

```sh
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -c requirements.lock -e '.[dev]'
npm ci --prefix analyzer
npm ci --prefix web
python scripts/setup.py
alembic upgrade head
npm run build --prefix web
uvicorn codelens.api:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a second terminal, activate the same virtual environment and run from the repository root:

```sh
python -m codelens.worker
```

The Python environment must be activated so the worker can locate `ruff`. SQLite is suitable for one local worker. Use PostgreSQL for deployment or multiple workers. For frontend development, run `npm run dev --prefix web`; Vite proxies `/api` to port 8000.

## Repository access

The bootstrap operator connects repositories. Provision a reviewer or repository owner through the [local access CLI](docs/architecture/0010-repository-access.md). User tokens are hashed at rest and remain only in browser memory. Reviewers read assigned repositories and record feedback; owners also configure/delete them. Use HTTPS for non-loopback access.

## Connect GitHub

Follow the [complete GitHub App setup and live-validation guide](docs/github-app-setup.md), including prepared Python/TypeScript test PRs.

1. Create a GitHub App with read-only **Contents**, **Pull requests**, and **Metadata** permissions. Subscribe to **Pull request** events. No write permissions are needed.
2. Set its webhook URL to `https://YOUR-HOST/api/v1/webhooks/github` and use the value of `CODELENS_WEBHOOK_SECRET`. Keep the dashboard private behind HTTPS.
3. Install the App on a selected repository. Record the installation ID from its installation URL.
4. Set `CODELENS_GITHUB_APP_ID`, `CODELENS_GITHUB_PRIVATE_KEY_PATH`, and `CODELENS_ALLOWED_REPOSITORIES=owner/repo` in `.env`. The private key is a file outside Git; never commit it.
5. For Docker, mount the key read-only in the **worker** using a Compose override (see [deployment guide](docs/deployment.md)). Restart services after environment changes.
6. In **Repositories**, enter `owner/repo` and its installation ID. Open a small PR or push a new commit. The dashboard polls every four seconds.

Run metadata records the exact head SHA. If the head changes during retrieval, that run fails safely; the synchronize event creates a new run. GitHub deliveries are idempotent for the retention window. Retry rejected queue-full deliveries manually from GitHub's delivery page.

## Configuration

`.codelens.yml` on the PR's **base commit** can narrow the operator configuration. PR changes cannot grant access, enable AI, add analyzers, or increase limits. Unknown configuration keys are rejected.

```yaml
version: 1
enabled: true
include: ["*"]
exclude: ["tests/*", "generated/*"]
analyzers: [ruff, eslint, secrets]
ai_enabled: false
max_files: 20
max_file_bytes: 100000
max_total_bytes: 500000
max_processing_seconds: 120
severity_threshold: info
github_feedback_enabled: false
```

Patterns use case-sensitive Python `fnmatch` against repository-relative paths. Hard exclusions cannot be overridden. The total-byte limit counts source plus patches; missing/binary patches are skipped. Binary, oversized and unsupported-encoding files are recorded as skipped. Total-byte or count overflow fails retrieval. The repository config API replaces the complete configuration, applying defaults to omitted fields.

## Optional AI

Set `CODELENS_AI_ENABLED=true`, configure `CODELENS_AI_KEY` and a compatible `CODELENS_AI_MODEL`, and enable AI for the repository. If a base `.codelens.yml` exists, it must also allow AI. The adapter sends **only analyzer/rule/severity metadata, opaque file aliases and line ranges**, never source, diffs, real paths, secret matches, or PR titles. Limits: 30 eligible findings, 1200 output tokens, a 20-second timeout and zero paid-request retries. Returned locations must match approved diff lines. Responses are validated and rendered as plain text labelled advisory. Provider failure produces a partial report while preserving deterministic findings. Provider retention is governed by your account terms. No automatic fixes or GitHub writes exist in this release.

## Development and tests

```sh
ruff check .
ruff format --check .
pytest --cov=codelens --cov-report=term-missing
npm test --prefix web
npm run build --prefix web
```

The Python suite covers signed webhooks, authorization, queue deduplication/recovery, diff mapping, real Ruff/ESLint execution, redaction, AI schema/data boundaries, GitHub retrieval limits, feedback persistence, deletion, and retention. External HTTP calls are mocked in tests. CI additionally builds Compose and runs the synthetic review inside the containers.

## Verification

CI builds Compose, starts PostgreSQL/Redis/RQ, verifies analyzer network and credential isolation, and runs the sample twice. Tests cover signed webhook to persisted report, real adapters, authorization and dashboard interactions with synthetic data. See [implementation status](IMPLEMENTATION_STATUS.md) for evidence.

Browser visual verification and screenshots remain outstanding after a browser-tool denial. No live App installation, paid AI call, hosted demo, performance benchmark or external security audit is claimed.

## Architecture

```mermaid
flowchart LR
  G[GitHub pull request] --> H[Signed webhook API]
  H --> DB[(PostgreSQL / local SQLite)]
  DB --> Q[Dispatcher / Redis RQ]
  Q --> W[Background worker]
  W --> GH[GitHub App read-only API]
  W --> A[Offline Ruff / ESLint / detect-secrets]
  A --> DB
  A -. opt-in rule metadata .-> AI[AI explanation adapter]
  AI --> DB
  DB --> UI[Authenticated React dashboard]
```

The API, worker, and adapters share a modular Python package. PostgreSQL stores a durable job outbox; a dispatcher enqueues committed runs into Redis/RQ. Redis never receives source code or tokens. See [current architecture decision](docs/architecture/0007-unified-prd-foundation.md), [security boundaries](SECURITY.md), and [implementation status](IMPLEMENTATION_STATUS.md).

## Contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [ROADMAP.md](ROADMAP.md). Small, reproducible fixes are welcome. Candidate first issues include filter UI tests, expanded diff fixtures, and analyzer documentation. Report sensitive vulnerabilities privately using GitHub private vulnerability reporting (enabled for this repository).

## Portfolio use

This is an original project, not evidence of a contribution accepted by another project's maintainer. Use the [portfolio guide](docs/portfolio.md) for accurate resume bullets, a demo script, and GitHub publishing steps. Add real measurements and links only after you have collected them.

Licensed under [Apache-2.0](LICENSE). CodeLens assists human review; it does not guarantee defect or vulnerability detection.
