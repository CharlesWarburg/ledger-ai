import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

password_hasher = PasswordHasher()


class TokenValidationError(ValueError):
    pass


def _jwt_secret_key() -> str:
    secret_key = settings.jwt_secret_key.get_secret_value()
    if len(secret_key) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters")
    return secret_key


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(hashed_password, password)
    except (InvalidHashError, VerificationError):
        return False


def create_access_token(
    user_id: uuid.UUID,
    expires_delta: Optional[timedelta] = None,
) -> str:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    claims = {
        "sub": str(user_id),
        "type": "access",
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(
        claims,
        _jwt_secret_key(),
        algorithm=settings.jwt_algorithm,
    )


def validate_access_token(token: str) -> uuid.UUID:
    try:
        claims = jwt.decode(
            token,
            _jwt_secret_key(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "type", "iat", "exp"]},
        )
        if claims["type"] != "access":
            raise TokenValidationError("Invalid token type")
        return uuid.UUID(claims["sub"])
    except TokenValidationError:
        raise
    except (jwt.PyJWTError, TypeError, ValueError) as exc:
        raise TokenValidationError("Invalid or expired access token") from exc
