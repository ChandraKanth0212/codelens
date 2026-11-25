# ADR-009: Credential-free, offline analyzer container

Compose analysis runs in a separate non-root container with `network_mode: none`, a read-only root filesystem, dropped capabilities, and CPU/memory/PID limits. The container receives no environment secrets, GitHub key mounts, database connection, or Redis access. The worker fetches source and writes a bounded JSON request to a dedicated shared volume; the analyzer removes that request before processing and returns normalized findings. The worker validates source paths and every line against its approved diff. Input/output files are deleted after consumption; abandoned files expire after ten minutes. The volume is transient working storage, not a report archive; protect it and exclude it from backups.

Fixed Ruff/ESLint configuration remains mandatory. No code, repository plugin, or repository configuration is executed. Analysis stops between adapters when the configured processing budget expires; an in-flight subprocess has a separate 20-second timeout. RQ enforces the outer job timeout. Local direct mode is only for trusted development fixtures and does not provide container isolation.

## Secret scanner choice

Replace the home-grown patterns with selected offline `detect-secrets` 1.5.0 detectors (GitHub tokens, AWS keys, private-key markers). This Apache-2.0 dependency is license-compatible. Review: [upstream](https://github.com/Yelp/detect-secrets), [license](https://github.com/Yelp/detect-secrets/blob/master/LICENSE), [PyPI release](https://pypi.org/project/detect-secrets/). The latest PyPI release is older than the repository's current activity; keep maintenance under review. This is not a claim of comprehensive secret coverage.

Only `analyze_string` is used; verification/network APIs and custom plugins are never invoked. Matched values and hashes are not persisted. Reports contain the detector name, location, and `[REDACTED]` evidence. False positives and unsupported secret formats remain possible.

The shared scanner container is a boundary against accidental execution, network access, and credential exposure, not a proof against every kernel/parser exploit. Keep the host patched and use dedicated deployments for unrelated trust domains.
