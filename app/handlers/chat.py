from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from starlette import status

from app.models.models import Message, MessageRead
from app.services.websocket import connection_manager


async def send_message(websocket, session, user, data: dict, chat):
    message_text = data.get("text")
    message_uuid = data.get("uuid")
    if not message_text or not message_uuid:
        await websocket.send_json({"error": "Требуются поля text и uuid"})
        return
        # Сохраняем сообщение в БД
    try:
        message = await Message.create(
            id=message_uuid,
            chat_id=chat.id,
            sender_id=user.id,
            text=message_text,
            timestamp=datetime.utcnow(),
            is_read=False,
            session=session
        )
    except HTTPException as e:
        if e.status_code == status.HTTP_409_CONFLICT:
            await websocket.send_json({"error": "Сообщение уже существует"})
            return
        raise
    # Отправляем сообщение всем участникам чата
    await connection_manager.send_message(message.to_dict(), chat.id)


async def read_message(websocket, session, user, data, chat):
    message_id = data.get("message_id")
    if not message_id:
        await websocket.send_json({"error": "Требуется поле message_id"})
        return None

        # Проверяем существование сообщения
    message = await Message.get_or_404(id=message_id, session=session)
    if message.chat_id != chat.id:
        await websocket.send_json({"error": "Сообщение не принадлежит этому чату"})
        return None

    if not chat.is_group:
        return await read_in_person_chat(session, user, message, chat.id)
    return await read_in_group_chat(session, user, message, chat.id, chat)


async def read_in_person_chat(session, user, message, chat_id):
    # Личный чат: обновляем is_read
    if message.sender_id != user.id and not message.is_read:
        message.is_read = True
        await message.save(session=session)
        # Уведомляем отправителя
        await connection_manager.send_message(
            {
                "action": "message_read",
                "message_id": str(message.id),
                "chat_id": str(chat_id),
                "read_by_user_id": str(user.id)
            },
            chat_id,
            recipient_id=message.sender_id
        )


async def read_in_group_chat(session, user, message, chat_id, chat):
    # Групповой чат: добавляем запись в MessageRead
    existing_read = await MessageRead.first(
        session=session,
        message_id=message.id,
        user_id=user.id
    )
    if not existing_read and message.sender_id != user.id:
        await MessageRead.create(
            session=session,
            message_id=message.id,
            user_id=user.id
        )
        # Проверяем, все ли участники (кроме отправителя) прочитали
        read_count = await session.scalar(
            select(MessageRead).where(MessageRead.message_id == message.id).count()
        )
        member_count = len([m for m in chat.members if m.id != message.sender_id])
        if read_count >= member_count:
            # Уведомляем отправителя
            await connection_manager.send_message(
                {
                    "action": "message_read",
                    "message_id": str(message.id),
                    "chat_id": str(chat_id),
                    "read_by_all": True
                },
                chat_id,
                recipient_id=message.sender_id
            )
