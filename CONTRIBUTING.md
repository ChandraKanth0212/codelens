# Contributing

Start with the README's local setup and run the synthetic sample. Then read `docs/architecture.md` and `SECURITY.md`.

1. Open an issue describing a reproducible problem or a scoped proposal. Do not include private source, tokens, or sensitive reports.
2. Fork the repository and create a short feature branch.
3. Keep changes focused. Add behavioral tests for changed parsing, authorization, persistence, or privacy boundaries.
4. Run Ruff checks/formatting, Pytest, frontend tests, and the production build using the README commands.
5. Open a PR explaining the problem, resulting behavior, tests, and privacy impact. Use synthetic fixtures only.

Analyzer adapters must use trusted fixed configuration, bounded input/output/time, redacted evidence, and changed-line mapping. Never install dependencies from a reviewed repository or run its scripts. New external providers require an explicit data-flow description and opt-in configuration.

UI changes should include desktop and mobile screenshots, keyboard testing, and loading/empty/error states. Preserve text labels for severity and distinguish AI from deterministic evidence.

By submitting a contribution, you agree it may be distributed under this project's Apache-2.0 license. No CLA is required. Maintainers review and merge changes manually.

Suggested starter tasks: add multi-hunk rename/deletion diff fixtures, improve analyzer rule explanations, add UI interaction tests, improve setup troubleshooting, or expand accessibility coverage. These are suggestions, not claims of existing community issues.
