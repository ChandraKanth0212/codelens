# ADR 0010: Repository-scoped local access tokens

Users receive cryptographically random bearer tokens, stored only as SHA-256 hashes. The operator provisions and revokes users through `python -m codelens.users`. Tokens remain in browser memory. Reviewers may read and record feedback on assigned repositories; owners may also configure/delete them. Only the operator connects repositories or starts synthetic demos. Out-of-scope object IDs return 404. Every list is scoped too.

This is intentionally local authentication, without OAuth or enterprise SSO. Use TLS and a private dashboard ingress. The bootstrap operator token is an environment secret with global access; do not distribute it to reviewers.

```sh
docker compose exec api python -m codelens.users create --email reviewer@example.com --name Reviewer --repository-id 1 --role reviewer
docker compose exec api python -m codelens.users revoke --email reviewer@example.com
```

The create command displays the token once; deliver it privately. To change grants, revoke the user and provision a new identity. No UI user administration is included in this beta.
