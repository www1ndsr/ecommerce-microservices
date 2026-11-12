from dataclasses import dataclass

import jwt
from fastapi import HTTPException

from .config import settings


@dataclass(frozen=True)
class Principal:
    user_id: int
    role: str


def is_public_endpoint(method: str, path: str) -> bool:
    if method == "POST" and path in {
        "/api/auth/register",
        "/api/auth/login",
    }:
        return True
    return method == "GET" and (
        path == "/api/products" or path.startswith("/api/products/")
    )


def authenticate(authorization: str | None) -> Principal:
    unauthorized = HTTPException(
        status_code=401,
        detail="Missing or invalid bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization:
        raise unauthorized

    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token.strip():
        raise unauthorized

    try:
        claims = jwt.decode(
            token.strip(),
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "role"]},
        )
        subject = claims["sub"]
        role = claims["role"]
        if not isinstance(subject, str) or not subject.isdecimal():
            raise ValueError("Invalid user ID claim")
        if not isinstance(role, str) or not role:
            raise ValueError("Invalid role claim")
        user_id = int(subject)
        if user_id < 1:
            raise ValueError("Invalid user ID claim")
    except (jwt.PyJWTError, TypeError, ValueError, OverflowError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    return Principal(user_id=user_id, role=role)


def require_admin(principal: Principal):
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
