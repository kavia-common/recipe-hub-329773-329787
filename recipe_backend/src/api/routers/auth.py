from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import TokenResponse, UserPublic, SignupRequest
from src.db.models import User
from src.security.auth import create_access_token, get_current_user, hash_password, verify_password
from src.core.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
    description="Registers a new user with email+password. Returns the created user profile.",
    operation_id="auth_signup",
)
async def signup(payload: SignupRequest, db: AsyncSession = Depends()) -> UserPublic:
    res = await db.execute(select(User).where(User.email == payload.email))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserPublic(id=user.id, email=user.email, display_name=user.display_name)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get a JWT token",
    description="OAuth2 password flow. Use email in the 'username' field; returns a Bearer token.",
    operation_id="auth_login",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    res = await db.execute(select(User).where(User.email == form_data.username))
    user = res.scalar_one_or_none()
    if not user or not user.is_active or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=str(user.id), settings=settings)
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Get current user profile",
    description="Returns the authenticated user's profile.",
    operation_id="auth_me",
)
async def me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, display_name=user.display_name)
