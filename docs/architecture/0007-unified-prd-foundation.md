# ADR-007: Align the existing beta with Unified PRD v1.1

Accepted 2026-11-25. Supersedes ADR-002 in the historical architecture notes.

Keep the existing package layout, React UI, fixed analyzers, and Alembic baseline. Add Redis with **RQ**, not Celery. Committed queued ReviewRun rows remain a durable outbox; a dispatcher sends only integer run IDs to RQ using a JSON serializer. Redis outages leave jobs queued for later dispatch. Stable job IDs and conditional database claims prevent repeated deliveries from running duplicate reviews.

Compose now includes PostgreSQL, Redis, API, migration job, dispatcher, and RQ worker. Ordinary unit/integration tests use SQLite and fake Redis without credentials. GitHub Actions builds the actual Docker images and executes a sample review through PostgreSQL and Redis/RQ. Local Docker verification cannot be claimed on this Windows machine because neither Docker nor WSL is installed.

Use the existing CSS rather than rewriting the working UI solely to add Tailwind; the PRD permits adapting a sound layout. Frontend lint, formatting, tests, and build are all CI checks. Object authorization, expanded metadata, analyzer isolation, and full AI findings contracts belong to M1–M4.

Apache-2.0 and public GitHub publication were explicitly confirmed by the user on 2026-11-25. A tagged release remains subject to separate approval.
