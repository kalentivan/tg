from datetime import UTC, datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Uuid, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from .base import Base, BaseId


class User(BaseId):
    __tablename__ = "users"

    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    is_admin = Column(Boolean, default=False)
    password = Column(String)

    messages = relationship("Message", back_populates="sender")
    chats = relationship("Chat", secondary="group_members", back_populates="members")

    @property
    def role(self):
        return "client" if not self.is_admin else "admin"

    @property
    def fields(self):
        return super().fields + ("email", "username")


class IssuedJWTToken(Base):
    """Таблица с выпущенными токенами"""
    __tablename__ = "tokens"

    jti = Column(Uuid, primary_key=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String, nullable=False)  # для авторизации с нескольких устройств надо хранить ID устройства
    revoked = Column(Boolean, default=False)
    expired_time = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC) + timedelta(hours=1))

    @property
    def fields(self):
        return super().fields + ("jti", "user_id", "device_id", "revoked", "expired_time")


class Chat(BaseId):
    __tablename__ = "chats"

    name = Column(String, nullable=True)
    is_group = Column(Boolean, default=False)

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    members = relationship("User", secondary="group_members", back_populates="chats")

    async def delete(self, session: AsyncSession = None):
        """
        Удаляет объект из базы данных.
        """
        await session.execute(delete(GroupMember).where(GroupMember.chat_id == self.id))
        await session.delete(self)
        await session.commit()

    @property
    def fields(self):
        return super().fields + ("name", "is_group")


class GroupMember(Base):
    __tablename__ = "group_members"

    user_id = Column(Uuid, ForeignKey("users.id"), primary_key=True)
    chat_id = Column(Uuid, ForeignKey("chats.id"), primary_key=True)
    is_admin = Column(Boolean, default=False)

    @property
    def fields(self):
        return super().fields + ("user_id", "chat_id", "is_admin")


class Message(BaseId):
    __tablename__ = "messages"

    chat_id = Column(Uuid, ForeignKey("chats.id"))
    sender_id = Column(Uuid, ForeignKey("users.id"))
    text = Column(Text)
    timestamp = Column(DateTime(timezone=True), default=datetime.now(UTC))
    is_read = Column(Boolean, default=False)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages")
    read_by = relationship("MessageRead", back_populates="message", cascade="all, delete-orphan")

    @property
    def timestamp_str(self) -> str:
        """
        Вернуть дату в формате dd.mm.yyyy hh:mm
        :return: Отформатированная строка даты
        """
        if self.timestamp is None:
            return "N/A"
        return self.timestamp.strftime("%d.%m.%Y %H:%M")

    @property
    def fields(self):
        return super().fields + ("chat_id", "sender_id", "text", "timestamp_str", "is_read")


class MessageRead(Base):
    __tablename__ = "message_reads"

    message_id = Column(Uuid, ForeignKey("messages.id"), primary_key=True)
    user_id = Column(Uuid, ForeignKey("users.id"), primary_key=True)
    read_at = Column(DateTime(timezone=True), default=datetime.now(UTC))

    message = relationship("Message", back_populates="read_by")
    user = relationship("User")

    @property
    def read_at_str(self) -> str:
        """
        Вернуть дату в формате dd.mm.yyyy hh:mm
        :return: Отформатированная строка даты
        """
        if self.read_at is None:
            return "N/A"
        return self.read_at.strftime("%d.%m.%Y %H:%M")

    @property
    def fields(self):
        return super().fields + ("message_id", "user_id", "read_at_str")

