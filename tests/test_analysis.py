import pytest

from codelens.analyzers import lint, secrets
from codelens.demo import FILES
from codelens.diffs import added_lines, safe_path, skip_reason
from codelens.schemas import RepoConfig
from codelens.worker import analyze


def test_diff_line_mapping():
    patch = "@@ -10,3 +10,4 @@\n context\n-old\n+new\n+newer\n context\n@@ -30 +31 @@\n-old\n+new"
    assert added_lines(patch) == {11, 12, 31}


@pytest.mark.parametrize("path", ["../evil.py", "/root.py", "C:/x.py", "x\\y.py", "a\x00.py"])
def test_unsafe_paths(path):
    assert not safe_path(path)


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        "src/.env.py",
        "node_modules/x.js",
        "src/credentials.py",
        "app.min.js",
        "assets/logo.png",
    ],
)
def test_default_exclusions(path):
    assert skip_reason(path, RepoConfig())


def test_config_exclusions():
    assert skip_reason("tests/x.py", RepoConfig(exclude=["tests/*"]))
    assert not skip_reason("src/x.py", RepoConfig(include=["src/*"]))


def test_secret_redaction():
    value = "ghp_" + "a" * 36
    results = secrets("app.py", f'token = "{value}"', {1})
    assert len(results) == 1
    assert value not in results[0].model_dump_json()
    assert secrets("app.py", f'token = "{value}"', {2}) == []


def test_real_ruff_changed_lines_only():
    findings = lint("sample.py", "import os\nprint(missing)\n", {2}, "ruff")
    assert [f.rule_id for f in findings] == ["F821"]


def test_real_eslint_typescript():
    findings = lint("sample.ts", "export const check = (x: number) => x == 1;\n", {1}, "eslint")
    assert "eqeqeq" in [f.rule_id for f in findings]


def test_analysis_failure_preserves_success(monkeypatch):
    import codelens.worker as worker

    original = worker.lint

    def fail_js(path, content, lines, analyzer):
        if analyzer == "eslint":
            raise RuntimeError("sensitive source must not be exposed")
        return original(path, content, lines, analyzer)

    monkeypatch.setattr(worker, "lint", fail_js)
    findings, errors = analyze(FILES, RepoConfig())
    assert findings and errors
    assert "sensitive source" not in str(errors)


def test_deduplication():
    findings, errors = analyze([FILES[0], FILES[0]], RepoConfig())
    assert not errors
    assert len(findings) == len({f.fingerprint for f in findings})
