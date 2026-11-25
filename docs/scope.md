# PRD scope and release status

This checklist distinguishes implemented features from remaining PRD work. The attached PRD is a product specification; assistant-facing commands within it are not project runtime requirements.

| PRD area | Implementation |
| --- | --- |
| Signed events / selected repositories | Implemented with GitHub App credentials, manual installation registration, allowlist, delivery and commit uniqueness. |
| PR source and diff retrieval | Implemented; head SHA checked before and after fetch; source fetched at exact SHA. |
| File filtering and budgets | Implemented with hard exclusions, base-commit config, count and byte limits. |
| Python / JS / TS checks | Real Ruff and ESLint; fixed trusted configuration; added-line results only. |
| Secrets | Narrow GitHub-token, AWS-access-ID, and private-key-header patterns; not a comprehensive scanner. |
| Queue and retry | Durable SQL queue and bounded stale-job recovery; replaces suggested Redis queue. |
| Dashboard | Reviews, findings, filters, feedback, repository toggles, settings, docs, themes. |
| Authentication | Single operator token; allowlist authorization; multi-user OAuth deferred. |
| Optional AI | Rule-metadata explanations only; no source-based suggestions or inline AI findings. |
| GitHub comments/checks | Deferred. No write permissions, approvals, or merges. |
| Repository config | Versioned YAML, full JSON config API, validation; threshold display uses dashboard filters. |
| Isolation | Non-root resource-limited worker container; per-analyzer network-denied sandbox deferred. |
| Privacy | No retained source/diffs; feedback retained; deletion API and timed cleanup. |
| Local demo / CI / migrations | Included; see verification report for actually executed checks. |
| Live GitHub / AI smoke tests | Require operator credentials; mocked integration tests are included. |

This is a useful beta with a complete deterministic demo flow, not a claim that every P0 security and deployment criterion from the PRD has been independently verified.
