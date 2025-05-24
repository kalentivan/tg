from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import func, select

from app.auth.auth import get_current_user
from app.database import get_db
from app.models.models import Chat, Message, User, GroupMember
from app.dto import ChatCreateDTO, ChatDTO, MemberAddDTO
from core.types import ID

router = APIRouter(tags=["chat"])


@router.post("/chat/", response_model=ChatDTO)
async def create_chat(
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Групповой чат должен иметь название")

    # Проверяем, что все указанные пользователи существуют
    members = await User.by_ids(ids=chat_data.member_ids, session=session)
    if len(members) != len(chat_data.member_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Один или несколько пользователей не найдены")

    # Добавляем создателя в участники, если его нет
    if user not in members:
        members.append(user)  # Создатель всегда участник

    # Создаем чат
    chat = await Chat.create(name=chat_data.name, is_group=chat_data.is_group, admin_id=user.id, session=session)

    # Добавляем участников одним запросом
    group_members = [GroupMember(user_id=member.id, chat_id=chat.id) for member in members]
    session.add_all(group_members)
    await session.commit()
    return chat.to_dict()


@router.delete("/chat/{chat_id}/")
async def delete_chat(
        chat_id: int,
        user: User = Depends(get_current_user),
        session=Depends(get_db)
) -> Response:
    """
    Удаление чата. Пользователь должен быть участником (для личного) или создателем (для группового).
    Удаляет чат, связанные сообщения и записи об участниках.
    """
    chat = await Chat.get_or_404(id=chat_id, session=session)
    if user not in chat.members:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не участник этого чата")
    if chat.is_group and chat.admin_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Только создатель может удалить групповой чат")

    await chat.delete()  # удаляются и сообщения чата
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/chat/{chat_id}/members/",
             response_model=ChatDTO)
async def add_member(
        chat_id: int,
        member_data: MemberAddDTO,
        user: User = Depends(get_current_user),
        session=Depends(get_db)
) -> ChatDTO:
    """
    Добавление пользователя в групповой чат. Только участники чата могут добавлять новых.
    """
    chat = await Chat.get_or_404(id=chat_id, session=session)
    if not chat.is_group:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Добавление участников возможно только в групповой чат")

    if user not in chat.members:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не участник этого чата")

    new_member = await User.get_or_404(id=member_data.user_id, session=session)
    if new_member in chat.members:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь уже в чате")

    await GroupMember.create(user_id=new_member.id, chat_id=chat.id, session=session)
    return chat.to_dict()


@router.post("/chat/{chat_id}/history/",
             response_model=ChatDTO)
async def router_history(
        chat_id: ID,
        limit: int = 10,
        offset: int = 0,
        user: User = Depends(get_current_user),
        session=Depends(get_db)
) -> ChatDTO:
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

    return messages, total


