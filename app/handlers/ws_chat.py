from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from starlette import status

from app.models.models import Chat, GroupMember, Message, MessageRead, User
from app.services.websocket import connection_manager
from app.tools import validate_uuid


async def send_message(websocket, session, user: User, data: dict, chat: Chat):
    message_text = data.get("text")
    message_uuid = validate_uuid(data.get("uuid"))
    if not message_text or not message_uuid:
        await websocket.send_json({"error": "Требуются поля text и uuid"})
        return

    try:
        message = await Message.create(
            id=message_uuid,
            chat_id=chat.id,
            sender_id=user.id,
            text=message_text,
            timestamp=datetime.now(UTC),
            is_read=False,
            session=session
        )
        await session.commit()  # Явно фиксируем изменения
    except HTTPException as e:
        print(f"HTTPException {e=}")
        if e.status_code == status.HTTP_409_CONFLICT:
            await websocket.send_json({"error": "Сообщение уже существует"})
            return
        raise
    except Exception as e:
        print(f"Exception {e=}")
        await session.rollback()  # Откат при других ошибках
        raise
    try:
        await connection_manager.send_message(message.to_dict(), chat.id)
    except Exception as e:
        print(f"connection_manager {e=}")
        await session.rollback()  # Откат, если отправка провалилась
        raise


async def read_message(websocket, session, user: User, data: dict, chat: Chat) -> bool | None:
    message_id = validate_uuid(data.get("message_id"))
    if not message_id:
        await websocket.send_json({"error": "Требуется поле message_id"})
        return False
    try:
        message = await Message.get_or_404(id=message_id, session=session)
        if message.chat_id != chat.id:
            await websocket.send_json({"error": "Сообщение не принадлежит этому чату"})
            return False
        if not chat.is_group:
            return await read_in_person_chat(session, user, message, chat.id)
        return await read_in_group_chat(session, user, message, chat)
    except HTTPException:
        return False


async def read_in_person_chat(session, user: User, message: Message, chat_id: UUID):
    if message.sender_id != user.id and not message.is_read:
        message.is_read = True
        try:
            await message.save(session=session, update_fields=["is_read"])
            await session.commit()
        except Exception as e:
            print(f"read_in_person_chat save {e=}")
            await session.rollback()
            raise

        try:
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
        except Exception as e:
            await session.rollback()
            raise


async def read_in_group_chat(session, user: User, message: Message, chat: Chat):
    existing_read = await MessageRead.first(
        session=session,
        message_id=message.id,
        user_id=user.id
    )
    if not existing_read and message.sender_id != user.id:
        try:
            await MessageRead.create(
                session=session,
                message_id=message.id,
                user_id=user.id
            )
            await session.commit()
        except Exception as e:
            print(f"read_in_group_chat save {e=}")
            await session.rollback()
            raise

        try:
            read_count = await session.scalar(
                select(func.count(MessageRead.id)).where(MessageRead.message_id == message.id)
            )
            members = await GroupMember.list(chat_id=chat.id, session=session)
            member_count = len([m for m in members if m.id != message.sender_id])
            if read_count >= member_count:
                await connection_manager.send_message(
                    {
                        "action": "message_read",
                        "message_id": str(message.id),
                        "chat_id": str(chat.id),
                        "read_by_all": True
                    },
                    chat.id,
                    recipient_id=message.sender_id
                )
        except Exception as e:
            await session.rollback()
            raise
