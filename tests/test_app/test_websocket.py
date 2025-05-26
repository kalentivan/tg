import uuid
import asyncio
import pytest
import uvicorn
from aiohttp import ClientSession, WSMsgType
from multiprocessing import Process
from time import sleep

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from app.auth.service import AuthService
from app.dto import UserPwdDTO
from app.models.models import Message, MessageRead, User, Chat, GroupMember
from app.database import AsyncSessionLocal


# Хелпер для запуска uvicorn в фоне
def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def start_server(event_loop):
    proc = Process(target=run_server, daemon=True)
    proc.start()
    await wait_load_db()  # Подождать пока поднимется сервер
    await asyncio.sleep(10)
    yield
    proc.terminate()


async def wait_load_db():
    # Ждём и проверяем подключение к базе данных
    max_attempts = 10
    attempt = 0
    session_ready = False
    tables = ["users", "messages", "group_members", "chats", "tokens", "message_reads"]
    while attempt < max_attempts and not session_ready:
        try:
            async with AsyncSessionLocal() as session:
                # Проверяем наличие таблиц
                for table in tables:
                    await session.execute(text(f"SELECT 1 FROM information_schema.tables WHERE table_name = '{table}'"))
                session_ready = True
        except (ConnectionError, ProgrammingError):
            attempt += 1
            await asyncio.sleep(1)

    if not session_ready:
        raise RuntimeError("Не удалось подключиться к базе данных или создать таблицы в течение 10 секунд")


@pytest.fixture
async def ws_db_session(start_server):
    async with AsyncSessionLocal() as session:
        yield session
        await session.close()


@pytest.fixture
async def ws_test_user(ws_db_session):
    if user := await User.first(email="test@example.com", session=ws_db_session):
        return user
    user_data = UserPwdDTO(
        username="testuser",
        email="test@example.com",
        password="test123"
    )
    auth_service = AuthService()
    user, tokens = await auth_service.register(user_data, session=ws_db_session)
    return user


@pytest.fixture
async def ws_test_user2(ws_db_session):
    if user := await User.first(email="test2@example.com", session=ws_db_session):
        return user
    user_data = UserPwdDTO(
        username="testuser2",
        email="test2@example.com",
        password="test123"
    )
    auth_service = AuthService()
    user, tokens = await auth_service.register(user_data, session=ws_db_session)
    await ws_db_session.refresh(user)
    return user


@pytest.fixture
async def ws_group_chat(ws_db_session, ws_test_user, ws_test_user2):
    if not (chat := await Chat.first(name="Test Group", session=ws_db_session)):
        chat = Chat(
            name="Test Group",
            is_group=True,
        )
    chat.is_group = True
    ws_db_session.add(chat)
    await ws_db_session.commit()
    await ws_db_session.refresh(chat)

    ws_db_session.add(GroupMember(user_id=ws_test_user.id, chat_id=chat.id, is_admin=True))
    ws_db_session.add(GroupMember(user_id=ws_test_user2.id, chat_id=chat.id, is_admin=False))
    await ws_db_session.commit()
    return chat


@pytest.fixture
async def ws_personal_chat(ws_db_session, ws_test_user, ws_test_user2):
    chat = await Chat.create(
        name=None,
        is_group=False,
        session=ws_db_session
    )
    ws_db_session.add(GroupMember(user_id=ws_test_user.id, chat_id=chat.id, is_admin=True))
    ws_db_session.add(GroupMember(user_id=ws_test_user2.id, chat_id=chat.id))
    await ws_db_session.commit()
    return chat


@pytest.mark.asyncio
async def test_websocket_connect(start_server, ws_db_session, ws_test_user, ws_personal_chat):
    # Генерируем токен
    auth_service = AuthService()
    payload = {"device_id": str(uuid.uuid4())}
    token = auth_service._jwt_auth.generate_access_token(subject=str(ws_test_user.id), payload=payload)
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Тестируем подключение к WebSocket
    uri = f"ws://127.0.0.1:8000/ws/{ws_personal_chat.id}"
    async with ClientSession() as session:
        async with session.ws_connect(uri, headers=auth_headers) as websocket:
            assert websocket.closed is False  # Проверяем, что соединение установлено
            await websocket.close()


@pytest.fixture
async def ws_auth_headers(ws_test_user):
    auth_service = AuthService()
    payload = {"device_id": str(uuid.uuid4())}
    token = auth_service._jwt_auth.generate_access_token(subject=str(ws_test_user.id), payload=payload)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_websocket_connect_disconnect(start_server, ws_db_session, ws_auth_headers, ws_personal_chat, ws_test_user):
    # Тестируем подключение к WebSocket
    uri = f"ws://127.0.0.1:8000/ws/{ws_personal_chat.id}"
    try:
        async with ClientSession() as session:
            async with session.ws_connect(uri, headers=ws_auth_headers) as websocket:
                pass  # Просто проверяем подключение
    except ConnectionError as e:
        # Ожидаемое закрытие из-за политики (например, если пользователь не авторизован)
        assert str(e).find("1008") != -1  # Код 1008 обычно указывает на политику
    finally:
        await asyncio.sleep(0.1)  # Даём время на закрытие


@pytest.mark.asyncio
async def test_websocket_send_message(start_server, ws_db_session, ws_auth_headers, ws_personal_chat, ws_test_user):
    # Тестируем отправку сообщения
    uri = f"ws://127.0.0.1:8000/ws/{ws_personal_chat.id}"
    async with ClientSession() as session:
        async with session.ws_connect(uri, headers=ws_auth_headers) as websocket:
            message_uuid = uuid.uuid4()
            await websocket.send_json({
                "action": "send_message",
                "text": "Test message",
                "uuid": str(message_uuid)
            })
            # Ждём ответа
            async for msg in websocket:
                if msg.type == WSMsgType.TEXT:
                    response = msg.json()
                    assert response["text"] == "Test message"
                    break
            # Проверяем сообщение в базе

            message = await Message.first(id=message_uuid, session=ws_db_session)
            assert message is not None
            assert message.text == "Test message"
            await websocket.close()


