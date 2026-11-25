# ADR-008: GitHub identity, history, and retries

Accepted for M1. Keep immutable head/base SHAs on every run and a separate pull-request record for navigation. Deliveries retain only action and numeric/commit identifiers, never raw payloads. Repository identity is pinned to GitHub's numeric ID after the first signed event; a name reused by a different repository is rejected until the operator re-registers it. PostgreSQL locks the repository row during ingestion; uniqueness constraints protect installations, PR numbers, and runs.

GitHub requests have 20-second timeouts and three bounded attempts for connection failures, 5xx responses, and rate limits. Retry-After sleeps are capped at five seconds before deferring further recovery to the job retry policy. File pagination is bounded to four pages of 30 entries and a configured maximum of 100. A mutable PR head is checked before and after source retrieval.

Each deliberate demo rerun increments a generation. RQ IDs include run, generation, and attempt; stale queued jobs cannot claim a newer generation. This avoids a completed Redis job blocking a rerun or processing an old request after a reset.

Live App credentials and installation are not implied by publishing this project to GitHub. Synthetic signed webhook tests and mocked HTTP tests validate the code path; a live test is a separate operator setup step.
