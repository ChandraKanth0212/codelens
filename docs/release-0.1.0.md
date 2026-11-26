# Proposed v0.1.0 release notes

Status: public launch postponed; not release-ready while live App and browser acceptance remain outstanding; no tag or GitHub Release created. PRD section 11 requires user approval before tagging.

CodeLens is a self-hostable PR review assistant with signed GitHub App ingestion, exact commit tracking, PostgreSQL/Redis/RQ jobs, isolated Ruff/ESLint/detect-secrets, repository-scoped local users, a React review dashboard and optional schema-validated advisory AI. Apache-2.0 licensed.

Quick start: clone, run `python scripts/setup.py`, then `docker compose up --build -d`. Open localhost:8000, sign in with the generated local operator token and run the synthetic sample. See README for App setup and contributor commands.

Verified: backend/frontend tests, lint/format/build, migration round trips, fresh Compose startup, isolated analyzer controls, restart/persistence, synthetic database backup/restore and repeated sample reviews in GitHub Actions. Exact counts and runs are recorded in IMPLEMENTATION_STATUS.md.

Known limits: live App install and paid AI verification not performed; browser visual/mobile/keyboard acceptance and screenshots remain outstanding. One worker recommended; no OAuth, distributed quotas, hosted service, automatic fixes or GitHub posting. Metadata-only AI enriches existing static findings. Treat this as an early beta, not a safety guarantee.

Final acceptance evidence: 73 backend tests (82% local coverage), 6 frontend tests, lint/format/build and migrations passed. [CI 45627845755](https://github.com/ChandraKanth0212/codelens/actions/runs/45627845755) verified application commit `5343193`, including fresh Compose, restart/persistence and isolated PostgreSQL restore. Live App/browser acceptance remains outstanding; no hosted deployment claimed.
