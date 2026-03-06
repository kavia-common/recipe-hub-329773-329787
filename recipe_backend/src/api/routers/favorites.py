from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas import FavoriteResponse, RecipeResponse, TagResponse
from src.db.models import Favorite, Recipe, RecipeTag, User
from src.security.auth import get_current_user

router = APIRouter(prefix="/favorites", tags=["favorites"])


def _favorite_to_response(fav: Favorite) -> FavoriteResponse:
    created_at = fav.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return FavoriteResponse(recipe_id=fav.recipe_id, created_at=created_at)


def _recipe_to_response(recipe: Recipe) -> RecipeResponse:
    tags = []
    for rt in recipe.tags:
        if getattr(rt, "tag", None) is not None:
            tags.append(TagResponse(id=rt.tag.id, name=rt.tag.name))
    created_at = recipe.created_at
    updated_at = recipe.updated_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return RecipeResponse(
        id=recipe.id,
        author_id=recipe.author_id,
        title=recipe.title,
        description=recipe.description,
        ingredients=recipe.ingredients or [],
        steps=recipe.steps or [],
        tags=tags,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.get(
    "",
    response_model=list[FavoriteResponse],
    summary="List my favorites",
    description="List favorited recipe IDs for the current user.",
    operation_id="favorites_list",
)
async def list_favorites(user: User = Depends(get_current_user), db: AsyncSession = Depends()) -> list[FavoriteResponse]:
    res = await db.execute(select(Favorite).where(Favorite.user_id == user.id).order_by(Favorite.created_at.desc()))
    favs = res.scalars().all()
    return [_favorite_to_response(f) for f in favs]


@router.get(
    "/recipes",
    response_model=list[RecipeResponse],
    summary="List my favorited recipes",
    description="List full recipe objects that the current user has favorited.",
    operation_id="favorites_list_recipes",
)
async def list_favorite_recipes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(),
) -> list[RecipeResponse]:
    stmt = (
        select(Recipe)
        .join(Favorite, Favorite.recipe_id == Recipe.id)
        .where(Favorite.user_id == user.id)
        .options(selectinload(Recipe.tags).selectinload(RecipeTag.tag))
        .order_by(Favorite.created_at.desc())
    )
    res = await db.execute(stmt)
    recipes = res.scalars().unique().all()
    return [_recipe_to_response(r) for r in recipes]


@router.post(
    "/{recipe_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Favorite a recipe",
    description="Adds a recipe to the current user's favorites.",
    operation_id="favorites_add",
)
async def add_favorite(
    recipe_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(),
) -> FavoriteResponse:
    recipe_res = await db.execute(select(Recipe.id).where(Recipe.id == recipe_id))
    if recipe_res.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    existing = await db.execute(select(Favorite).where(Favorite.user_id == user.id, Favorite.recipe_id == recipe_id))
    fav = existing.scalar_one_or_none()
    if fav:
        return _favorite_to_response(fav)

    fav = Favorite(user_id=user.id, recipe_id=recipe_id)
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    return _favorite_to_response(fav)


@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unfavorite a recipe",
    description="Removes a recipe from the current user's favorites.",
    operation_id="favorites_remove",
)
async def remove_favorite(
    recipe_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(),
) -> None:
    await db.execute(delete(Favorite).where(Favorite.user_id == user.id, Favorite.recipe_id == recipe_id))
    await db.commit()
    return None
