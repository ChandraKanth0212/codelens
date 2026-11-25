import json
import threading
import time

import pytest

from codelens.demo import FILES
from codelens.sandbox import request_analysis, serve_once, validate_findings
from codelens.schemas import RepoConfig
from codelens.settings import settings


def test_spool_roundtrip_with_real_analyzers(tmp_path, monkeypatch):
    monkeypatch.setenv("CODELENS_ANALYSIS_DIRECTORY", str(tmp_path))
    settings.cache_clear()
    done = threading.Event()

    def runner():
        while not done.is_set():
            if serve_once(tmp_path):
                break
            time.sleep(0.01)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    try:
        findings, errors = request_analysis(FILES, RepoConfig())
        assert not errors
        assert {f.analyzer for f in findings} == {"ruff", "eslint"}
        assert not list(tmp_path.glob("*.json"))
    finally:
        done.set()
        thread.join(timeout=2)
        settings.cache_clear()


def test_runner_rejects_unapproved_path(tmp_path):
    request = tmp_path / ("a" * 32 + ".request.json")
    request.write_text(
        json.dumps(
            {"files": [{"path": "../escape.py", "content": "x", "patch": "+x"}], "config": {}}
        )
    )
    assert serve_once(tmp_path)
    assert not request.exists()
    response = json.loads(next(tmp_path.glob("*.response.json")).read_text())
    assert response["errors"] and response["findings"] == []


def test_untrusted_finding_outside_diff_rejected():
    finding = {
        "source": "static_analyzer",
        "analyzer": "ruff",
        "rule_id": "F821",
        "severity": "medium",
        "category": "bug",
        "title": "Test",
        "file_path": "src/payments.py",
        "start_line": 999,
        "end_line": 999,
        "explanation": "Test",
        "suggested_action": "Test",
    }
    with pytest.raises(ValueError, match="outside"):
        validate_findings({"findings": [finding]}, FILES)


def test_processing_budget_preserves_prior_findings(monkeypatch):
    import codelens.worker as worker

    times = iter([0, 0, 10])
    monkeypatch.setattr(worker.time, "monotonic", lambda: next(times))
    findings, errors = worker.analyze([FILES[0]], RepoConfig(max_processing_seconds=5))
    assert findings and errors
    assert "time limit" in errors[0]["message"]
