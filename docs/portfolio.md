# Portfolio and GitHub launch guide

## Publish your project

Review the source and license, run the tests, and understand the architecture before presenting it. Create an empty GitHub repository named `codelens` under your account, then run from this folder:

```sh
git init -b main
git add .
git status
git commit -m "Build CodeLens review assistant beta"
git remote add origin https://github.com/YOUR-USERNAME/codelens.git
git push -u origin main
```

Inspect `git status` before committing. `.env`, databases, private keys, virtual environments, and dependency folders are ignored. Do not add them with `git add -f`. Enable private vulnerability reporting, require CI before merging, add a project description and topics, and replace the clone placeholder in README. Run the GitHub App flow against a public synthetic test repository before tagging a release.

Suggested description: “Self-hosted pull request review with Ruff, ESLint, signed GitHub webhooks, and an evidence-first dashboard.” Suggested topics: `code-review`, `github-app`, `fastapi`, `react`, `typescript`, `python`, `static-analysis`, `self-hosted`.

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
6. Show tests and architecture decisions, including the SQL queue and single-operator tradeoffs.

## Interview discussion prompts

- Why is a durable SQL queue simpler than a database-plus-Redis dual write here?
- Why must a worker verify a PR's head before and after retrieving its file list?
- Why must repository-controlled analyzer configuration never be executed?
- What does a finding's absence prove, and what does it not prove?
- What would you add for multi-tenant production use and untrusted parser isolation?
