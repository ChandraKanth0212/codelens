"""File-spool IPC to a credential-free, network-disabled analyzer container.

Source is transient in a private shared volume and deleted after processing/timeout.
Only schema-validated findings with verified changed-line references return to the worker.
"""

import json
import logging
import re
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from codelens.diffs import added_lines, safe_path, skip_reason
from codelens.schemas import Finding, RepoConfig
from codelens.settings import settings

MAX_WIRE_BYTES = 6_000_000


class SourceFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(max_length=1024)
    content: str = Field(max_length=200_000)
    patch: str = Field(max_length=1_000_000)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    files: list[SourceFile] = Field(max_length=100)
    config: RepoConfig


def read_json(path: Path):
    if path.is_symlink() or path.stat().st_size > MAX_WIRE_BYTES:
        raise ValueError("Unsafe analysis envelope")
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value):
    encoded = json.dumps(value).encode()
    if len(encoded) > MAX_WIRE_BYTES:
        raise ValueError("Analysis envelope exceeded limit")
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)


def validate_findings(payload: dict, files: list[dict]):
    allowed = {file["path"]: added_lines(file["patch"]) for file in files}
    accepted = {}
    values = payload.get("findings", [])
    if not isinstance(values, list) or len(values) > 10000:
        raise ValueError("Invalid finding list")
    for raw in values:
        finding = Finding.model_validate(raw)
        lines = allowed.get(finding.file_path, set())
        if not (
            safe_path(finding.file_path)
            and finding.start_line in lines
            and finding.end_line >= finding.start_line
            and finding.end_line - finding.start_line < 1000
            and all(line in lines for line in range(finding.start_line, finding.end_line + 1))
        ):
            raise ValueError("Analyzer returned a location outside the approved diff")
        if finding.source == "ai" or finding.analyzer not in {"ruff", "eslint", "detect-secrets"}:
            raise ValueError("Unknown analyzer")
        accepted[finding.fingerprint] = finding
    # Errors are reduced to safe fixed messages at this trust boundary.
    errors = (
        [
            {
                "analyzer": "sandbox",
                "message": "One or more isolated analyzers failed or reached their time limit.",
            }
        ]
        if payload.get("errors")
        else []
    )
    return list(accepted.values()), errors


def request_analysis(files: list[dict], config: RepoConfig):
    directory = Path(settings().analysis_directory)
    identifier = uuid.uuid4().hex
    request = directory / f"{identifier}.request.json"
    response = directory / f"{identifier}.response.json"
    envelope = AnalysisRequest(files=[SourceFile.model_validate(f) for f in files], config=config)
    try:
        atomic_json(request, envelope.model_dump())
        deadline = time.monotonic() + config.max_processing_seconds + 25
        while time.monotonic() < deadline:
            if response.exists():
                return validate_findings(read_json(response), files)
            time.sleep(0.1)
        raise TimeoutError("Isolated analyzer timed out")
    finally:
        request.unlink(missing_ok=True)
        response.unlink(missing_ok=True)


def serve_once(directory: Path):
    from codelens.worker import analyze

    for request in sorted(directory.glob("*.request.json")):
        if not re.fullmatch(r"[a-f0-9]{32}\.request\.json", request.name):
            continue
        response = request.with_name(request.name.replace(".request.", ".response."))
        try:
            envelope = AnalysisRequest.model_validate(read_json(request))
            request.unlink(missing_ok=True)
            files = [f.model_dump() for f in envelope.files]
            if len(files) > envelope.config.max_files:
                raise ValueError("File count limit exceeded")
            total = 0
            for file in files:
                if skip_reason(file["path"], envelope.config):
                    raise ValueError("Unapproved file")
                if len(file["content"].encode()) > envelope.config.max_file_bytes:
                    raise ValueError("File budget exceeded")
                total += len(file["content"].encode()) + len(file["patch"].encode())
            if total > envelope.config.max_total_bytes:
                raise ValueError("Total budget exceeded")
            findings, errors = analyze(files, envelope.config)
            atomic_json(
                response, {"findings": [f.model_dump() for f in findings], "errors": errors}
            )
        except Exception:
            request.unlink(missing_ok=True)
            atomic_json(response, {"findings": [], "errors": [{"message": "Analysis failed"}]})
        return True
    return False


def main():
    directory = Path(settings().analysis_directory)
    while True:
        try:
            serve_once(directory)
            cutoff = time.time() - 600
            for path in directory.iterdir():
                if (
                    re.fullmatch(
                        r"[a-f0-9]{32}\.(?:request\.json|response\.json|request\.tmp|response\.tmp)",
                        path.name,
                    )
                    and path.stat().st_mtime < cutoff
                ):
                    path.unlink(missing_ok=True)
            time.sleep(0.1)
        except KeyboardInterrupt:
            return
        except Exception:
            logging.error("sandbox_loop_failed")
            time.sleep(1)


if __name__ == "__main__":
    main()
