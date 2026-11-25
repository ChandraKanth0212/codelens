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


## Restart and persistence verification

After a completed synthetic review, stop and restart services without removing volumes:

```sh
docker compose stop api worker dispatcher analyzer db redis
docker compose up -d --wait
docker compose ps
```

Sign in again, confirm the earlier completed report remains, then run another sample. PostgreSQL and Redis use named volumes; `docker compose down` preserves them, while `down -v` removes them and is unsuitable for keeping data. CI exercises this restart sequence and verifies both existing reports and new RQ/analyzer processing.

For the automated operator check (POSIX shell, from the repository root):

```sh
docker compose exec -T api python - --require-existing < scripts/container_smoke.py
```

It checks API health, served frontend HTML, retained completed reports and two real analyzer reviews with AI disabled. It uses the container's configured token without displaying it. Omit `--require-existing` on a fresh instance. This verifies HTTP behavior, not browser rendering.

## Backup and non-destructive restore rehearsal

Backups contain repository metadata, reports, users and token hashes. Restrict access, encrypt off-host copies and apply retention. Never commit a dump. `backups/` and `*.dump` are ignored. Also securely back up operator configuration and the App key separately; do not include the transient analyzer spool. A database dump is not a copy of `.env` or your key.

Pause inbound webhook traffic at the proxy, wait for queued/running work to finish, then stop application services for a consistent recovery point:

```sh
docker compose stop api dispatcher worker analyzer
mkdir backups
docker compose exec -T db pg_dump -U codelens -d codelens -Fc -f /tmp/codelens.dump
docker compose cp db:/tmp/codelens.dump ./backups/codelens.dump
docker compose up -d --wait
```

Use a timestamped destination for subsequent backups rather than overwriting the only copy. Remove the temporary container dump after securely exporting it. Resume inbound traffic after service health checks. `pg_dump` creates a consistent database snapshot; quiescing application writes makes it easier to reconcile pending jobs and webhook redeliveries.

Rehearse into a **new** database. The following fails if the target already exists; it does not replace the running database:

```sh
docker compose cp ./backups/codelens.dump db:/tmp/codelens-restore.dump
docker compose exec -T db createdb -U codelens codelens_restore_check
docker compose exec -T db pg_restore -U codelens --no-owner --exit-on-error -d codelens_restore_check /tmp/codelens-restore.dump
docker compose exec -T db psql -U codelens -d codelens_restore_check -c "SELECT count(*) FROM review_runs; SELECT count(*) FROM findings;"
```

The development database role can create databases; production restoration may require a database administrator. CI restores its synthetic snapshot into a separate database and compares finding counts.

For actual disaster recovery, use a separate deployment with fresh volumes/Redis, restore the database, securely supply the matching configuration/key, point all application services at the restored database, and run migrations for the chosen application version. Validate health, user access and existing reports before switching ingress. Pending database jobs are redispatched; stale running jobs recover on the existing timeout/retry policy. Do not combine an arbitrary old Redis snapshot with a different database snapshot. Keep the old deployment intact until verification completes. Full production disaster recovery remains operator-specific; the automated test covers a synthetic database restore.
