import uuid

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from app.routes.chat import is_user_in_chat, user_is_admin_chat
from main import app  # твое приложение
from app.auth.service import AuthService
from app.dto import ChatCreateDTO, MemberAddDTO
from app.models.models import Chat, GroupMember, Message
from app.tools import validate_uuid


@pytest.mark.asyncio
async def test_create_personal_chat(test_user, test_user2, auth_headers, db_session):
    chat_data = ChatCreateDTO(is_group=False, member_ids=[str(test_user2.id)])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/chat/", json=chat_data.model_dump(), headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["is_group"] is False

    # Проверяем участников
    chat = await Chat.get_or_404(id=validate_uuid(data["id"]), session=db_session)
    members = await GroupMember.list(session=db_session, chat_id=chat.id)
    member_ids = [str(m.user_id) for m in members]
    assert str(test_user.id) in member_ids
    assert str(test_user2.id) in member_ids


@pytest.mark.asyncio
async def test_create_group_chat(client, auth_headers, test_user, test_user2, db_session):
    chat_data = ChatCreateDTO(name="Test Group", is_group=True, member_ids=[str(test_user2.id)])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/chat/", json=chat_data.model_dump(), headers=auth_headers)
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/chat/", json=chat_data.model_dump(), headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "не найдены" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_group_chat_no_name(client, auth_headers, test_user2):
    chat_data = ChatCreateDTO(is_group=True, member_ids=[str(test_user2.id)])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/chat/", json=chat_data.model_dump(), headers=auth_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "название" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_personal_chat(client, auth_headers, personal_chat, test_user, db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.delete(f"/chat/{personal_chat.id}/", headers=auth_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    chat = await Chat.first(id=personal_chat.id, session=db_session)
    assert chat is None


