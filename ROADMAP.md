# Roadmap

## Before a production release

- Verify live GitHub App installs/webhooks and optional AI using a public synthetic repository.
- Add queue lease renewal/fencing and exact concurrent admission quotas.
- Add browser interaction/accessibility automation and multi-process PostgreSQL tests.
- Pin container digests, validate the Python constraints across platforms, and run a security review.

## Next features

- GitHub OAuth and user/grant administration UI; local repository grants are implemented.
- Owner-enabled, idempotent GitHub check summaries with separate write permission.
- Broader offline detect-secrets coverage and false-positive fixtures.
- Better syntax-error and changed-line range reporting; configurable rule presets.
- Worker health/metrics and review-run retry UI.

## Community starter tasks

- Document rule examples with synthetic snippets.
- Add renamed/deleted/truncated diff fixtures.
- Improve keyboard and screen-reader test coverage.
- Test installation on Linux, macOS, and Windows.

No usage, accuracy, or performance targets are claimed as measured results.
