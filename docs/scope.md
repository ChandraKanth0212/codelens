# Scope and acceptance

Implemented: signed App webhooks, delivery/head-SHA idempotence, repository/PR identities, retrieval limits/retries, RQ outbox, isolated Ruff/ESLint/detect-secrets, normalized findings, repository-scoped users, dashboard filters/detail/feedback, optional structured AI, migrations, Compose and CI.

Intentional choices: existing plain CSS retained; AI enriches rule metadata with opaque locations instead of source-based review; SQLite/direct worker is developer-only. GitHub posting remains unsupported and cannot be enabled.

Unverified external acceptance: live GitHub App install, real paid AI provider, browser visual/mobile/keyboard review and screenshots. No hosted demo. See IMPLEMENTATION_STATUS.md for evidence.

Deferred: OAuth/SSO, user-admin UI, distributed quotas/lease fencing, GitHub feedback and more languages. No automatic fixes, commits, approvals or merges.
