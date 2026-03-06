from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routers import all_routers
from src.core.config import get_settings
from src.db.session import create_engine, create_session_factory, get_db_session

openapi_tags = [
    {"name": "health", "description": "Service health and diagnostics."},
    {"name": "auth", "description": "JWT authentication endpoints (signup/login/me)."},
    {"name": "recipes", "description": "Recipe CRUD and search."},
    {"name": "favorites", "description": "Favorite/unfavorite recipes and list favorites."},
    {"name": "tags", "description": "Categories/Tags management."},
]

app = FastAPI(
    title="Recipe Hub Backend API",
    description=(
        "Backend for Recipe Hub: authentication, recipe CRUD, favorites, and tags.\n\n"
        "Authentication: Use `POST /auth/login` (OAuth2 password flow) to obtain a JWT.\n"
        "Then call protected endpoints with `Authorization: Bearer <token>`.\n"
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

_settings = get_settings()
_engine = create_engine(_settings.database_url)
_session_factory = create_session_factory(_engine)


# PUBLIC_INTERFACE
def db_session_dep() -> AsyncSession:
    """
    FastAPI dependency provider for AsyncSession.

    This indirection ensures all routers share one canonical session factory.
    """
    return Depends(lambda: get_db_session(_session_factory))  # type: ignore[return-value]


# Dependency override: we want `Depends()` in routers to resolve to DB session consistently.
async def _db_override() -> AsyncSession:
    async for s in get_db_session(_session_factory):
        return s
    raise RuntimeError("Failed to create DB session")


app.dependency_overrides[AsyncSession] = _db_override  # type: ignore[assignment]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"], summary="Health check", operation_id="health_check")
def health_check() -> dict:
    """Return a basic health response."""
    return {"message": "Healthy"}


@app.get(
    "/docs/help",
    tags=["health"],
    summary="API usage help",
    description="Quick notes on auth usage and common request patterns.",
    operation_id="docs_help",
)
def docs_help() -> dict:
    """Provide minimal usage help for developers consuming the API."""
    return {
        "auth": {
            "login": "POST /auth/login with form fields: username=<email>, password=<password>",
            "header": "Authorization: Bearer <access_token>",
        },
        "recipes": {
            "create": "POST /recipes (requires auth)",
            "list": "GET /recipes?q=<optional>&tag=<optional>",
        },
    }


for r in all_routers:
    app.include_router(r)
