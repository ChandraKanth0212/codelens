# ADR 0011: Structured AI with opaque locations

The optional adapter enriches deterministic findings; it does not perform source-based review. Server and repository opt-in are both required. No live provider calls were made during development.

Input: at most 30 static analyzer names, validated rule IDs, severities, opaque file aliases and line ranges. No source, actual paths, titles, free-text evidence, environment files, secret-scanner findings or excluded files are transmitted. This is the minimal approved context. Injection text in repository content cannot become instructions because it never enters the request.

The provider returns the PRD summary/findings schema with numeric confidence. JSON Schema strict mode and independent Pydantic validation reject malformed fields. Locations must exactly match an offered alias and range; the worker separately checks approved diff lines. Valid findings are mapped back to local paths, deduplicated and labeled AI/advisory. Unknown references are discarded and counted. Nothing executes model output.

One request per eligible run, at most 1200 output tokens, 20-second HTTP timeout, zero paid-request retries. Failure preserves deterministic findings and marks the report partial. Operator controls cost through repository opt-in, queue limits and provider account budgets; there is no application-wide dollar quota. Provider/model/prompt version are recorded; hidden reasoning is not stored. `store: false` does not establish zero provider retention: account terms and settings still apply.

Structured output contract follows [OpenAI documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat). A compatible model is required. Mock tests cover success, invalid schema/locations, timeout, safe failure, secret exclusion and injection boundaries.
