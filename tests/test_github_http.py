import httpx
import pytest

from codelens.github import GitHub, GitHubTransientError


def test_rate_limit_retry_is_bounded(monkeypatch):
    delays, calls = [], []
    monkeypatch.setattr("codelens.github.time.sleep", delays.append)

    def respond(request):
        calls.append(request)
        return httpx.Response(429, headers={"retry-after": "600"})

    github = object.__new__(GitHub)
    github.client = httpx.Client(
        base_url="https://api.github.com", transport=httpx.MockTransport(respond)
    )
    with pytest.raises(GitHubTransientError):
        github.request("GET", "/repos/test/repo")
    assert len(calls) == 3 and delays == [5, 5]


def test_transient_network_error_recovers(monkeypatch):
    monkeypatch.setattr("codelens.github.time.sleep", lambda seconds: None)
    calls = []

    def respond(request):
        calls.append(request)
        if len(calls) < 3:
            raise httpx.ConnectError("sensitive endpoint text")
        return httpx.Response(200, json={"ok": True})

    github = object.__new__(GitHub)
    github.client = httpx.Client(
        base_url="https://api.github.com", transport=httpx.MockTransport(respond)
    )
    assert github.request("GET", "/repos/test/repo") == {"ok": True}
    assert len(calls) == 3


def test_pagination_and_limit():
    github = object.__new__(GitHub)
    pages = []

    def request(method, path):
        pages.append(path)
        return [{}] * 30 if "page=1" in path else [{}] * 5

    github.request = request
    assert len(github.changed_files("test/repo", 1, 40)) == 35
    assert len(pages) == 2
    with pytest.raises(Exception, match="count exceeds"):
        github.changed_files("test/repo", 1, 20)
