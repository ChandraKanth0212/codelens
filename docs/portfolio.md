# Portfolio and GitHub launch guide

## Published source

Repository: https://github.com/ChandraKanth0212/codelens (public, Apache-2.0). Source and CI are published; this does not host the running application. Private vulnerability reporting is enabled. Run the documented synthetic sample, understand the architecture and review current limitations before presenting it.

Keep `.env`, databases, private keys, virtual environments and dependencies out of Git. Live App installation and browser visual acceptance remain outstanding. Version 0.1.0 is untagged pending approval.

## Accurate resume entry

**CodeLens — Open-source project | Python, FastAPI, React, TypeScript, PostgreSQL, Docker**

- Built a self-hosted pull request review platform with signed GitHub webhooks, a durable job queue, and commit-scoped static analysis.
- Integrated Ruff and ESLint with added-line filtering, normalized findings, redacted secret checks, and an interactive review dashboard.
- Added authentication, repository authorization, database migrations, CI, and automated tests for webhook security and review processing.

Use “built” only after you have reviewed, run, and can explain the implementation. Disclose AI assistance when required by your institution, employer, or contribution policy. Add a GitHub link once public. Do not claim external users, accepted community contributions, speedups, vulnerability detection accuracy, or test counts you have not verified.

An original open-source repository belongs under **Projects** or **Open-source projects**. “Open-source contributor” is better supported by specific accepted PRs in an existing project. To earn that separately, choose an issue, reproduce it, follow the maintainer's contribution policy, and link the merged PR.

## Two-minute demo

1. Sign in and run the labelled synthetic review.
2. Explain why Ruff flags the undefined name and why ESLint flags loose equality.
3. Filter by severity or analyzer, open a finding, and record feedback.
4. Show the exact SHA and explain added-line mapping and deduplication.
5. Open settings: AI is off; if enabled it receives rule metadata only.
6. Show tests and architecture decisions, including the durable outbox, Redis/RQ, repository grants and isolated analyzers.

## Interview discussion prompts

- How does the PostgreSQL outbox prevent losing jobs between database commit and Redis enqueue?
- Why must a worker verify a PR's head before and after retrieving its file list?
- Why must repository-controlled analyzer configuration never be executed?
- What does a finding's absence prove, and what does it not prove?
- What would you add for multi-tenant production use and stronger worker lease fencing?