@pytest.mark.asyncio
async def test_delete_group_chat_by_admin(client, auth_headers, group_chat, test_user, db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.delete(f"/chat/{group_chat.id}/", headers=auth_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    chat = await Chat.first(id=group_chat.id, session=db_session)
    assert chat is None


@pytest.mark.asyncio
async def test_delete_group_chat_by_non_admin(client, group_chat, test_user2, db_session):
    auth_service = AuthService()
    token = auth_service._jwt_auth.generate_access_token(subject=str(test_user2.id))
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.delete(f"/chat/{group_chat.id}/", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "создатель" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_new_member_to_group_chat(client, auth_headers, group_chat, test_user, test_user3, db_session):
    """Проверяет успешное добавление нового пользователя в групповой чат."""
    # Убедимся, что test_user — участник чата
    user_id = str(test_user3.id)
    group_chat_id = str(group_chat.id)
    try:
        db_session.add(GroupMember(user_id=test_user.id, chat_id=group_chat.id))
        await db_session.commit()
    except IntegrityError as ex:
        await db_session.rollback()
    except Exception as ex:
        await db_session.rollback()
    # Добавляем test_user2 (нового пользователя)
    member_data = MemberAddDTO(user_id=user_id)
    transport = ASGITransport(app=app)
    cur_members = await GroupMember.list(session=db_session, chat_id=group_chat_id)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/chat/{group_chat_id}/members/",
            json=member_data.model_dump(),
            headers=auth_headers
        )
    assert response.status_code == 200
    members = await GroupMember.list(session=db_session, chat_id=group_chat_id)
    member_ids = [str(m.user_id) for m in members]
    assert user_id in member_ids
    assert len(members) == len(cur_members) + 1  # test_user и test_user2


@pytest.mark.asyncio
async def test_add_existing_member_to_group_chat(client, auth_headers, group_chat, test_user, test_user2, db_session):
    """Проверяет попытку добавления уже существующего пользователя в групповой чат."""
    # Убедимся, что test_user — участник чата
    user_1_id = str(test_user.id)
    user_2_id = str(test_user2.id)
    group_chat_id = str(group_chat.id)
    try:
        db_session.add(GroupMember(user_id=user_1_id, chat_id=group_chat.id))
        await db_session.commit()
    except IntegrityError as ex:
        await db_session.rollback()
    except Exception as ex:
        await db_session.rollback()
    # Добавляем test_user2 в чат
    try:
        db_session.add(GroupMember(user_id=user_2_id, chat_id=group_chat.id))
        await db_session.commit()
    except IntegrityError as ex:
        await db_session.rollback()
    except Exception as ex:
        await db_session.rollback()

    # Пытаемся добавить test_user2 ещё раз
    member_data = MemberAddDTO(user_id=user_2_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/chat/{group_chat_id}/members/",
            json=member_data.model_dump(),
            headers=auth_headers
        )
    assert response.status_code == 400
    assert "Пользователь уже в чате" in response.json()["detail"]
    members = await GroupMember.list(session=db_session, chat_id=group_chat_id)
    assert len(members) == 2  # Количество участников не изменилось


@pytest.mark.asyncio
async def test_add_member_to_personal_chat(client, auth_headers, personal_chat, test_user2):
    member_data = MemberAddDTO(user_id=str(test_user2.id))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(f"/chat/{personal_chat.id}/members/", json=member_data.model_dump(),
                                 headers=auth_headers)
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(f"/chat/{personal_chat.id}/history/", headers=auth_headers)
    assert response.status_code == 200
    answer = response.json()
    messages, total = answer["messages"], answer["total"]
    assert total == 1
    assert len(messages) == 1
    assert messages[0]["text"] == "Hello"


@pytest.mark.asyncio
async def test_remove_members_from_group_chat_success(
        client, auth_headers, group_chat, test_user, test_user2, db_session
):
    note = await GroupMember.first(chat_id=group_chat.id, user_id=test_user.id, session=db_session)
    note.is_admin = True
    db_session.add(note)
    await db_session.commit()

    member_ids = [str(test_user2.id)]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.patch(
            f"/chat/{group_chat.id}/members/",
            json={"member_ids": member_ids},
            headers=auth_headers
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == str(test_user2.id)

    members = await GroupMember.list(session=db_session, chat_id=group_chat.id)
    assert len(members) == 1  # Остался только админ
    assert str(test_user.id) in [str(m.user_id) for m in members]


@pytest.mark.asyncio
async def test_remove_members_from_personal_chat(
        client, auth_headers, personal_chat, test_user, test_user2
):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.patch(
            f"/chat/{personal_chat.id}/members/",
            json={"member_ids": [str(test_user2.id)]},
            headers=auth_headers
        )
    assert response.status_code == 400
    assert "Нельзя удалить участников из личного чата" in response.json()["detail"]


@pytest.mark.asyncio
async def test_remove_members_by_non_admin(
        client, group_chat, test_user, test_user2, db_session
):
    auth_service = AuthService()
    token = auth_service._jwt_auth.generate_access_token(subject=str(test_user2.id))
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.patch(
            f"/chat/{group_chat.id}/members/",
            json={"member_ids": [str(test_user.id)]},
            headers=headers
        )
    assert response.status_code == 403
    assert "Только администратор чата может удалять участников" in response.json()["detail"]


@pytest.mark.asyncio
async def test_remove_nonexistent_member(
        client, auth_headers, group_chat, test_user, db_session
):
    nonexistent_user_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.patch(
            f"/chat/{group_chat.id}/members/",
            json={"member_ids": [nonexistent_user_id]},
            headers=auth_headers
        )
    assert response.status_code == 404
    assert "не найдены" in response.json()["detail"]


@pytest.mark.asyncio
async def test_remove_admin_self(
        client, auth_headers, group_chat, test_user, db_session
):
    note = await GroupMember.first(chat_id=group_chat.id, user_id=test_user.id, session=db_session)
    note.is_admin = True
    db_session.add(note)
    db_session.add(group_chat)
    await db_session.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.patch(
            f"/chat/{group_chat.id}/members/",
            json={"member_ids": [str(test_user.id)]},
            headers=auth_headers
        )
    assert response.status_code == 400
    assert "Администратор не может удалить самого себя" in response.json()["detail"]


@pytest.mark.asyncio
async def test_is_user_in_chat_success_group_chat(db_session, test_user, group_chat):
    # Проверяем, что test_user (участник и админ) находится в групповом чате
    members = await is_user_in_chat(test_user, group_chat, db_session)
    assert len(members) == 2  # Два участника: test_user и test_user2
    assert test_user.id in [member.user_id for member in members]
    assert all(isinstance(member, GroupMember) for member in members)


@pytest.mark.asyncio
async def test_is_user_in_chat_success_personal_chat(db_session, test_user, personal_chat):
    # Проверяем, что test_user (участник) находится в личном чате
    members = await is_user_in_chat(test_user, personal_chat, db_session)
    assert len(members) == 2  # Два участника: test_user и test_user2
    assert test_user.id in [member.user_id for member in members]
    assert all(isinstance(member, GroupMember) for member in members)


@pytest.mark.asyncio
async def test_is_user_in_chat_not_member(db_session, test_user3, group_chat):
    # Проверяем, что test_user3 (не участник) не находится в групповом чате
    with pytest.raises(HTTPException) as exc_info:
        await is_user_in_chat(test_user3, group_chat, db_session)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Вы не участник этого чата"


@pytest.mark.asyncio
async def test_is_user_in_chat_chat_not_found(db_session, test_user):
    # Создаём "несуществующий" чат с невалидным ID
    from app.tools import validate_uuid
    chat = Chat(id=validate_uuid("00000000-0000-0000-0000-000000000000"), name="Non-existent", is_group=True)
    with pytest.raises(HTTPException) as exc_info:
        await is_user_in_chat(test_user, chat, db_session)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_user_is_admin_chat_admin_group_chat(db_session, test_user, group_chat):
    # Проверяем, что test_user (админ) возвращает True в групповом чате
    is_admin = await user_is_admin_chat(test_user, group_chat, db_session)
    assert is_admin is True


@pytest.mark.asyncio
async def test_user_is_admin_chat_not_admin_group_chat(db_session, test_user2, group_chat):
    # Проверяем, что test_user2 (не админ) возвращает False в групповом чате
    is_admin = await user_is_admin_chat(test_user2, group_chat, db_session)
    assert is_admin is False


@pytest.mark.asyncio
async def test_user_is_admin_chat_admin_personal_chat(db_session, test_user, personal_chat):
    # Проверяем, что test_user (админ) возвращает True в личном чате
    is_admin = await user_is_admin_chat(test_user, personal_chat, db_session)
    assert is_admin is True


@pytest.mark.asyncio
async def test_user_is_admin_chat_not_admin_personal_chat(db_session, test_user2, personal_chat):
    # Проверяем, что test_user2 (не админ) возвращает False в личном чате
    is_admin = await user_is_admin_chat(test_user2, personal_chat, db_session)
    assert is_admin is False


@pytest.mark.asyncio
async def test_user_is_admin_chat_not_member(db_session, test_user3, group_chat):
    # Проверяем, что test_user3 (не участник) возвращает False
    is_admin = await user_is_admin_chat(test_user3, group_chat, db_session)
    assert is_admin is False


@pytest.mark.asyncio
async def test_user_is_admin_chat_chat_not_found(db_session, test_user):
    # Создаём "несуществующий" чат с невалидным ID
    from app.tools import validate_uuid
    chat = Chat(id=validate_uuid("00000000-0000-0000-0000-000000000000"), name="Non-existent", is_group=True)
    is_admin = await user_is_admin_chat(test_user, chat, db_session)
    assert is_admin is False


@pytest.mark.asyncio
async def test_is_user_in_chat_with_test_data(db_session, test_data):
    # Выбираем случайный групповой чат
    group_chat = test_data["group_chats"][0]
    # Получаем участников чата
    members = await GroupMember.list(session=db_session, chat_id=group_chat.id)
    member_ids = [member.user_id for member in members]
    # Выбираем первого участника
    member = next(user for user in test_data["users"] if user.id == member_ids[0])
    # Проверяем, что участник находится в чате
    chat_members = await is_user_in_chat(member, group_chat, db_session)
    assert len(chat_members) == test_data["group_chat_members"][group_chat.id]
    assert member.id in [m.user_id for m in chat_members]


@pytest.mark.asyncio
async def test_user_is_admin_chat_with_test_data(db_session, test_data):
    # Выбираем случайный групповой чат
    group_chat = test_data["group_chats"][0]
    # Получаем участников чата
    members = await GroupMember.list(session=db_session, chat_id=group_chat.id)
    # Находим админа
    admin = next(member for member in members if member.is_admin)
    admin_user = next(user for user in test_data["users"] if user.id == admin.user_id)
    # Проверяем, что админ возвращает True
    is_admin = await user_is_admin_chat(admin_user, group_chat, db_session)
    assert is_admin is True

    # Находим не-админа
    non_admin = next(member for member in members if not member.is_admin)
    non_admin_user = next(user for user in test_data["users"] if user.id == non_admin.user_id)
    # Проверяем, что не-админ возвращает False
    is_admin = await user_is_admin_chat(non_admin_user, group_chat, db_session)
    assert is_admin is False
