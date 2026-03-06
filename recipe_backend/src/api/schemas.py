from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type for Authorization header")


class UserPublic(BaseModel):
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    display_name: str | None = Field(None, description="Optional display name")


class SignupRequest(BaseModel):
    email: str = Field(..., description="User email (unique)")
    password: str = Field(..., min_length=6, description="User password (min 6 chars)")
    display_name: str | None = Field(None, description="Optional display name")


class LoginRequest(BaseModel):
    username: str = Field(..., description="OAuth2 username field (we use email)")
    password: str = Field(..., description="Password")


class TagResponse(BaseModel):
    id: int = Field(..., description="Tag ID")
    name: str = Field(..., description="Tag name")


class RecipeBase(BaseModel):
    title: str = Field(..., description="Recipe title")
    description: str | None = Field(None, description="Short recipe description")
    ingredients: list[dict[str, Any]] = Field(default_factory=list, description="List of ingredient objects")
    steps: list[dict[str, Any]] = Field(default_factory=list, description="List of step objects")
    tag_names: list[str] = Field(default_factory=list, description="List of tag names to associate with recipe")


class RecipeCreateRequest(RecipeBase):
    pass


class RecipeUpdateRequest(BaseModel):
    title: str | None = Field(None, description="Recipe title")
    description: str | None = Field(None, description="Short recipe description")
    ingredients: list[dict[str, Any]] | None = Field(None, description="List of ingredient objects")
    steps: list[dict[str, Any]] | None = Field(None, description="List of step objects")
    tag_names: list[str] | None = Field(None, description="List of tag names to associate with recipe")


class RecipeResponse(BaseModel):
    id: int = Field(..., description="Recipe ID")
    author_id: int = Field(..., description="Author user ID")
    title: str = Field(..., description="Recipe title")
    description: str | None = Field(None, description="Short recipe description")
    ingredients: list[dict[str, Any]] = Field(..., description="Ingredients payload")
    steps: list[dict[str, Any]] = Field(..., description="Steps payload")
    tags: list[TagResponse] = Field(default_factory=list, description="Associated tags")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")


class FavoriteResponse(BaseModel):
    recipe_id: int = Field(..., description="Favorited recipe ID")
    created_at: datetime = Field(..., description="Time favorited (UTC)")
