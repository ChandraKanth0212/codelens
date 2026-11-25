"""Operator-only local CLI: provision/revoke users without a public registration endpoint."""

import argparse
import secrets

from sqlalchemy import select

from codelens.auth import hash_token
from codelens.db import Repository, RepositoryAccess, Session, User


def provision(session, email: str, display_name: str, repositories: list[int], role: str):
    if role not in {"owner", "reviewer"}:
        raise ValueError("Invalid repository role")
    if session.scalar(select(User).where(User.email == email)):
        raise ValueError("User exists; revoke it or use another identity")
    for repo_id in repositories:
        if not session.get(Repository, repo_id):
            raise ValueError("Unknown repository")
    token = secrets.token_urlsafe(32)
    user = User(email=email, display_name=display_name, token_hash=hash_token(token))
    session.add(user)
    session.flush()
    for repo_id in set(repositories):
        session.add(RepositoryAccess(user_id=user.id, repository_id=repo_id, role=role))
    session.commit()
    return token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--repository-id", type=int, action="append", required=True)
    create.add_argument("--role", choices=["owner", "reviewer"], default="reviewer")
    revoke = sub.add_parser("revoke")
    revoke.add_argument("--email", required=True)
    args = parser.parse_args()
    with Session() as session:
        if args.command == "create":
            token = provision(session, args.email, args.name, args.repository_id, args.role)
            print("Copy this token securely; it will not be shown again:")
            print(token)
        else:
            user = session.scalar(select(User).where(User.email == args.email))
            if not user:
                raise SystemExit("User not found")
            user.enabled = False
            session.commit()
            print("User access revoked.")


if __name__ == "__main__":
    main()
