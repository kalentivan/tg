import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import join, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from app.auth.auth import get_current_ws_user
from app.database import AsyncSessionLocal, get_db
from app.handlers.chat import read_message, send_message
from app.models.models import Chat, GroupMember, User
from app.services.websocket import connection_manager
from app.tools import validate_uuid
from core.types import ID

router = APIRouter()


@router.websocket("/ws/{chat_id}")
async def websocket_chat(
        websocket: WebSocket,
        chat_id: ID,
        user: User = Depends(get_current_ws_user),
        session: AsyncSession = Depends(get_db)
):
    chat_id = validate_uuid(chat_id)
    try:
        chat = await get_chat_with_membership_check(chat_id, user.id, session)
    except HTTPException:
        await websocket.close(code=1008)
        return

    await connection_manager.connect(websocket, chat_id, user.id)
    try:
        while True:
            data = await websocket.receive_json()
            print(str(data) + " ОК !!!!")
            match data.get("action"):
                case "send_message":
                    await send_message(websocket, session, user, data, chat)
                case "message_read":
                    await read_message(websocket, session, user, data, chat)

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, chat_id, user.id)
        print("WebSocketDisconnect!!!!")
    finally:
        await session.close()  # Явное закрытие сессии на случай прерывания


async def get_chat_with_membership_check(chat_id: uuid.UUID,
                                         user_id: uuid.UUID,
                                         session: AsyncSession) -> Chat:
    """
    Получает чат и проверяет, является ли пользователь участником, одним запросом.
    """
    stmt = (
        select(Chat)
        .select_from(join(Chat, GroupMember, Chat.id == GroupMember.chat_id))
        .where(Chat.id == chat_id)
        .where(GroupMember.user_id == user_id)
    )
    result = await session.execute(stmt)
    chat: Chat = result.scalars().first()

    if not chat:
        # Проверяем, существует ли чат вообще
        stmt_exists = select(Chat).where(Chat.id == chat_id)
        result_exists = await session.execute(stmt_exists)
        if not result_exists.scalars().first():
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Чат не найден")
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Вы не участник этого чата")
    return chat
