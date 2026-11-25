# Architecture

CodeLens is a modular monolith. FastAPI serves the API and built React assets. PostgreSQL persists installations, repositories, PRs, deliveries, runs, findings, users and grants. Alembic manages schema changes.

Signed webhooks atomically persist delivery and run records. A dispatcher reads the durable outbox and queues numeric identifiers/generations in Redis. RQ workers retrieve commit-pinned source through a read-only GitHub App. Transient GitHub failures receive bounded retries; analyzer failures produce partial reports.

Compose uses a separate non-root, network-denied analyzer with bounded temporary JSON requests on a shared volume. Ruff, ESLint and selected detect-secrets detectors use trusted configurations. Project scripts, plugins and dependencies never execute. Source is transient; reports retain normalized metadata and redacted evidence. Spool files expire after ten minutes and must be excluded from backups.

Optional AI receives rule metadata and opaque locations only. Schema and diff-reference validation precede storing advisory findings. Failures preserve deterministic results. There are no automatic fixes, approvals, merges or GitHub comments.

Local bearer tokens enforce per-user repository grants. Operators have global bootstrap access, reviewers read assigned repositories, owners configure/delete them. Out-of-scope objects return 404. User tokens are hashed at rest and remain in browser memory.

## Decisions

- [Foundation and RQ outbox](architecture/0007-unified-prd-foundation.md)
- [GitHub ingestion](architecture/0008-github-ingestion.md)
- [Analyzer isolation and detectors](architecture/0009-analyzer-isolation.md)
- [Repository access](architecture/0010-repository-access.md)
- [Structured advisory AI](architecture/0011-advisory-ai.md)

These supersede the earlier SQL-only queue, single-operator auth and worker-process analysis. Existing plain CSS was retained instead of a Tailwind rewrite.

Use one worker for this beta: stale-job lease fencing and exact distributed quotas remain future work. Proxy TLS/rate limits, storage encryption, backups and secret rotation are operator responsibilities. SQLite/direct-worker mode is a developer shortcut without Compose isolation.
