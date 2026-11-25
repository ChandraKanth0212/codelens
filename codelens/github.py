import base64
import time
from pathlib import Path
from urllib.parse import quote

import httpx
import jwt
import yaml

from codelens.diffs import skip_reason
from codelens.schemas import RepoConfig
from codelens.settings import Settings


class GitHubError(Exception):
    pass


class GitHubTransientError(GitHubError):
    """Safe error eligible for bounded job retry."""


class SkipFile(GitHubError):
    """A known safe file exclusion, not a failed review."""


class GitHub:
    def __init__(self, config: Settings, installation: int):
        if not config.github_app_id or not config.github_private_key_path:
            raise GitHubError("GitHub App credentials are not configured")
        timestamp = int(time.time())
        token = jwt.encode(
            {"iat": timestamp - 60, "exp": timestamp + 540, "iss": config.github_app_id},
            Path(config.github_private_key_path).read_text(),
            algorithm="RS256",
        )
        self.client = httpx.Client(
            base_url="https://api.github.com",
            timeout=20,
            follow_redirects=False,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Authorization": f"Bearer {token}",
            },
        )
        try:
            result = self.request("POST", f"/app/installations/{installation}/access_tokens")
            self.client.headers["Authorization"] = f"Bearer {result['token']}"
        except Exception:
            self.client.close()
            raise

    def request(self, method: str, path: str):
        for attempt in range(3):
            try:
                with self.client.stream(method, path) as response:
                    rate_limited = response.status_code == 429 or (
                        response.status_code == 403
                        and (
                            response.headers.get("x-ratelimit-remaining") == "0"
                            or "retry-after" in response.headers
                        )
                    )
                    if response.status_code >= 500 or rate_limited:
                        if attempt == 2:
                            raise GitHubTransientError("GitHub rate limit or temporary outage")
                        try:
                            delay = min(
                                5, max(1, float(response.headers.get("retry-after", 2**attempt)))
                            )
                        except ValueError:
                            delay = 2**attempt
                        time.sleep(delay)
                        continue
                    if response.status_code == 404:
                        raise FileNotFoundError("GitHub resource not found")
                    if response.status_code >= 300:
                        raise GitHubError(f"GitHub request failed ({response.status_code})")
                    data = bytearray()
                    for part in response.iter_bytes():
                        data.extend(part)
                        if len(data) > 2_000_000:
                            raise GitHubError("GitHub response exceeded size limit")
                    import json

                    return json.loads(data)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 2:
                    raise GitHubTransientError("GitHub connection timed out") from None
                time.sleep(2**attempt)
        raise GitHubTransientError("GitHub unavailable")

    def changed_files(self, repo: str, number: int, limit: int):
        files = []
        for page in range(1, 5):
            batch = self.request(
                "GET", f"/repos/{repo}/pulls/{number}/files?per_page=30&page={page}"
            )
            if not isinstance(batch, list):
                raise GitHubError("Invalid changed-file response")
            files.extend(batch)
            if len(files) > limit:
                raise GitHubError("Changed file count exceeds configured limit")
            if len(batch) < 30:
                return files
        raise GitHubError("Changed file pagination limit exceeded")

    def content(self, repo: str, path: str, sha: str, limit: int) -> str:
        result = self.request("GET", f"/repos/{repo}/contents/{quote(path, safe='/')}?ref={sha}")
        if (
            not isinstance(result, dict)
            or result.get("type") != "file"
            or result.get("size", limit + 1) > limit
        ):
            raise SkipFile("Not a regular file or exceeds per-file size limit")
        if result.get("encoding") != "base64":
            raise GitHubError("Unsupported content encoding")
        value = base64.b64decode(result["content"])
        if len(value) > limit or b"\x00" in value:
            raise SkipFile("Binary or oversized content")
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            raise SkipFile("Unsupported text encoding") from None

    def retrieve(self, repo: str, number: int, sha: str, config: RepoConfig):
        pr = self.request("GET", f"/repos/{repo}/pulls/{number}")
        if pr["head"]["sha"] != sha:
            raise GitHubError("Pull request changed before review; a newer run will review it")
        if pr["changed_files"] > config.max_files:
            raise GitHubError("Changed file count exceeds configured limit")
        # Trusted base branch config can only narrow operator permissions.
        try:
            source = self.content(repo, ".codelens.yml", pr["base"]["sha"], 16_000)
            base_config = RepoConfig.model_validate(yaml.safe_load(source))
            config = config.model_copy(
                update={
                    "enabled": config.enabled and base_config.enabled,
                    "exclude": config.exclude + base_config.exclude,
                    "analyzers": [a for a in config.analyzers if a in base_config.analyzers],
                    "ai_enabled": config.ai_enabled and base_config.ai_enabled,
                    "max_files": min(config.max_files, base_config.max_files),
                    "max_file_bytes": min(config.max_file_bytes, base_config.max_file_bytes),
                    "max_total_bytes": min(config.max_total_bytes, base_config.max_total_bytes),
                    "severity_threshold": base_config.severity_threshold,
                    "max_processing_seconds": min(
                        config.max_processing_seconds, base_config.max_processing_seconds
                    ),
                }
            )
        except FileNotFoundError:
            base_config = config
        if not config.enabled:
            return [], [{"file": "*", "reason": "review disabled"}], config
        files = self.changed_files(repo, number, config.max_files)
        if len(files) != pr["changed_files"]:
            raise GitHubError("Changed-file response incomplete or PR changed during pagination")
        reviewed, skipped, total = [], [], 0
        for file in files:
            path = file["filename"]
            reason = skip_reason(path, config) or skip_reason(path, base_config)
            if file["status"] == "removed":
                reason = "deleted file"
            if not file.get("patch"):
                reason = reason or "binary or missing diff"
            if reason:
                skipped.append({"file": path, "reason": reason})
                continue
            patch = file["patch"]
            try:
                content = self.content(repo, path, sha, config.max_file_bytes)
            except SkipFile as error:
                skipped.append({"file": path, "reason": str(error)})
                continue
            total += len(content.encode()) + len(patch.encode())
            if total > config.max_total_bytes:
                raise GitHubError("Review byte budget exceeded")
            reviewed.append({"path": path, "content": content, "patch": patch})
        # File-list endpoint is mutable: reject a concurrent synchronize event.
        latest = self.request("GET", f"/repos/{repo}/pulls/{number}")
        if latest["head"]["sha"] != sha:
            raise GitHubError("Pull request changed during retrieval; review discarded")
        return reviewed, skipped, config

    def close(self):
        self.client.close()
