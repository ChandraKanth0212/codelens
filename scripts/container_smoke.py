"""Run inside the API container with stdin; never prints credentials or source."""

import argparse
import json
import os
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--require-existing", action="store_true")
args = parser.parse_args()
base = "http://localhost:8000"
headers = {"Authorization": "Bearer " + os.environ["CODELENS_ADMIN_TOKEN"]}


def request(path, method="GET"):
    req = urllib.request.Request(
        base + "/api/v1" + path,
        headers=headers,
        data=b"" if method == "POST" else None,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)


assert request("/health")["status"] == "ok"
with urllib.request.urlopen(base, timeout=5) as response:
    assert "CodeLens" in response.read().decode()
if args.require_existing:
    previous = request("/review-runs")
    assert any(r["is_demo"] and r["status"] == "completed" for r in previous)
for _ in range(2):
    run_id = request("/demo", "POST")["run_id"]
    for attempt in range(60):
        run = request(f"/review-runs/{run_id}")
        if run["status"] not in ("queued", "running"):
            assert run["status"] == "completed", "Synthetic review did not complete"
            assert run["report"]["ai"]["status"] == "disabled"
            findings = request(f"/review-runs/{run_id}/findings")
            assert {"F821", "F401", "eqeqeq"} <= {f["rule_id"] for f in findings}
            break
        time.sleep(2)
    else:
        raise RuntimeError("Synthetic review timed out")
print("Health, served frontend, persistent reports and real analyzer review verified")
