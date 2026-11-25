"""Fixed analyzer commands: no project plugins, configs, installs, or execution."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from codelens.schemas import Finding

ROOT = Path(__file__).resolve().parent.parent
SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "github-token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{50,255})\b"),
    ),
    ("aws-access-id", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
]


def secrets(path: str, content: str, lines: set[int]) -> list[Finding]:
    found = []
    for number, text in enumerate(content.splitlines(), 1):
        if number not in lines:
            continue
        for rule, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                found.append(
                    Finding(
                        source="secret_scanner",
                        analyzer="codelens-secrets",
                        rule_id=rule,
                        severity="critical",
                        category="security",
                        title="Possible exposed credential",
                        file_path=path,
                        start_line=number,
                        end_line=number,
                        explanation="An added line matches a credential format. The value is redacted.",
                        suggested_action="Verify the match; revoke and rotate the credential if real.",
                        evidence="[REDACTED]",
                        confidence="medium",
                    )
                )
    return found


def run_command(command: list[str], content: str):
    # Strip application credentials from child-process environments.
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "LANG"}
    }
    result = subprocess.run(
        command,
        input=content,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        cwd=ROOT,
        env=env,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError("Analyzer failed; raw output withheld to protect source content")
    if len(result.stdout) > 2_000_000:
        raise RuntimeError("Analyzer output limit exceeded")
    return json.loads(result.stdout)


def lint(path: str, content: str, lines: set[int], analyzer: str) -> list[Finding]:
    if analyzer == "ruff":
        executable = shutil.which("ruff")
        if not executable:
            raise RuntimeError("Ruff is not installed")
        output = run_command(
            [
                executable,
                "check",
                "--isolated",
                "--no-cache",
                "--select",
                "E9,F63,F7,F82,F401,B,S307",
                "--output-format",
                "json",
                "--stdin-filename",
                path,
                "-",
            ],
            content,
        )
        rows = [(x.get("code") or "syntax", x["location"]["row"]) for x in output]
    else:
        node = shutil.which("node")
        if not node:
            raise RuntimeError("Node.js is not installed")
        output = run_command([node, str(ROOT / "analyzer/scan.mjs"), path], content)
        rows = [(x.get("ruleId") or "syntax", x.get("line", 1)) for x in output]
    findings = []
    for rule, line in rows:
        if line not in lines:
            continue
        security = rule in {"S307", "no-eval", "no-implied-eval"}
        descriptions = {
            "F401": ("Unused import", "Remove the import or use it explicitly."),
            "F821": ("Undefined name", "Define or import the name before using it."),
            "S307": ("Dynamic code evaluation", "Use explicit parsing instead of eval."),
            "no-eval": ("Dynamic code evaluation", "Replace eval with explicit parsing."),
            "eqeqeq": (
                "Coercive equality comparison",
                "Use === or !== to avoid implicit conversion.",
            ),
            "no-unused-vars": ("Unused variable", "Remove the variable or use it explicitly."),
            "@typescript-eslint/no-unused-vars": (
                "Unused variable",
                "Remove the variable or use it explicitly.",
            ),
            "no-undef": ("Undefined name", "Define or import the name before using it."),
        }
        title, action = descriptions.get(
            rule, (f"{analyzer} rule {rule}", "Inspect the rule documentation and changed line.")
        )
        findings.append(
            Finding(
                source="static_analyzer",
                analyzer=analyzer,
                rule_id=rule,
                severity="high"
                if security
                else "medium"
                if rule in {"F821", "no-undef", "syntax"}
                else "low",
                category="security"
                if security
                else "correctness"
                if rule in {"F821", "no-undef", "syntax"}
                else "maintainability",
                title=title,
                file_path=path,
                start_line=line,
                end_line=line,
                explanation=f"{analyzer} reported {rule} on an added line. Source values are not retained.",
                suggested_action=action,
            )
        )
    return findings
