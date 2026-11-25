import base64

import pytest

from codelens.github import GitHub, GitHubError
from codelens.schemas import RepoConfig


def fake_github():
    return object.__new__(GitHub)


def test_refuses_stale_commit():
    github = fake_github()
    github.request = lambda *args: {"head": {"sha": "b" * 40}}
    with pytest.raises(GitHubError, match="changed before"):
        github.retrieve("test/repo", 1, "a" * 40, RepoConfig())


def test_file_count_limit_before_fetch():
    github = fake_github()
    github.request = lambda *args: {"head": {"sha": "a" * 40}, "changed_files": 200}
    with pytest.raises(GitHubError, match="count"):
        github.retrieve("test/repo", 1, "a" * 40, RepoConfig())


def test_excluded_content_never_fetched():
    github = fake_github()

    def request(method, path):
        if "/files?" in path:
            return [
                {"filename": ".env", "status": "modified", "patch": "@@ -0,0 +1 @@\n+TOKEN=x"},
                {"filename": "src/a.py", "status": "modified", "patch": "@@ -0,0 +1 @@\n+print(1)"},
            ]
        return {"head": {"sha": "a" * 40}, "base": {"sha": "b" * 40}, "changed_files": 2}

    def content(repo, path, sha, limit):
        if path == ".codelens.yml":
            raise FileNotFoundError()
        assert path == "src/a.py"
        assert sha == "a" * 40
        return "print(1)"

    github.request, github.content = request, content
    files, skipped, _ = github.retrieve("test/repo", 1, "a" * 40, RepoConfig())
    assert len(files) == len(skipped) == 1


def test_base_config_cannot_enable_ai_or_raise_limits():
    github = fake_github()
    github.request = (
        lambda method, path: []
        if "/files?" in path
        else {"head": {"sha": "a" * 40}, "base": {"sha": "b" * 40}, "changed_files": 0}
    )
    github.content = lambda *args: "version: 1\nai_enabled: true\nmax_files: 100"
    _, _, config = github.retrieve("test/repo", 1, "a" * 40, RepoConfig(max_files=10))
    assert not config.ai_enabled
    assert config.max_files == 10


@pytest.mark.parametrize("value", [b"\x00binary", b"x" * 2000])
def test_binary_and_size_limit(value):
    github = fake_github()
    github.request = lambda *args: {
        "type": "file",
        "size": len(value),
        "encoding": "base64",
        "content": base64.b64encode(value).decode(),
    }
    with pytest.raises(GitHubError):
        github.content("test/repo", "a.py", "a" * 40, 1000)
