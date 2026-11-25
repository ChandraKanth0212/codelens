# Architecture decisions

## ADR-001: Modular monolith

**Accepted.** FastAPI serves the API and built React/TypeScript assets. A separately started worker imports the same Python modules. SQLAlchemy handles persistence and Alembic records schema history. This keeps deployments understandable while preserving adapter boundaries. There is no user-code execution service.

## ADR-002: Durable SQL queue instead of Redis + RQ

**Accepted deviation from the suggested stack.** ReviewRun rows are jobs. A signed webhook transaction persists its delivery and job together. PostgreSQL workers claim queued rows using `FOR UPDATE SKIP LOCKED`; the SQLite demo uses a conditional status update. This removes the failure gap between committing a database row and enqueueing in another service. Worker processes do not run inside HTTP handlers.

The worker recovers jobs idle for 15 minutes, up to three attempts. Configured per-file subprocess timeouts and small default limits keep normal runs short. Multiple workers are supported on PostgreSQL, but lease renewal and strong fencing for exceptionally long runs are future work; run one worker for this beta. Queue admission counts queued/running rows with a configured soft cap (100). Concurrent webhook transactions may briefly exceed that soft cap. It is not a distributed quota or public internet rate limiter.

## ADR-003: One authenticated operator

**Accepted MVP simplification.** A high-entropy bearer token grants access to all registered repositories in one deployment. It is held only in browser memory. GitHub webhooks use an independent HMAC secret and require both an operator allowlist and registered installation ID. This is not multi-user tenancy, GitHub OAuth, or per-user RBAC. Do not share one deployment between unrelated organizations.

## ADR-004: Fixed analyzer policy

**Accepted.** Ruff runs with `--isolated` and fixed rules. ESLint uses `overrideConfigFile: true` and an embedded trusted configuration. No files from the PR are written or executed; text is passed through stdin. Project ESLint plugins/configs and Python import paths are never loaded. Output is reduced to rule and line metadata to avoid retaining secrets or source identifiers. Findings outside added lines are discarded; duplicates use a stable SHA256 fingerprint.

Compose runs the worker non-root with dropped capabilities, a read-only filesystem, CPU/memory/PID limits, and a bounded temp filesystem. This is worker-level isolation, not a per-analyzer network namespace. The worker needs GitHub access. Analyzer child environments omit application credentials, but subprocesses are not a complete security boundary against parser exploits. Strong per-process/container sandboxing with network denied is a pre-production hardening task.

## ADR-005: Evidence-only AI

**Accepted scope reduction.** The first adapter explains deterministic rule IDs rather than inventing findings from source. A provider Protocol allows substitution. The HTTP call has a 20-second timeout, bounded input/output, and strict response validation. No retries are attempted for AI calls. Raw response bodies/errors are not persisted. AI summaries cannot introduce inline locations because they are not modeled as findings.

## ADR-006: Privacy and retention

**Accepted.** Persist PR metadata, exact SHAs, normalized findings, feedback, run errors, and delivery IDs. Source and diffs are transient. Reports deliberately omit code excerpts. Credential matching only emits a redacted placeholder. Cleanup deletes terminal runs older than 30 days by default; repository deletion removes associated rows and is refused during active jobs. Backups follow operator policy. Disk encryption and TLS are operator responsibilities.

## Boundaries and sources

- [GitHub signature validation](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)
- [GitHub App authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app)
- [Ruff configuration](https://docs.astral.sh/ruff/configuration/)
- [ESLint configuration](https://eslint.org/docs/latest/use/configure/configuration-files)

These sources informed integration choices. This document describes implemented behavior, not a security certification.
