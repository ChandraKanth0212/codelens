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
- Latest local backend run: **75 passed, 83% coverage**. Includes signed webhook -> RQ -> real analyzers -> stored report/API fixtures, mixed rename/delete/exclusion/oversize handling, analyzer timeout redaction, bounded retries and stale-generation callbacks.
- Full frontend suite: **6 passed**. Backend/frontend lint and formatting, frontend production build, and SQLite migration upgrade/downgrade/upgrade all passed.

## Final self-hosting work
- Added scripts/container_smoke.py and CI checks for API/frontend serving, reports surviving stop/start, new analysis after restart, and PostgreSQL dump/restore into a separate database.
- Added backup/restore/restart operator commands to docs/deployment.md; ignored backup directories/dumps. Existing App setup guide covers minimal permissions, safe credentials, webhook ingress and real-event acceptance.
- Docker unavailable locally. Enhanced checks **passed in CI [45627845755](https://github.com/ChandraKanth0212/codelens/actions/runs/45627845755) at `5343193`**: fresh Compose startup, API/frontend serving, offline/non-root/read-only analyzer and CPU/memory/PID limits, real reviews before/after stop-start, retained reports, and PostgreSQL backup/isolated restore with matching finding counts. Both test and container jobs passed.
- Staged changes reviewed with `git diff --cached --check`; no forbidden credential/database artifacts or matches from selected credential detectors. Working source preserved, no dependency additions.

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
- **Not release-ready.** Public launch is postponed. Live App/browser acceptance remains pending; no tag, Release or announcement is authorized.


## Release-readiness audit — 2026-11-26
- Baseline `ceb01ac` matched remote main with clean tree; CI 45628519486 passed. Public launch is postponed; no tag, Release or announcement authorized. **Not release-ready** until every acceptance check below has evidence.
- Live App task paused: no local .env/App ID/key path/webhook secret/allowlist. Need safe local configuration, installation ID/registration and reachable webhook endpoint. Existing public PR tests do not prove App authentication/delivery.
- Browser task paused: saved origin-denial policy has not been lifted; no workaround or rendered desktop/mobile inspection claimed. Exact origin required: http://127.0.0.1:8000.
- Security review found example credentials were accepted if .env.example was copied directly. Added fail-closed validation and redacted validation errors, with regression tests. Also excluded backups/dumps/local overrides from Docker build context. 75 backend tests passed (83% coverage); all 6 frontend tests and frontend lint/format/build passed.
- Fresh ephemeral Ubuntu CI covers clean checkout, Docker build/startup, persistence/restart and isolated restore. Local Docker remains unavailable; other OS installation coverage is not claimed.

- Operator explicitly paused live App and browser QA on 2026-11-26 until local configuration and browser permission are supplied; continue independent work only. No credentials requested or stored in chat.

- Python advisory review: upgraded developer pytest to 9.0.3 for CVE-2025-71176. Re-audit of all 51 pinned packages: zero known advisories, zero skipped packages. Full npm audits (including development dependencies) also report zero advisories. See docs/security-review-2026-11-26.json for scope/limitations.
- Source review and selected offline credential-pattern scan found no tracked secret/database artifacts or detector matches. This is not comprehensive detection or an independent security certification.


## Current acceptance evidence (2026-11-26)

| Criterion | State and evidence |
| --- | --- |
| Real App installation / PR review | **Paused, unverified** by operator instruction. Await safe local configuration and installation/endpoint details. |
| Webhooks / background processing | **Verified in fixtures and Compose**: signed events, deduplication, RQ dispatch, real analyzers, persisted reports, retry limits. Actual GitHub delivery remains part of the paused App check. |
| Desktop / mobile browser QA | **Paused, unverified** until browser origin access is explicitly permitted. No workaround or visual-pass claim. |
| Fresh Docker installation | **Verified on fresh Ubuntu GitHub runner with Docker preinstalled**: clean checkout without .env, generated configuration, build/startup, serving frontend/API, isolation, restart/persistence, backup/restore. Windows/macOS Docker installation not tested. |
| Security / privacy | **Internal review completed and fixes verified**; known template secrets rejected, settings errors redacted, private build-context files excluded, developer dependency advisory patched. Audits: 51 Python pins and both npm trees report zero known advisories. Not an independent penetration test or container OS audit. |
| Documentation / onboarding | **Updated** setup diagnostics, release hold, security findings and evidence. Commands exercised by CI; human/browser onboarding remains unverified. |
| Regression / CI | **Passed**: 75 backend tests, 6 frontend tests, lint/format/build, migrations and container checks. [CI 45793044102](https://github.com/ChandraKanth0212/codelens/actions/runs/45793044102) verified implementation commit `4c44086`. |

No tag, GitHub Release or announcement created. Only source and acceptance documentation were pushed. Remaining gating work resumes when the operator supplies configuration/access; no new product features are needed.
