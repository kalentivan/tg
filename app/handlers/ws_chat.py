import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from starlette import status

from app.models.models import Chat, GroupMember, Message, MessageRead, User
from app.services.websocket import connection_manager as cm
from app.tools import validate_uuid

logger = logging.getLogger(__name__)


async def send_message(websocket, session, user: User, data: dict, chat: Chat):
    message_text = data.get("text")
    message_uuid = validate_uuid(data.get("message_id"))
    if not message_text or not message_uuid:
        await cm.send_message({"error": "🛑 Требуются поля text и uuid"}, recipient_id=user.id)
        return
    try:
        message = Message(
            id=message_uuid,
            chat_id=chat.id,
            sender_id=user.id,
            text=message_text,
            timestamp=datetime.now(UTC),
            is_read=False
        )
        session.add(message)
        await session.commit()  # Явно фиксируем изменения
        logger.info(f"✅✅ {message.id=} SAVE")
    except HTTPException as e:
        logger.error(f"HTTPException {e=}")
        if e.status_code == status.HTTP_409_CONFLICT:
            await cm.send_message({"error": "Сообщение уже существует", "message_id": data.get("message_id")}, recipient_id=user.id)
            return
        raise
    except Exception as e:
        logger.error(f"🛑 Exception {e=}")
        await session.rollback()  # Откат при других ошибках
        raise
    try:
        logger.info(f"▶️▶️ {message.id=} Отправляем")
        data = message.to_dict()
        del data["id"]
        data["message_id"] = str(message.id)
        await cm.send_message(data, chat.id)
        logger.info(f"✅✅ {message.id=} Отправлено!")
    except Exception as e:
        logger.error(f"🛑 connection_manager {e=}")
        await session.rollback()  # Откат, если отправка провалилась
        raise


async def read_message(websocket, session, user: User, data: dict, chat: Chat) -> bool | None:
    message_id = validate_uuid(data.get("message_id"))
    if not message_id:
        await cm.send_message({"error": "Требуется поле message_id", "message_id": data.get("message_id")}, chat.id, recipient_id=user.id)
        return False
    try:
        message = await Message.first(id=message_id, session=session)
        if not message:
            await cm.send_message({"error": "Сообщение не найдено", "message_id": data.get("message_id")}, chat.id)
            return False
        if message.chat_id != chat.id:
            await cm.send_message({"error": "Сообщение не принадлежит этому чату", "message_id": data.get("message_id")})
            return False
        if not chat.is_group:
            return await read_in_person_chat(session, user, message, chat.id)
        return await read_in_group_chat(session, user, message, chat)
    except HTTPException as ex:
        logger.error(f"🛑 read_message {ex=}")
        return False
    except Exception as ex:
        logger.error(f"🛑 read_message {ex=}")
        return False


async def read_in_person_chat(session, user: User, message: Message, chat_id: UUID):
    if message.sender_id != user.id and not message.is_read:
        message.is_read = True
        try:
            await message.save(session=session, update_fields=["is_read"])
            await session.commit()
        except Exception as e:
            logger.error(f"🛑 read_in_person_chat save {e=}")
            await session.rollback()
            raise

        try:
            await cm.send_message(
                {
                    "action": "message_read",
                    "message_id": str(message.id),
                    "chat_id": str(chat_id),
                    "read_by_user_id": str(user.id)
                },
                chat_id
            )
        except Exception as e:
            logger.error(f"🛑 read_in_person_chat {e=}")
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
            obj = MessageRead(
                message_id=message.id,
                user_id=user.id
            )
            session.add(obj)
            await session.commit()
        except Exception as e:
            logger.error(f"🛑 read_in_group_chat save {e=}")
            await session.rollback()
            raise

        try:
            read_count = await session.scalar(
                select(func.count()).select_from(MessageRead).where(MessageRead.message_id == message.id)
            )
            members = await GroupMember.list(chat_id=chat.id, session=session)
            member_count = len([m for m in members if m.user_id != message.sender_id])
            if read_count >= member_count:
                await cm.send_message(
                    {
                        "action": "message_read",
                        "message_id": str(message.id),
                        "chat_id": str(chat.id),
                        "read_by_all": True
                    },
                    chat.id
                )
            else:
                logger.error(f"🛑 read_count < member_count")
        except Exception as e:
            logger.error(f"🛑 read_in_person_chat save {e=}")
            await session.rollback()
            raise
