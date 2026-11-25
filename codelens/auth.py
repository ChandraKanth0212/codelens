"""Local high-entropy access tokens, hashed at rest, with object-level permissions."""

import hashlib
import hmac
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select

from codelens.db import Repository, RepositoryAccess, User, get_session
from codelens.settings import settings


@dataclass(frozen=True)
class Principal:
    user_id: int | None
    is_operator: bool = False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticated(authorization: str = Header(default=""), session=Depends(get_session)):
    expected = settings().admin_token.get_secret_value()
    if expected and hmac.compare_digest(authorization.encode(), f"Bearer {expected}".encode()):
        return Principal(None, True)
    if not authorization.startswith("Bearer ") or len(authorization) > 256:
        raise HTTPException(401, "A valid access token is required")
    token = authorization[7:]
    user = session.scalar(
        select(User).where(User.token_hash == hash_token(token), User.enabled.is_(True))
    )
    if not user:
        raise HTTPException(401, "A valid access token is required")
    return Principal(user.id)


def operator(principal=Depends(authenticated)):
    if not principal.is_operator:
        raise HTTPException(403, "Operator access required")
    return principal


def permitted_ids(principal: Principal):
    if principal.is_operator:
        return select(Repository.id)
    return select(RepositoryAccess.repository_id).where(
        RepositoryAccess.user_id == principal.user_id
    )


def can_configure(session, principal: Principal, repo_id: int):
    if principal.is_operator:
        return True
    access = session.get(RepositoryAccess, (principal.user_id, repo_id))
    return bool(access and access.role == "owner")


def require_repository(session, principal: Principal, repo_id: int, write=False):
    repo = session.get(Repository, repo_id)
    if not repo:
        raise HTTPException(404, "Repository not found")
    if not principal.is_operator:
        access = session.get(RepositoryAccess, (principal.user_id, repo_id))
        if not access:
            raise HTTPException(404, "Repository not found")
        if write and access.role != "owner":
            raise HTTPException(403, "Repository owner access required")
    return repo
