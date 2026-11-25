"""Create local-only secrets. Never overwrites an existing .env."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parent.parent
target = root / ".env"
if target.exists():
    print(".env already exists; no changes made.")
else:
    text = (root / ".env.example").read_text()
    text = text.replace(
        "replace-with-a-random-token-at-least-32-characters", secrets.token_urlsafe(32)
    )
    text = text.replace("replace-with-another-random-secret", secrets.token_urlsafe(32))
    target.write_text(text, encoding="utf-8")
    print(
        "Created .env with independent random secrets. Open it locally to copy your operator token."
    )
