# GitHub App setup and live acceptance

This guide targets the existing public synthetic [validation repository](https://github.com/ChandraKanth0212/codelens-validation). Keep AI disabled. No App credentials were configured or live App deliveries verified during preparation.

## 1. Start CodeLens

Install Docker with Compose v2 (not available on the development workstation used for this validation). Clone CodeLens, then:

```sh
python scripts/setup.py
docker compose up --build -d --wait
docker compose ps
```

Open http://localhost:8000. Copy the operator token from your local `.env` into the password field. Do not paste it into issues/chat, screenshots, shell command arguments or logs. Run the synthetic sample to check local processing first.

## 2. Provide a reachable webhook URL

GitHub cannot call localhost. Use your existing HTTPS reverse proxy, routing **only** `/api/v1/webhooks/github` to `http://127.0.0.1:8000/api/v1/webhooks/github`. Preserve raw request bodies, cap bodies at 1 MB, rate limit, and keep the dashboard private. Keep certificate validation enabled.

For a temporary synthetic-only test, GitHub's official tutorial documents [Smee relay setup](https://docs.github.com/en/apps/creating-github-apps/writing-code-for-a-github-app/building-a-github-app-that-responds-to-webhook-events). Create a channel at smee.io, install its official `smee-client` package, and forward the channel to CodeLens:

```sh
npm install --global smee-client
smee --url YOUR_CHANNEL_URL --path /api/v1/webhooks/github --port 8000
```

Leave that terminal running. Use the channel URL as the App webhook URL. Relay payloads contain repository/PR metadata and pass through a third party; use only these public synthetic fixtures. Do not publish the channel URL. Stop the relay after validation. No relay or public ingress has been created by this project.

## 3. Register the App

1. Open GitHub Settings > Developer settings > GitHub Apps > New GitHub App.
2. Choose a unique name, such as `ChandraKanth0212-CodeLens-validation`; use the CodeLens repository URL as its homepage.
3. Leave OAuth/user authorization and callback/setup URLs unused. CodeLens uses installation authentication, not OAuth.
4. Enable Webhooks. Enter the reachable URL from step 2.
5. Set the webhook secret to the locally generated `CODELENS_WEBHOOK_SECRET` from `.env`; do not reuse the dashboard token.
6. Grant repository **Contents: read-only**, **Pull requests: read-only**, and **Metadata: read-only**. Leave other permissions unset. No Checks, Issues or write permissions are required.
7. Subscribe to **Pull request** events. Select installation only on your account for this test, then create the App.
8. Record its numeric **App ID**, not Client ID. Generate a private key; move the downloaded PEM outside this repository and restrict access to your account/container worker.

Reference: [GitHub permission guidance](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app).

## 4. Install and configure

On the App settings page choose Install App, select your account, and grant access to **only** `codelens-validation`. Record the numeric installation ID from the installation URL. Do not confuse it with the App ID or repository ID.

Edit the local ignored `.env`:

```dotenv
CODELENS_GITHUB_APP_ID=YOUR_NUMERIC_APP_ID
CODELENS_GITHUB_PRIVATE_KEY_PATH=/run/secrets/github-app.pem
CODELENS_ALLOWED_REPOSITORIES=ChandraKanth0212/codelens-validation
CODELENS_AI_ENABLED=false
```

Retain the generated admin token and matching webhook secret. Do not commit `.env`. In ignored `compose.override.yaml`, mount the private key only into the worker:

```yaml
services:
  worker:
    volumes:
      - /absolute/path/outside/repo/github-app.pem:/run/secrets/github-app.pem:ro
```

On Windows, use a quoted absolute path such as `C:/secure/github-app.pem:/run/secrets/github-app.pem:ro`. Ensure the non-root container user (UID 10001) can read it without making it publicly accessible. Recreate services to load environment changes:

```sh
docker compose up -d --force-recreate --wait
```

In CodeLens > Repositories, connect `ChandraKanth0212/codelens-validation` with its installation ID. Settings showing configured means fields are present, not that authentication succeeded.

## 5. Trigger real review events

Prepared PRs:

| PR | Intentional defects | Expected rules |
| --- | --- | --- |
| [Python #1](https://github.com/ChandraKanth0212/codelens-validation/pull/1) | Unused import, undefined fee, eval | F401, F821, S307 |
| [TypeScript #2](https://github.com/ChandraKanth0212/codelens-validation/pull/2) | Unused variable, loose equality, eval | @typescript-eslint/no-unused-vars, eqeqeq, no-eval |

Do not execute the fixture code. The PRs predate installation: close and reopen each to produce `reopened`, or create a fresh PR from a new fixture branch for `opened`. Merely installing the App does not backfill reviews.

1. In App settings > Advanced > Recent deliveries, inspect the pull_request delivery. Expect HTTP 202; ping/unsupported events are safely ignored.
2. In CodeLens, observe queued/running then completed (or inspect explicit partial/failed errors). Compare the full reviewed SHA with the PR head, not just the short label.
3. Confirm the expected rules, exact file/line locations, redacted evidence and GitHub link. AI must remain disabled.
4. Redeliver the same event. Expect no extra run or duplicate findings. Same SHA under another delivery ID also deduplicates.
5. Push a harmless source comment to the fixture branch. The `synchronize` event must create a new run with the new SHA. Verify earlier run history remains.
6. Reopen again without changing SHA: the existing run should be reused, not duplicated.
7. Repeat for the other language. Record PR URL, full SHA, delivery ID, HTTP status, run ID/status and observed rules. Do not capture tokens, request headers, private keys or raw sensitive payloads.

App authentication uses a short-lived installation token generated server-side; no personal access token is required. [GitHub installation authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation).

## 6. Diagnose failures

- No delivery: verify App installation, repository selection, Pull request subscription and active webhook URL/relay.
- HTTP 401: mismatched secret or changed raw body; check proxy/relay without logging secrets.
- HTTP 403: repository allowlist, registration or installation mismatch.
- HTTP 429: queue admission limit; let work drain, then redeliver.
- Queued indefinitely: inspect `docker compose logs dispatcher worker analyzer redis`; verify shared PostgreSQL/Redis configuration.
- Failed retrieval: check App ID, key readability, read permissions, installation ID, current PR SHA and file limits. No raw API error is exposed to the dashboard.
- Partial analysis: check analyzer service/resource limits and safe report errors; do not interpret partial/clean reports as proof of safety.

## 7. Browser acceptance

Check login/error, empty overview, queued/running/completed/partial/failed reports, finding detail and feedback, all filters, repositories, settings and setup/help. Verify keyboard navigation, modal focus/Escape, light/dark themes and desktop/narrow mobile widths. Use only synthetic data in screenshots. Browser-tool access to localhost is currently denied by a saved permission policy; this checklist is not a claim of completed visual QA.

## 8. Evidence and cleanup

Record results in IMPLEMENTATION_STATUS.md. Stop temporary relays, close unused fixture PRs after testing, and uninstall the App/revoke its key when no longer needed. Keep credentials outside Git. Do not create a release tag as part of this validation milestone.
