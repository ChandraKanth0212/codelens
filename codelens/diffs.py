import fnmatch
import re
from pathlib import PurePosixPath

from codelens.schemas import RepoConfig

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
BLOCKED_PARTS = {"node_modules", "vendor", "dist", "build", ".git", "__pycache__"}


def safe_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return bool(parts) and not (
        path.startswith("/")
        or "\\" in path
        or ":" in path
        or any(p in {"..", "."} for p in parts)
        or any(ord(c) < 32 for c in path)
    )


def skip_reason(path: str, config: RepoConfig) -> str | None:
    if not safe_path(path):
        return "unsafe path"
    parts = PurePosixPath(path).parts
    name = parts[-1].lower()
    if any(p.lower() in BLOCKED_PARTS for p in parts):
        return "generated or vendored"
    if name.startswith(".env") or name.endswith((".pem", ".key", ".lock", ".min.js")):
        return "sensitive or generated file"
    if "credential" in name or "secret" in name:
        return "sensitive filename"
    if not any(fnmatch.fnmatchcase(path, pattern) for pattern in config.include):
        return "outside include patterns"
    if any(fnmatch.fnmatchcase(path, pattern) for pattern in config.exclude):
        return "excluded by configuration"
    if PurePosixPath(path).suffix not in {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return "unsupported language"
    return None


def added_lines(patch: str) -> set[int]:
    line = None
    added = set()
    for text in patch.splitlines():
        match = HUNK.match(text)
        if match:
            line = int(match.group(1))
        elif line is not None:
            if text.startswith("+"):
                added.add(line)
                line += 1
            elif text.startswith(" "):
                line += 1
    return added
