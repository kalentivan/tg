from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class UserDTO(BaseModel):
    username: str | None = ""
    email: str | None = ""


class UserPwdDTO(UserDTO):
    password: str | None = ""


class ChatDTO(BaseModel):
    id: str = ""
    name: Optional[str] = None
    is_group: bool = False
    admin_id: str = ""


class MessageDTO(BaseModel):
    id: str
    sender_id: str
    timestamp_str: str
    is_read: bool
    chat_id: str
    text: str
    model_config = ConfigDict(from_attributes=True)  # Замените orm_mode на from_attributes


class MessageHistoryDTO(BaseModel):
    messages: List[MessageDTO]
    total: int


class ChatCreateDTO(BaseModel):
    name: Optional[str] = None
    is_group: bool = False
    member_ids: List[str] = None  # Список ID пользователей для группового чата


class MemberAddDTO(BaseModel):
    user_id: str


class MembersIdsDTO(BaseModel):
    member_ids: List[str] = None  # Список ID пользователей для группового чата


class TokensDTO(BaseModel):
    user_id: str = 0
    role: str = ""
    access_token: str = ""
    refresh_token: str | None = ""
    access_ttl: int = 0
    refresh_ttl: int = 0


class RTokenDTO(BaseModel):
    refresh_token: str | None = ""


