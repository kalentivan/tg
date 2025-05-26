import uuid
from typing import Any, List, Optional, Self, Sequence, TypeVar

from fastapi import HTTPException
from sqlalchemy import Column, Row, RowMapping, Uuid, select, update
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from starlette import status

from app.tools import validate_uuid

T = TypeVar("T", bound="Base")


class Base(AsyncAttrs, DeclarativeBase):

    @property
    def fields(self) -> tuple:
        return tuple()

    def to_dict(self):
        _ = getattr
        return {f: _(self, f) if not isinstance(_(self, f), uuid.UUID) else str(_(self, f)) for f in self.fields}

    @classmethod
    async def get_or_404(cls,
                         session: Optional[AsyncSession],
                         er_status=status.HTTP_404_NOT_FOUND, er_msg=None, **kwargs) -> Self:
        """
        Возвращает первый объект, соответствующий фильтру, или вызывает HTTPException 404.
        Пример: await User.get_or_404(id=1)
        """
        result = await session.execute(select(cls).filter_by(**kwargs))
        obj = result.scalar_one_or_none()
        if obj is None:
            raise HTTPException(status_code=er_status, detail=er_msg or f"{cls.__name__} with {kwargs} not found")
        return obj

    @classmethod
    async def first(cls,
                    session: Optional[AsyncSession] = None, **kwargs) -> Self:
        """
        Возвращает первый объект, соответствующий фильтру, или None.
        Пример: await User.first(email="alice@example.com")
        """
        result = await session.execute(select(cls).filter_by(**kwargs))
        return result.scalar_one_or_none()

    @classmethod
    async def list_rows(cls, session: Optional[AsyncSession] = None, **kwargs) -> List[dict]:
        """
        Возвращает список словарей напрямую из базы данных, соответствующих фильтру.
        Пример: await User.list_rows(is_active=True)
        """
        # Получаем столбцы из fields
        columns = [getattr(cls, field) for field in cls().fields]
        # Формируем запрос с указанными столбцами
        query = select(*columns).filter_by(**kwargs)
        result = await session.execute(query)
        # Преобразуем результат в список словарей
        return [dict(row) for row in result.mappings()]

    @classmethod
    async def list(cls, session: Optional[AsyncSession] = None, **kwargs) -> Sequence[
                                                                                 Row[Any] | RowMapping | Any] | Any:
        """
        Возвращает список объектов, соответствующих фильтру.
        Пример: await User.list(is_active=True)
        """
        result = await session.execute(select(cls).filter_by(**kwargs))
        return result.scalars().all()

    async def delete(self, session: AsyncSession = None):
        """
        Удаляет объект из базы данных.
        """
        await session.delete(self)
        await session.commit()


class BaseId(Base):
    __abstract__ = True  # Указываем, что это абстрактный класс
    id = Column(Uuid, primary_key=True, index=True, default=uuid.uuid4)

    @property
    def fields(self):
        return super().fields + ("id", )

    @classmethod
    async def by_ids(cls,
                     ids: List[str],
                     session: Optional[AsyncSession] = None) -> list[Any] | Sequence[Self]:
        """
        Возвращает список объектов, соответствующих списку ID.
        Пример: await User.by_ids(ids=[1, 2, 3])
        """
        if not ids:  # Если список ID пуст, возвращаем пустой список
            return []
        ids = [validate_uuid(item_id) for item_id in ids]
        result = await session.execute(select(cls).where(cls.id.in_(ids)))
        return result.scalars().all()

    async def save(self,
                   session: Optional[AsyncSession] = None,
                   update_fields: Optional[List[str]] = None):
        """
        Сохраняет объект в базе данных (создание или обновление).
        :param session: Асинхронная сессия
        :param update_fields: Список полей для обновления (если None, сохраняется весь объект)
        """
        if self.id is None or not update_fields:  # Новый объект или полное обновление
            session.add(self)
            await session.commit()
            await session.refresh(self)
            return
        # Формируем словарь только с указанными полями
        values = {field: getattr(self, field) for field in update_fields if hasattr(self, field)}
        if values:
            stmt = update(self.__class__).where(self.__class__.id == self.id).values(**values)
            await session.execute(stmt)
            await session.commit()
            await session.refresh(self)

    @classmethod
    async def create(cls, session: Optional[AsyncSession] = None, **kwargs) -> Self:
        """
        Создаёт новый объект модели и сохраняет его в базе данных.
        Пример: await User.create(email="alice@example.com", password="hashed_password")
        """
        obj = cls(**kwargs)
        await obj.save(session)
        return obj
