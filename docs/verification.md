# Verification record

Verified locally on 25 November 2026 using Windows, Python 3.13.12, and Node.js 22.21.0.

| Check | Result |
| --- | --- |
| Python suite | **45 passed**, 81% statement coverage, 9.23 seconds in the final run. |
| Ruff lint | Passed. |
| Ruff format | Passed; 22 Python files formatted. |
| Frontend tests | **2 passed**, covering combined finding filters and severity sorting. |
| TypeScript / Vite production build | Passed. |
| Alembic migration cycle | Upgrade, downgrade to base, and re-upgrade passed against local SQLite. |
| Analyzer dependency audit | npm reported 0 known vulnerabilities after updates. |
| Frontend dependency audit | npm reported 0 known vulnerabilities after updates. |
| Real analyzer adapters | Ruff and ESLint executed in tests against Python and TypeScript fixtures. |
| Integration path | Signed mock webhook → database queue → worker → real analyzers → persisted report → authenticated API retrieval passed. |
| Local server startup | Uvicorn started successfully with a migrated database. Stopped after verification. |
| Source archive | ZIP integrity and required-file checks performed during packaging. |

The Python test runner emitted one dependency deprecation warning: Starlette's `httpx` TestClient transport is deprecated in favor of `httpx2`. It did not cause test failures. Keep the test transport under review when updating dependencies.

## Not verified here

- **Browser visual/interaction QA:** the browser approval gate declined localhost access. No screenshot or manual UI-test pass is claimed.
- **Docker/PostgreSQL runtime:** Docker is not installed in the execution environment. Compose and container smoke tests are configured in CI, but no CI run on GitHub has occurred yet.
- **Live GitHub App:** no owner App credentials were supplied. Retrieval, permission boundaries, and event processing were tested with synthetic data and mocks.
- **Live AI provider:** no API key was supplied. The data boundary and response schema were tested with a mocked provider.
- **GitHub publication:** the project is a local deliverable, not a published repository or an accepted contribution to another project.
- **Production security/performance:** no external audit, load test, or accuracy benchmark is claimed. Read SECURITY.md and docs/scope.md before deploying.

Audit counts are a point-in-time registry result, not a guarantee that dependencies are vulnerability-free. The coverage number measures statements exercised by this suite, not correctness.
