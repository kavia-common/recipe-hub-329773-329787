from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.db.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """
    Hash a plaintext password.

    Contract:
      - Inputs: password (non-empty)
      - Outputs: password hash
      - Errors: ValueError on empty password
      - Side effects: none
    """
    if not password:
        raise ValueError("password must be non-empty")
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against a stored hash.

    Returns:
      bool: True if valid, False otherwise.
    """
    return pwd_context.verify(password, password_hash)


# PUBLIC_INTERFACE
def create_access_token(*, subject: str, settings: Settings) -> str:
    """
    Create a signed JWT access token.

    Contract:
      - Inputs: subject (typically user_id as string), settings
      - Outputs: JWT string
      - Errors: ValueError if subject empty
      - Side effects: none
    """
    if not subject:
        raise ValueError("subject is required")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.jwt_access_token_expires_minutes)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": exp}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decode_token(token: str, settings: Settings) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e


# PUBLIC_INTERFACE
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(),
    settings: Settings = Depends(get_settings),
) -> User:
    """
    Resolve the authenticated user from Bearer token.

    Contract:
      - Inputs: Bearer JWT token; AsyncSession; Settings
      - Outputs: User ORM object
      - Errors: HTTP 401 if token invalid/expired; HTTP 401 if user not found/inactive
      - Side effects: DB read
    """
    payload = _decode_token(token, settings)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    try:
        user_id = int(subject)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from e

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user
