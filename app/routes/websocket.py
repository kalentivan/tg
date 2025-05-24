from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect

from app.auth.auth import get_current_ws_user
from app.handlers.chat import read_message, send_message
from app.models.models import User, Chat
from app.services.websocket import connection_manager
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

from core.types import ID

router = APIRouter()


@router.websocket("/ws/{chat_id}")
async def websocket_chat(
        websocket: WebSocket,
        chat_id: ID,
        user: User = Depends(get_current_ws_user),
        session: AsyncSession = Depends(get_db)
):
    # Проверяем, что пользователь имеет доступ к чату
    chat = await Chat.get_or_404(id=chat_id, session=session)
    if user not in chat.members:
        await websocket.close(code=1008)  # Policy violation
        return

    await connection_manager.connect(websocket, chat_id, user.id)
    try:
        while True:
            data = await websocket.receive_json()
            match data.get("action"):
                case "send_message": await send_message(websocket, session, user, data, chat)
                case "message_read": await read_message(websocket, session, user, data, chat)

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, chat_id, user.id)


