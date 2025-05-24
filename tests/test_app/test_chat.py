import uuid

import pytest
from fastapi import status

from app.auth.service import AuthService
from app.dto import ChatCreateDTO, MemberAddDTO
from app.models.models import Chat, GroupMember, Message
from app.tools import validate_uuid


@pytest.mark.asyncio
async def test_create_personal_chat(client, auth_headers, test_user, test_user2, db_session):
    chat_data = ChatCreateDTO(is_group=False, member_ids=[str(test_user2.id)])
    response = client.post("/chat/", json=dict(chat_data), headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_group"] is False
    assert data["admin_id"] == str(test_user.id)

    # Проверяем участников
    chat = await Chat.get_or_404(id=validate_uuid(data["id"]), session=db_session)
    members = await GroupMember.list(session=db_session, chat_id=chat.id)
    member_ids = [str(m.user_id) for m in members]
    assert str(test_user.id) in member_ids
    assert str(test_user2.id) in member_ids


@pytest.mark.asyncio
async def test_create_group_chat(client, auth_headers, test_user, test_user2, db_session):
    chat_data = ChatCreateDTO(name="Test Group", is_group=True, member_ids=[str(test_user2.id)])
    response = client.post("/chat/", json=chat_data.dict(), headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Group"
    assert data["is_group"] is True

    # Проверяем участников
    chat = await Chat.get_or_404(id=validate_uuid(data["id"]), session=db_session)
    members = await GroupMember.list(session=db_session, chat_id=chat.id)
    member_ids = [str(m.user_id) for m in members]
    assert str(test_user.id) in member_ids
    assert str(test_user2.id) in member_ids


@pytest.mark.asyncio
async def test_create_personal_chat_invalid_members(client, auth_headers):
    chat_data = ChatCreateDTO(is_group=False, member_ids=[str(uuid.uuid4())])
    response = client.post("/chat/", json=chat_data.dict(), headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "не найдены" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_group_chat_no_name(client, auth_headers, test_user2):
    chat_data = ChatCreateDTO(is_group=True, member_ids=[str(test_user2.id)])
    response = client.post("/chat/", json=chat_data.dict(), headers=auth_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "название" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_personal_chat(client, auth_headers, personal_chat, test_user, db_session):
    response = client.delete(f"/chat/{personal_chat.id}/", headers=auth_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    chat = await Chat.first(id=personal_chat.id, session=db_session)
    assert chat is None


@pytest.mark.asyncio
async def test_delete_group_chat_by_admin(client, auth_headers, group_chat, test_user, db_session):
    response = client.delete(f"/chat/{group_chat.id}/", headers=auth_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    chat = await Chat.first(id=group_chat.id, session=db_session)
    assert chat is None


@pytest.mark.asyncio
async def test_delete_group_chat_by_non_admin(client, group_chat, test_user2, db_session):
    auth_service = AuthService()
    token = auth_service._jwt_auth.generate_access_token(subject=str(test_user2.id))
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete(f"/chat/{group_chat.id}/", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "создатель" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_member_to_group_chat(client, auth_headers, group_chat, test_user2, db_session):
    member_data = MemberAddDTO(user_id=str(test_user2.id))
    response = client.post(f"/chat/{group_chat.id}/members/", json=member_data.dict(), headers=auth_headers)
    assert response.status_code == 200
    members = await GroupMember.list(session=db_session, chat_id=group_chat.id)
    member_ids = [str(m.user_id) for m in members]
    assert str(test_user2.id) in member_ids


@pytest.mark.asyncio
async def test_add_member_to_personal_chat(client, auth_headers, personal_chat, test_user2):
    member_data = MemberAddDTO(user_id=str(test_user2.id))
    response = client.post(f"/chat/{personal_chat.id}/members/", json=member_data.dict(), headers=auth_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "групповой чат" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_history(client, auth_headers, personal_chat, test_user, db_session):
    # Создаем тестовое сообщение
    await Message.create(
        chat_id=personal_chat.id,
        sender_id=test_user.id,
        text="Hello",
        session=db_session
    )
    response = client.post(f"/chat/{personal_chat.id}/history/", headers=auth_headers)
    assert response.status_code == 200
    answer = response.json()
    messages, total = answer["messages"], answer["total"]
    assert total == 1
    assert len(messages) == 1
    assert messages[0]["text"] == "Hello"
