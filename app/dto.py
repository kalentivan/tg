from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

from core.types import ID


class UserDTO(BaseModel):
    username: str | None
    email: str | None


class UserPwdDTO(UserDTO):
    password: str | None


class User(UserDTO):
    id: ID | None

    class Config:
        orm_mode = True


class ChatDTO(BaseModel):
    name: Optional[str] = None
    is_group: bool = False


class ChatIds(ChatDTO):
    member_ids: List[ID] = []  # Для групповых чатов


class Chat(ChatDTO):
    id: ID
    members: List[User] = []

    class Config:
        orm_mode = True


class MessageBase(BaseModel):
    text: str


class MessageCreate(MessageBase):
    chat_id: ID


class Message(MessageBase):
    id: ID
    chat_id: ID
    sender_id: ID
    timestamp: datetime
    is_read: bool

    class Config:
        orm_mode = True


class MessageHistory(BaseModel):
    messages: List[Message]
    total: int


class ChatCreateDTO(BaseModel):
    name: Optional[str] = None
    is_group: bool = False
    member_ids: List[ID] = []  # Список ID пользователей для группового чата


class MemberAddDTO(BaseModel):
    user_id: ID
