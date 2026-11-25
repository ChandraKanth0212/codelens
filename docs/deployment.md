# Deployment and troubleshooting

Use a trusted HTTPS reverse proxy in front of the API. Keep operator access private. The Compose API binds only to loopback. Configure the proxy to cap request bodies at 1 MB and rate limit the webhook endpoint. Do not log authorization headers or request/response bodies.

## GitHub key mount

Keep your App private key outside the repository. Create a local `compose.override.yaml` (add it to your local `.git/info/exclude` if it contains private paths):

```yaml
services:
  worker:
    environment:
      CODELENS_GITHUB_PRIVATE_KEY_PATH: /run/secrets/github-app.pem
    volumes:
      - /absolute/path/outside/repo/github-app.pem:/run/secrets/github-app.pem:ro
```

The non-root worker must be able to read the mounted file. Prefer a secrets manager in production. The API does not read the key or generate installation tokens; only the worker does. The dashboard status reflects configuration presence, not a successful external handshake.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Startup refuses to run | Set a random operator token at least 32 characters long. |
| Run remains queued | Check `docker compose logs dispatcher worker analyzer redis`. For the non-Docker shortcut, start `python -m codelens.worker`. |
| Ruff/ESLint partial result | Activate the venv; run `npm ci --prefix analyzer`; confirm Node is in PATH. |
| Webhook 401 | Match the App secret to the server; preserve the exact raw request body. |
| Webhook 403 | Match the allowlisted repository, registered repository, and installation ID. |
| Webhook 429 | Drain the queue, then redeliver from GitHub's delivery view. |
| Retrieval fails | Check App permissions, key mount, installed repositories, commit freshness, and file/byte limits. |
| AI disabled | Enable server, repository, and base-branch config; configure the provider key. |
| Dashboard missing | Run `npm run build --prefix web` and restart the API. |

The API intentionally withholds raw exceptions because they may contain credentials or source. Worker logs contain only run IDs, terminal status, and safe error codes/messages. Never enable raw HTTP debug logging with real credentials.

## Data deletion

`DELETE /api/v1/repositories/{id}` with an operator or repository-owner token removes grants, PRs, findings, runs and deliveries; active jobs cause a conflict response, so retry after completion. Removing a repository from the environment allowlist prevents future live reviews. `CODELENS_RETENTION_DAYS` controls terminal-run retention (default 30); the dispatcher periodically applies it (also the direct development worker). Deleted delivery IDs no longer prevent replay; commit deduplication also lasts only as long as the run record. Keep GitHub delivery records and database backups under an explicit operator policy.

## Operational limitations

One worker is recommended for the beta. No metrics backend, distributed quotas, OAuth, email, GitHub posting, or automatic updates are included. A clean report means no configured rule reported an added-line finding; it does not establish safety. The checked-in Compose configuration is for development and requires operator hardening before internet exposure.
