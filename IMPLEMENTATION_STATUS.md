# Implementation status

## Baseline and delivery
- Final-completion baseline: `5fe39b5af45e5b390e48d1d5e4933896a222650f`, clean local main matched remote; CI [45626204960](https://github.com/ChandraKanth0212/codelens/actions/runs/45626204960) passed.
- Repository: https://github.com/ChandraKanth0212/codelens — public, existing Apache-2.0 preserved. No force pushes, tags or GitHub Releases.
- Versions agree: Python package, API and frontend are 0.1.0. Draft notes: docs/release-0.1.0.md.

## Implemented and verified
- Signed App webhooks, delivery/head-SHA idempotency, opened/synchronize/reopened, durable PostgreSQL outbox/Redis RQ, immutable commit retrieval, bounded API retries/pagination.
- Ruff/ESLint/detect-secrets, exclusions and resource budgets, offline non-root analyzer container, normalized/deduplicated findings, optional metadata-only advisory AI (off by default).
- Repository-scoped authentication, dashboard and feedback, migrations, contributor/security docs and private vulnerability reporting.
- Dedicated public synthetic test PRs: https://github.com/ChandraKanth0212/codelens-validation/pull/1 and /pull/2. Anonymous public-API retrieval and real analyzers found six expected rules; evidence in docs/validation-evidence.json. This is not live App authentication verification.
- Final local backend run: **73 passed, 82% coverage**. Includes signed webhook -> RQ -> real analyzers -> stored report/API fixtures, mixed rename/delete/exclusion/oversize handling, analyzer timeout redaction, bounded retries and stale-generation callbacks.
- Full frontend suite: **6 passed**. Backend/frontend lint and formatting, frontend production build, and SQLite migration upgrade/downgrade/upgrade all passed.

## Final self-hosting work
- Added scripts/container_smoke.py and CI checks for API/frontend serving, reports surviving stop/start, new analysis after restart, and PostgreSQL dump/restore into a separate database.
- Added backup/restore/restart operator commands to docs/deployment.md; ignored backup directories/dumps. Existing App setup guide covers minimal permissions, safe credentials, webhook ingress and real-event acceptance.
- Docker unavailable locally. Enhanced container checks must pass in GitHub Actions before being reported as verified.

## Exact verification commands
- `ruff check .`; `ruff format --check .`
- `pytest --cov=codelens --cov-report=term-missing`
- `npm test --prefix web`; `npm run lint --prefix web`; `npm run format:check --prefix web`; `npm run build --prefix web`
- `alembic upgrade head`; `alembic downgrade base`; `alembic upgrade head` against an isolated SQLite validation database.
- CI: `docker compose up --build -d --wait`; real smoke script; stop/start and repeat; `pg_dump`, `createdb`, `pg_restore` and restored finding-count comparison. See .github/workflows/ci.yml for exact commands.

## Outstanding acceptance and release
- No live App credentials/configured .env: App ID, private-key path, matching webhook secret, installation/repository registration and reachable webhook endpoint needed. Follow docs/github-app-setup.md; never paste secret values into chat.
- Browser visual/mobile/keyboard QA remains unavailable: saved browser-origin permission denied localhost and explicitly prohibits workarounds. Prior attempt documented; no rendered-app inspection or screenshots claimed. Frontend tests/build are not visual QA.
- No hosted demo or paid AI call performed. Hosting is optional and does not block self-hosted delivery.
- One existing Starlette/httpx TestClient deprecation warning; no failing local tests. One worker recommended; production lease fencing and exact distributed quotas remain deferred.
- v0.1.0 candidate is prepared for owner review with these limitations. Full beta acceptance remains pending live App/browser checks. Do not tag or publish a Release without separate owner approval.
