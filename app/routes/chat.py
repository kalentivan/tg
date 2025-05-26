from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.auth.auth import get_current_user
from app.database import AsyncSessionLocal, get_db
from app.dto import ChatCreateDTO, ChatDTO, MemberAddDTO, MembersIdsDTO, MessageHistoryDTO
from app.models.models import Chat, GroupMember, Message, User
from app.tools import validate_uuid

router = APIRouter(tags=["chat"])


@router.post("/chat/",
             response_model=ChatDTO)
async def router_create_chat(
        chat_data: ChatCreateDTO,
        user: User = Depends(get_current_user),
        session=Depends(get_db)
) -> ChatDTO:
    """
    Создание личного или группового чата.
    Для личного чата: member_ids должен содержать ровно один ID.
    Для группового чата: member_ids может содержать несколько ID.
    """
    if not chat_data.is_group and len(chat_data.member_ids) != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Личный чат должен содержать ровно одного участника")
    if chat_data.is_group and not chat_data.name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Групповой чат должен иметь название")

    # Проверяем, что все указанные пользователи существуют
    members = await User.by_ids(ids=chat_data.member_ids, session=session)
    if len(members) != len(chat_data.member_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Один или несколько пользователей не найдены")

    # Добавляем создателя в участники, если его нет
    if user not in members:
        members.append(user)  # Создатель всегда участник

    # Создаем чат
    chat = await Chat.create(name=chat_data.name, is_group=chat_data.is_group, session=session)

    # Добавляем участников одним запросом
    group_members = [GroupMember(user_id=member.id, is_admin=True, chat_id=chat.id) for member in members]
    session.add_all(group_members)
    await session.commit()
    return chat.to_dict()


@router.delete("/chat/{chat_id}/")
async def router_delete_chat(
        chat_id: str,
        user: User = Depends(get_current_user),
        session=Depends(get_db)
) -> Response:
    """
    Удаление чата. Пользователь должен быть участником (для личного) или создателем (для группового).
    Удаляет чат, связанные сообщения и записи об участниках.
    """
    chat_id = validate_uuid(chat_id)
    chat = await Chat.get_or_404(id=chat_id, session=session)

    await is_user_in_chat(user, chat, session)

    if chat.is_group and not await user_is_admin_chat(user, chat, session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Только создатель может удалить групповой чат")

    await chat.delete(session=session)  # удаляются и сообщения чата
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/chat/{chat_id}/members/",
             response_model=ChatDTO)
async def router_add_member(
        chat_id: str,
        member_data: MemberAddDTO,
        user: User = Depends(get_current_user),
        session=Depends(get_db)
) -> ChatDTO:
    """
    Добавление пользователя в групповой чат. Только участники чата могут добавлять новых.
    """
    chat_id = validate_uuid(chat_id)
    user_id = validate_uuid(member_data.user_id)
    chat = await Chat.get_or_404(id=chat_id, session=session)
    if not chat.is_group:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Добавление участников возможно только в групповой чат")

    members = await is_user_in_chat(user, chat, session)

    new_member = await User.get_or_404(id=user_id, session=session)
    if new_member.id in [member.user_id for member in members]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь уже в чате")

    try:
        session.add(GroupMember(user_id=new_member.id, chat_id=chat.id))
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь уже в чате")
    return chat.to_dict()


@router.post("/chat/{chat_id}/members/",
             response_model=ChatDTO)
async def router_add_member(
        chat_id: str,
        member_data: MemberAddDTO,
        user: User = Depends(get_current_user),
        session=Depends(get_db)
) -> ChatDTO:
    """
    Добавление пользователя в групповой чат. Только участники чата могут добавлять новых.
    """
    chat_id = validate_uuid(chat_id)
    user_id = validate_uuid(member_data.user_id)
    chat = await Chat.get_or_404(id=chat_id, session=session)
    if not chat.is_group:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Добавление участников возможно только в групповой чат")

    members = await is_user_in_chat(user, chat, session)

    new_member = await User.get_or_404(id=user_id, session=session)
    if new_member in [member.user_id for member in members]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь уже в чате")

    session.add(GroupMember(user_id=new_member.id, chat_id=chat.id))
    await session.commit()
    return chat.to_dict()


@router.patch("/chat/{chat_id}/members/", response_model=List[dict[str, str]])
async def remove_chat_members(
    chat_id: str,
    members_data: MembersIdsDTO,
    user: User = Depends(get_current_user),
    session: AsyncSessionLocal = Depends(get_db)
) -> List[dict[str, str]]:
    """
    Удаление участников из группового чата.
    :param chat_id: ID чата
    :param members_data: DTO с ID пользователей для удаления
    :param user: Текущий пользователь (администратор)
    :param session: Сессия базы данных
    :return: Список удалённых участников в формате [{"id": ..., "user_id": ...}]
    """
    # Получаем чат или вызываем 404, если он не существует
    chat = await Chat.get_or_404(id=chat_id, session=session)

    # Проверяем, что это групповой чат
    if not chat.is_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить участников из личного чата"
        )

    # Не позволяем администратору удалить самого себя
    if str(user.id) in members_data.member_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Администратор не может удалить самого себя из чата"
        )

    # Проверяем, что все указанные пользователи существуют
    existing_users = await session.execute(
        select(User).where(User.id.in_(members_data.member_ids))
    )
    existing_users = existing_users.scalars().all()
    if len(existing_users) != len(members_data.member_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Один или несколько пользователей не найдены"
        )

    # Проверяем, что все указанные пользователи являются участниками чата
    chat_members = await session.execute(
        select(GroupMember).where(
            GroupMember.chat_id == chat_id,
            GroupMember.user_id.in_(members_data.member_ids)
        )
    )
    chat_members = chat_members.scalars().all()
    if len(chat_members) != len(members_data.member_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Один или несколько пользователей не являются участниками чата"
        )

    if not await user_is_admin_chat(user, chat, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор чата может удалять участников"
        )

    # Сохраняем данные удаляемых участников до удаления
    removed_members = [{"chat_id": str(m.chat_id), "user_id": str(m.user_id)} for m in chat_members]

    # Удаляем участников из чата
    await session.execute(
        delete(GroupMember).where(
            GroupMember.chat_id == chat_id,
            GroupMember.user_id.in_(members_data.member_ids)
        )
    )
    await session.commit()
    return removed_members


@router.post("/chat/{chat_id}/history/",
             response_model=MessageHistoryDTO)
async def router_history(
        chat_id: str,
        limit: int = 10,
        offset: int = 0,
        user: User = Depends(get_current_user),
        session=Depends(get_db)
) -> dict:
    chat_id = validate_uuid(chat_id)
    result = await session.execute(
        select(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.timestamp.asc())
        .offset(offset)
        .limit(limit)
    )
    messages = result.scalars().all()

    # Получаем общее количество сообщений
    count_result = await session.execute(
        select(func.count()).select_from(Message).filter(Message.chat_id == chat_id)
    )
    total = count_result.scalar_one()

    return {
        "messages": [message.to_dict() for message in messages],
        "total": total
    }


async def is_user_in_chat(user: User, chat: Chat, session) -> List[GroupMember]:
    members = await GroupMember.list(session=session, chat_id=chat.id)
    member_ids = [member.user_id for member in members]
    if user.id not in member_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не участник этого чата")
    return members


async def user_is_admin_chat(user: User, chat: Chat, session) -> bool:
    admins = await GroupMember.list(session=session, is_admin=True, chat_id=chat.id)
    return user.id in [a.user_id for a in admins]