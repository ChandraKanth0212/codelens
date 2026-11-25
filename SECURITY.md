# Security policy

## Supported release

0.1.x is an experimental beta. Do not treat CodeLens as a complete security scanner or a security approval gate.

## Reporting

Maintainers should enable GitHub **Private vulnerability reporting** before making the repository public. Use the repository Security tab to submit a private report. If that option is unavailable, ask the maintainer for a private contact without publishing exploit details. Never open a public issue containing private source or live credentials.

Include affected version, a minimal synthetic reproduction, expected/observed behavior, and potential impact. Do not test against systems without authorization.

## Implemented controls

- Raw-body HMAC verification with constant-time comparison; no unsigned webhook processing.
- Separate operator token, repository allowlist, and registered installation verification.
- Fixed GitHub API origin; no use of webhook-provided download URLs; redirects disabled.
- Source and configuration retrieved at commit SHAs. Base config can only narrow operator policy.
- File count, content byte, response byte, webhook body, and analyzer timeout limits.
- No repository configs/plugins/scripts executed. Analyzer commands use argument arrays, not a shell.
- Analyzer child environment excludes application credentials. Reports/logs omit raw source and exceptions.
- AI receives rule metadata only and cannot create inline findings or execute actions.
- React escapes rendered data; no model/repository HTML execution.
- Non-root, read-only, resource-limited Compose application containers.

## Known boundaries

Single-operator authentication is not multi-tenant authorization. Use HTTPS and keep the token private. The worker needs outbound GitHub/optional AI access; analyzers currently share its network namespace. A parser exploit could cross process boundaries. Strong network-denied analyzer sandboxing is not implemented. Use a dedicated host/container and only repositories you are authorized to review.

Detection is deliberately narrow: only supported text files, added lines, and selected rules. Full type checking, dependency vulnerabilities, and comprehensive secret detection are out of scope. Secrets can take arbitrary forms; no scanner guarantees their absence. Source is not sent to AI, but rule metadata may disclose technology choices.

The queue cap is a soft admission limit under concurrent requests. Apply rate limits and request-size limits at the reverse proxy. Stale-job recovery lacks lease fencing; use one worker for the beta. Encrypt disks/backups, protect the GitHub key, rotate tokens, and review dependencies regularly. Never expose the development database or commit `.env`/private keys.
