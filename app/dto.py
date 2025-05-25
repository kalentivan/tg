from typing import List, Optional

from pydantic import BaseModel

from core.types import ID


class UserDTO(BaseModel):
    username: str | None
    email: str | None


class UserPwdDTO(UserDTO):
    password: str | None


class ChatDTO(BaseModel):
    id: str = ""
    name: Optional[str] = None
    is_group: bool = False
    admin_id: str = ""


class ChatIdsDTO(ChatDTO):
    member_ids: List[ID] = []  # Для групповых чатов


class ChatIdMems(ChatDTO):
    id: ID
    members: List[UserDTO] = []

    class Config:
        orm_mode = True


class MessageDTO(BaseModel):
    text: str


class MessageChIdDTO(MessageDTO):
    chat_id: ID


class MessageDTO(MessageChIdDTO):
    id: ID
    sender_id: ID
    timestamp_str: str
    is_read: bool

    class Config:
        orm_mode = True


class MessageHistoryDTO(BaseModel):
    messages: List[MessageDTO]
    total: int


class ChatCreateDTO(BaseModel):
    name: Optional[str] = None
    is_group: bool = False
    member_ids: List[ID] = []  # Список ID пользователей для группового чата


class MemberAddDTO(BaseModel):
    user_id: ID


class TokensDTO(BaseModel):
    user_id: ID = 0
    role: str = ""
    access_token: str = ""
    refresh_token: str | None = ""
    access_ttl: int = 0
    refresh_ttl: int = 0

