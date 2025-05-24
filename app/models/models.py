from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Uuid, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class User(Base):
    __tablename__ = "users"

    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

    messages = relationship("Message", back_populates="sender")
    chats = relationship("Chat", secondary="group_members", back_populates="members")

    @property
    def fields(self):
        return super().fields + ("email", "username")


class Chat(Base):
    __tablename__ = "chats"

    name = Column(String, nullable=True)
    is_group = Column(Boolean, default=False)
    admin_id = Column(Uuid, ForeignKey("users.id"), primary_key=True)

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    members = relationship("User", secondary="group_members", back_populates="chats")
    admin = relationship("User", foreign_keys=[admin_id])

    async def delete(self, session: AsyncSession = None):
        """
        Удаляет объект из базы данных.
        """
        await session.execute(delete(GroupMember).where(GroupMember.chat_id == self.id))
        await session.delete(self)
        await session.commit()

    @property
    def fields(self):
        return super().fields + ("name", "is_group", "admin_id")


class GroupMember(Base):
    __tablename__ = "group_members"

    user_id = Column(Uuid, ForeignKey("users.id"), primary_key=True)
    chat_id = Column(Uuid, ForeignKey("chats.id"), primary_key=True)

    @property
    def fields(self):
        return super().fields + ("user_id", "chat_id")


class Message(Base):
    __tablename__ = "messages"

    chat_id = Column(Uuid, ForeignKey("chats.id"))
    sender_id = Column(Uuid, ForeignKey("users.id"))
    text = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages")

    @property
    def fields(self):
        return super().fields + ("chat_id", "sender_id", "text", "timestamp", "is_read")


class MessageRead(Base):
    __tablename__ = "message_reads"

    message_id = Column(Uuid, ForeignKey("messages.id"), primary_key=True)
    user_id = Column(Uuid, ForeignKey("users.id"), primary_key=True)
    read_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="read_by")
    user = relationship("User")

    @property
    def fields(self):
        return super().fields + ("message_id", "user_id", "read_at")
    