# Security policy

0.1.x is an experimental beta, not a security approval gate or comprehensive scanner.

## Private reporting

[Report a vulnerability privately](https://github.com/ChandraKanth0212/codelens/security/advisories/new). Private reporting is enabled and was verified through GitHub's API. If unavailable, contact the maintainer privately before sharing details. Never post credentials, private source or exploit details publicly. Include version, a synthetic reproduction and impact. Test only systems you are authorized to assess.

## Controls

- Constant-time raw-body HMAC validation, delivery/head-SHA deduplication and registered installation/repository checks.
- User tokens hashed at rest, repository grants, owner/reviewer permissions and object-level tests. Separate global operator secret.
- Fixed GitHub origin, redirects disabled, commit-pinned retrieval; base config only narrows analysis access.
- Path, file, body and response limits; timeouts, bounded retries and container resource limits.
- Trusted analyzer configuration; no reviewed scripts, plugins or dependencies execute.
- Compose analyzer has no network, application credentials, DB/Redis access or key mount. Non-root, read-only root, dropped capabilities, bounded memory/CPU/PIDs.
- AI receives no source, real paths, secret findings or PR titles. Strict schema/reference checks, advisory labels and escaped rendering. Provider failure preserves static findings.
- Raw source, credentials and exception strings are excluded from application reports/logs. Secret findings use redacted evidence.

## Boundaries

Use HTTPS and private dashboard ingress. Protect/revoke bearer tokens; the operator token has global privileges. This is not OAuth, SSO or hardened multi-tenant SaaS. Direct local-worker mode lacks container isolation. Containers do not prove safety against kernel/parser exploits; use dedicated deployments for unrelated trust domains.

Source temporarily exists in memory and the spool volume. Requests are removed before analysis, responses after consumption, abandoned files after ten minutes. Exclude the spool from backups. Encrypt storage/backups, protect the App key, and keep PostgreSQL/Redis private. Compose's database password is development-only.

Only supported text files, added lines and selected rules are reviewed. There is no full type check, dependency-vulnerability scan or comprehensive secret detection. Metadata may disclose technology choices. Provider retention follows account terms; `store: false` is not a zero-retention guarantee.

Queue admission is a soft cap. Apply a proxy 1 MB body limit and rate limits. One worker is recommended until lease fencing is added. Deletion cannot retract provider metadata or operator backups. No external security audit or measured production performance is claimed.
