from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models import Chapter, ChapterOutline, NovelProject


class NovelRepository(BaseRepository[NovelProject]):
    model = NovelProject

    async def get_by_id(self, project_id: str) -> Optional[NovelProject]:
        stmt = (
            select(NovelProject)
            .where(NovelProject.id == project_id)
            .options(
                selectinload(NovelProject.blueprint),
                selectinload(NovelProject.characters),
                selectinload(NovelProject.relationships_),
                selectinload(NovelProject.volumes),
                selectinload(NovelProject.outlines).selectinload(ChapterOutline.volume),
                selectinload(NovelProject.conversations),
                selectinload(NovelProject.chapters).selectinload(Chapter.versions),
                selectinload(NovelProject.chapters).selectinload(Chapter.evaluations),
                selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_user(self, user_id: int) -> Iterable[NovelProject]:
        result = await self.session.execute(
            select(NovelProject)
            .where(NovelProject.user_id == user_id)
            .order_by(NovelProject.updated_at.desc())
            .options(
                selectinload(NovelProject.blueprint),
                selectinload(NovelProject.outlines).selectinload(ChapterOutline.volume),
                selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
            )
        )
        return result.scalars().all()

    async def list_all(self) -> Iterable[NovelProject]:
        result = await self.session.execute(
            select(NovelProject)
            .order_by(NovelProject.updated_at.desc())
            .options(
                selectinload(NovelProject.owner),
                selectinload(NovelProject.blueprint),
                selectinload(NovelProject.outlines).selectinload(ChapterOutline.volume),
                selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
            )
        )
        return result.scalars().all()
