from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import TagResponse
from src.db.models import Tag
from src.security.auth import get_current_user
from src.db.models import User

router = APIRouter(prefix="/tags", tags=["tags"])


class TagCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="Tag name (unique)")


@router.get(
    "",
    response_model=list[TagResponse],
    summary="List tags",
    description="List all tags (categories/tags) available in the system.",
    operation_id="tags_list",
)
async def list_tags(db: AsyncSession = Depends()) -> list[TagResponse]:
    res = await db.execute(select(Tag).order_by(Tag.name.asc()))
    tags = res.scalars().all()
    return [TagResponse(id=t.id, name=t.name) for t in tags]


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tag",
    description="Creates a tag; requires authentication.",
    operation_id="tags_create",
)
async def create_tag(
    payload: TagCreateRequest,
    db: AsyncSession = Depends(),
    _user: User = Depends(get_current_user),
) -> TagResponse:
    existing = await db.execute(select(Tag).where(Tag.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists")
    tag = Tag(name=payload.name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return TagResponse(id=tag.id, name=tag.name)
