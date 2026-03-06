from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas import RecipeCreateRequest, RecipeResponse, RecipeUpdateRequest, TagResponse
from src.db.models import Recipe, RecipeTag, Tag, User
from src.security.auth import get_current_user

router = APIRouter(prefix="/recipes", tags=["recipes"])


async def _get_or_create_tags(db: AsyncSession, tag_names: list[str]) -> list[Tag]:
    normalized = []
    for n in tag_names:
        nn = n.strip()
        if nn and nn not in normalized:
            normalized.append(nn)

    if not normalized:
        return []

    res = await db.execute(select(Tag).where(Tag.name.in_(normalized)))
    existing = {t.name: t for t in res.scalars().all()}

    tags: list[Tag] = []
    for name in normalized:
        t = existing.get(name)
        if not t:
            t = Tag(name=name)
            db.add(t)
            tags.append(t)
        else:
            tags.append(t)

    # Flush so new Tag IDs exist before inserting join rows.
    await db.flush()
    return tags


def _recipe_to_response(recipe: Recipe) -> RecipeResponse:
    tags = []
    for rt in recipe.tags:
        # relationship(rt.tag) may not be loaded in some selects; prefer safe access
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
    response_model=list[RecipeResponse],
    summary="List/search recipes",
    description="List recipes with optional text search on title/description and optional tag filter.",
    operation_id="recipes_list",
)
async def list_recipes(
    q: str | None = Query(None, description="Search query for title/description"),
    tag: str | None = Query(None, description="Filter by tag name"),
    db: AsyncSession = Depends(),
) -> list[RecipeResponse]:
    stmt = (
        select(Recipe)
        .options(selectinload(Recipe.tags).selectinload(RecipeTag.tag))
        .order_by(Recipe.created_at.desc())
    )

    if q:
        stmt = stmt.where(or_(Recipe.title.ilike(f"%{q}%"), Recipe.description.ilike(f"%{q}%")))
    if tag:
        stmt = stmt.join(RecipeTag).join(Tag).where(Tag.name == tag)

    res = await db.execute(stmt)
    recipes = res.scalars().unique().all()
    return [_recipe_to_response(r) for r in recipes]


@router.get(
    "/{recipe_id}",
    response_model=RecipeResponse,
    summary="Get recipe details",
    description="Get a single recipe by ID.",
    operation_id="recipes_get",
)
async def get_recipe(recipe_id: int, db: AsyncSession = Depends()) -> RecipeResponse:
    res = await db.execute(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.tags).selectinload(RecipeTag.tag))
    )
    recipe = res.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return _recipe_to_response(recipe)


@router.post(
    "",
    response_model=RecipeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recipe",
    description="Create a new recipe authored by the current user.",
    operation_id="recipes_create",
)
async def create_recipe(
    payload: RecipeCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(),
) -> RecipeResponse:
    recipe = Recipe(
        author_id=user.id,
        title=payload.title,
        description=payload.description,
        ingredients=payload.ingredients,
        steps=payload.steps,
    )
    db.add(recipe)
    await db.flush()

    tags = await _get_or_create_tags(db, payload.tag_names)
    for t in tags:
        db.add(RecipeTag(recipe_id=recipe.id, tag_id=t.id))

    await db.commit()
    # reload with tags
    res = await db.execute(
        select(Recipe)
        .where(Recipe.id == recipe.id)
        .options(selectinload(Recipe.tags).selectinload(RecipeTag.tag))
    )
    recipe = res.scalar_one()
    return _recipe_to_response(recipe)


@router.patch(
    "/{recipe_id}",
    response_model=RecipeResponse,
    summary="Update a recipe",
    description="Update an existing recipe. Only the author may update.",
    operation_id="recipes_update",
)
async def update_recipe(
    recipe_id: int,
    payload: RecipeUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(),
) -> RecipeResponse:
    res = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = res.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    if recipe.author_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the recipe author")

    if payload.title is not None:
        recipe.title = payload.title
    if payload.description is not None:
        recipe.description = payload.description
    if payload.ingredients is not None:
        recipe.ingredients = payload.ingredients
    if payload.steps is not None:
        recipe.steps = payload.steps

    if payload.tag_names is not None:
        # Clear existing tags and re-add
        await db.execute(delete(RecipeTag).where(RecipeTag.recipe_id == recipe.id))
        tags = await _get_or_create_tags(db, payload.tag_names)
        for t in tags:
            db.add(RecipeTag(recipe_id=recipe.id, tag_id=t.id))

    await db.commit()

    res2 = await db.execute(
        select(Recipe)
        .where(Recipe.id == recipe.id)
        .options(selectinload(Recipe.tags).selectinload(RecipeTag.tag))
    )
    recipe = res2.scalar_one()
    return _recipe_to_response(recipe)


@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recipe",
    description="Delete a recipe. Only the author may delete.",
    operation_id="recipes_delete",
)
async def delete_recipe(
    recipe_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(),
) -> None:
    res = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = res.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    if recipe.author_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the recipe author")

    await db.execute(delete(Recipe).where(Recipe.id == recipe.id))
    await db.commit()
    return None
