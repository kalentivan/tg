import asyncio
import logging
import os
from multiprocessing import Process
from uuid import uuid4

import pytest
import uvicorn
from aiohttp import ClientSession, WSMsgType
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.service import AuthService
from app.database import get_db
from app.dto import UserPwdDTO
from app.models.models import Chat, GroupMember, MessageRead, User
from app.models.models import Message
from main import app

logger = logging.getLogger(__name__)


def run_server():
    os.environ["TESTING"] = "true"
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    os.environ["TESTING"] = "false"


# Для тестирования веб-сокетов создаем новый движок, так как при использованит прошлого возникают конфликты even-loop
USER = os.getenv("TG_DB_USER")
PWD = os.getenv("TG_DB_PASSWORD")
HOST = os.getenv("TG_DB_HOST")
PORT = os.getenv("TG_DB_PORT")
TEST_HOST = "127.0.0.1:8000"
BD_NAME = os.getenv("TG_DB_TEST_NAME")
TEST_DATABASE_URL = f"postgresql+asyncpg://{USER}:{PWD}@{HOST}:{PORT}/{BD_NAME}"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest.fixture(scope="function")
async def db_session_factory():
    AsyncSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    yield AsyncSessionLocal
    await test_engine.dispose()  # Очищаем движок после тестов


@pytest.fixture(scope="function")
async def start_server(db_session_factory):
    proc = Process(target=run_server, daemon=True)
    proc.start()
    await wait_load_db(db_session_factory)  # Подождать пока поднимется сервер
    await asyncio.sleep(10)  # надо еще подождать, иначе падает, так как не находит таблицы
    yield
    proc.terminate()


async def wait_load_db(db_session_factory):
    max_attempts = 10
    attempt = 0
    session_ready = False
    tables = ["users", "messages", "group_members", "chats", "tokens", "message_reads"]
    while attempt < max_attempts and not session_ready:
        try:
            async with db_session_factory() as session:
                for table in tables:
                    await session.execute(text(f"SELECT 1 FROM information_schema.tables WHERE table_name = '{table}'"))
                session_ready = True
        except (ConnectionError, ProgrammingError):
            attempt += 1
            await asyncio.sleep(1)

    if not session_ready:
        raise RuntimeError("Не удалось подключиться к базе данных или создать таблицы в течение 10 секунд")


@pytest.fixture
async def ws_db_session(start_server, db_session_factory):
    async with db_session_factory() as session:
        yield session
        # Очистка данных после теста
        await wait_load_db(db_session_factory)
        await asyncio.sleep(0.5)
        for table in ["message_reads", "messages", "group_members", "chats", "users", "tokens"]:
            await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        await session.commit()
        await session.close()


# Переопределяем зависимость get_db для тестов
async def override_get_db(db_session_factory):
    async with db_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
def override_dependency(db_session_factory):
    app.dependency_overrides[get_db] = lambda: override_get_db(db_session_factory)
    yield
    app.dependency_overrides.clear()


# переопределяем фикстуры, чтобы они были зависимы от ws_db_session(start_server)
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

    if not await GroupMember.first(user_id=ws_test_user.id, chat_id=chat.id, session=ws_db_session):
        ws_db_session.add(GroupMember(user_id=ws_test_user.id, chat_id=chat.id, is_admin=True))
    if not await GroupMember.first(user_id=ws_test_user2.id, chat_id=chat.id, session=ws_db_session):
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


@pytest.fixture
async def ws_auth_headers(ws_test_user):
    auth_service = AuthService()
    payload = {"device_id": str(uuid4())}
    token = auth_service._jwt_auth.generate_access_token(subject=str(ws_test_user.id), payload=payload)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_websocket_connect(start_server, ws_db_session, ws_test_user, ws_personal_chat):
    auth_service = AuthService()
    payload = {"device_id": str(uuid4())}
    token = auth_service._jwt_auth.generate_access_token(subject=str(ws_test_user.id), payload=payload)
    auth_headers = {"Authorization": f"Bearer {token}"}
    uri = f"ws://{TEST_HOST}/ws/{ws_personal_chat.id}"
    async with ClientSession() as session:
        async with session.ws_connect(uri, headers=auth_headers) as websocket:
            assert websocket.closed is False
            await websocket.close()


@pytest.mark.asyncio
async def test_websocket_connect_disconnect(start_server, ws_db_session, ws_auth_headers, ws_personal_chat, ws_test_user):
    uri = f"ws://{TEST_HOST}/ws/{ws_personal_chat.id}"
    try:
        async with ClientSession() as session:
            async with session.ws_connect(uri, headers=ws_auth_headers) as websocket:
                pass
    except ConnectionError as e:
        assert str(e).find("1008") != -1
    finally:
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_websocket_send_message(start_server, ws_db_session, db_session_factory, ws_auth_headers, ws_personal_chat, ws_test_user):
    uri = f"ws://{TEST_HOST}/ws/{ws_personal_chat.id}"
    async with ClientSession() as session:
        async with session.ws_connect(uri, headers=ws_auth_headers) as websocket:
            message_uuid = uuid4()
            await asyncio.wait_for(websocket.send_json({
                "action": "send_message",
                "text": "Test message",
                "message_id": str(message_uuid),
                "chat_id": str(ws_personal_chat.id),
            }), timeout=2.0)
            print(f"🔄 Ждем")
            try:
                msg = await asyncio.wait_for(websocket.receive(), timeout=2.0)
                if msg.type == WSMsgType.TEXT:
                    response = msg.json()
                    print(f"📥 Получено: {response}")
                    assert response["text"] == "Test message"
                else:
                    print(f"🔴 Получен не текстовый тип: {msg.type}")
            except asyncio.TimeoutError:
                print("🔴 Таймаут ожидания сообщения")
                assert False, "Не получено сообщение от сервера"
            await asyncio.sleep(1)
            # Создаём новую сессию для проверки
            async with db_session_factory() as check_session:
                message = await Message.first(id=message_uuid, session=check_session)
                assert message is not None
                assert message.text == "Test message"
            await websocket.close()


@pytest.mark.asyncio
async def test_websocket_read_message_personal_chat(
        start_server, ws_db_session, db_session_factory, ws_auth_headers, ws_personal_chat, ws_test_user, ws_test_user2
):
    """
    Тестирует чтение сообщения в личном чате.
    ws_test_user отправляет сообщение, ws_test_user2 читает его.
    """
    uri = f"ws://{TEST_HOST}/ws/{ws_personal_chat.id}"

    # Отправляем сообщение от ws_test_user
    async with ClientSession() as session:
        async with session.ws_connect(uri, headers=ws_auth_headers) as websocket:
            message_uuid = uuid4()
            await asyncio.wait_for(websocket.send_json({
                "action": "send_message",
                "text": "Test message for reading",
                "message_id": str(message_uuid),
                "chat_id": str(ws_personal_chat.id),
            }), timeout=2.0)
            print(f"🔄 Ждем")
            try:
                msg = await asyncio.wait_for(websocket.receive(), timeout=2.0)
                if msg.type == WSMsgType.TEXT:
                    response = msg.json()
                    assert response["text"] == "Test message for reading"
                    assert response["message_id"] == str(message_uuid)
                else:
                    print(f"🔴 Получен не текстовый тип: {msg.type}")
            except asyncio.TimeoutError:
                print("🔴 Таймаут ожидания сообщения")
                assert False, "Не получено сообщение от сервера"
            await websocket.close()

    # Даём серверу время зафиксировать транзакцию
    await asyncio.sleep(0.1)

    # Генерируем токен для ws_test_user2
    auth_service = AuthService()
    payload = {"device_id": str(uuid4())}
    token = auth_service._jwt_auth.generate_access_token(subject=str(ws_test_user2.id), payload=payload)
    user2_headers = {"Authorization": f"Bearer {token}"}

    # ws_test_user2 подключается и читает сообщение
    async with ClientSession() as session:
        async with session.ws_connect(uri, headers=user2_headers) as websocket:
            await asyncio.wait_for(websocket.send_json({
                "action": "message_read",
                "message_id": str(message_uuid),
                "chat_id": str(ws_personal_chat.id),
            }), timeout=2.0)
            # Ждём ответа о прочтении
            logger.info(f"🔄 Ждем")
            try:
                msg = await asyncio.wait_for(websocket.receive(), timeout=2.0)
                if msg.type == WSMsgType.TEXT:
                    response = msg.json()
                    if response.get("action") == "message_read":
                        assert response["message_id"] == str(message_uuid)
                        assert response["read_by_user_id"] == str(ws_test_user2.id)
                else:
                    logger.error(f"🔴 Получен не текстовый тип: {msg.type}")
            except asyncio.TimeoutError:
                logger.error("🔴 Таймаут ожидания сообщения")
                assert False, "Не получено сообщение от сервера"

            # Проверяем, что сообщение помечено как прочитанное
            async with db_session_factory() as check_session:
                message = await Message.first(id=message_uuid, session=check_session)
                assert message is not None
                assert message.is_read is True

            await websocket.close()


@pytest.mark.asyncio
async def test_websocket_read_message_group_chat(
        start_server, ws_db_session, db_session_factory, ws_auth_headers, ws_group_chat, ws_test_user, ws_test_user2
):
    """
    Тестирует чтение сообщения в групповом чате.
    ws_test_user отправляет сообщение, ws_test_user2 читает его.
    Проверяем, что создаётся запись в MessageRead.
    """
    uri = f"ws://{TEST_HOST}/ws/{ws_group_chat.id}"

    # Отправляем сообщение от ws_test_user
    async with ClientSession() as session:
        async with session.ws_connect(uri, headers=ws_auth_headers) as websocket:
            message_uuid = uuid4()
            await asyncio.wait_for(websocket.send_json({
                "action": "send_message",
                "text": "Test group message",
                "message_id": str(message_uuid),
                "chat_id": str(ws_group_chat.id),
            }), timeout=20.0)
            logger.info(f"🔄 Ждем")
            try:
                msg = await asyncio.wait_for(websocket.receive(), timeout=2.0)
                if msg.type == WSMsgType.TEXT:
                    response = msg.json()
                    logger.info(f"📥 Получено: {response}")
                    assert response["text"] == "Test group message"
                else:
                    logger.error(f"🔴 Получен не текстовый тип: {msg.type}")
            except asyncio.TimeoutError:
                logger.error("🔴 Таймаут ожидания сообщения")
                assert False, "Не получено сообщение от сервера"

            await websocket.close()

    # Даём серверу время зафиксировать транзакцию
    await asyncio.sleep(0.1)

    # Генерируем токен для ws_test_user2
    auth_service = AuthService()
    payload = {"device_id": str(uuid4())}
    token = auth_service._jwt_auth.generate_access_token(subject=str(ws_test_user2.id), payload=payload)
    user2_headers = {"Authorization": f"Bearer {token}"}

    # ws_test_user2 подключается и читает сообщение
    async with ClientSession() as session:
        async with session.ws_connect(uri, headers=user2_headers) as websocket:
            await asyncio.wait_for(websocket.send_json({
                "action": "message_read",
                "message_id": str(message_uuid),
                "chat_id": str(ws_group_chat.id),
            }), timeout=10.0)
            logger.info(f"🔄 Ждем")
            try:
                msg = await asyncio.wait_for(websocket.receive(), timeout=10.0)
                if msg.type == WSMsgType.TEXT:
                    response = msg.json()
                    logger.info(f"📥 Получено: {response}")
                    assert response["message_id"] == str(message_uuid)
                    assert response.get("read_by_all") is True  # Так как только ws_test_user2 читает
                else:
                    logger.info(f"🔴 Получен не текстовый тип: {msg.type}")
            except asyncio.TimeoutError:
                logger.error("🔴 Таймаут ожидания сообщения")
                assert False, "Не получено сообщение от сервера"

            # Проверяем, что создана запись в MessageRead
            async with db_session_factory() as check_session:
                message_read = await MessageRead.first(
                    session=check_session,
                    message_id=message_uuid,
                    user_id=ws_test_user2.id
                )
                assert message_read is not None

            await websocket.close()


@pytest.mark.asyncio
async def test_websocket_read_message_invalid_id(
        start_server, ws_db_session, ws_auth_headers, ws_personal_chat, ws_test_user
):
    """
    Тестирует попытку чтения сообщения с несуществующим message_id.
    Ожидаем ошибку.
    """
    uri = f"ws://{TEST_HOST}/ws/{ws_personal_chat.id}"

    async with ClientSession() as session:
        async with session.ws_connect(uri, headers=ws_auth_headers) as websocket:
            invalid_message_id = uuid4()
            await asyncio.wait_for(websocket.send_json({
                "action": "message_read",
                "message_id": str(invalid_message_id),
                "chat_id": str(ws_personal_chat.id),
            }), timeout=2.0)
            # Ждём ответа об ошибке
            logger.info(f"🔄 Ждем")
            try:
                msg = await asyncio.wait_for(websocket.receive(), timeout=2.0)
                if msg.type == WSMsgType.TEXT:
                    response = msg.json()
                    assert "error" in response
                    assert response["error"] == "Сообщение не найдено"
                else:
                    logger.error(f"🔴 Получен не текстовый тип: {msg.type}")
            except asyncio.TimeoutError:
                logger.error("🔴 Таймаут ожидания сообщения")
                assert False, "Не получено сообщение от сервера"

            await websocket.close()


@pytest.mark.asyncio
async def test_websocket_send_multiple_messages(
    start_server, ws_db_session, db_session_factory, ws_auth_headers, ws_personal_chat, ws_test_user
):
    """
    Тестирует отправку нескольких сообщений с интервалом времени, как будто пользователь пишет в чат.
    Проверяет получение сообщений через WebSocket и их сохранение в базе данных.
    """
    uri = f"ws://{TEST_HOST}/ws/{ws_personal_chat.id}"
    async with ClientSession() as session:
        async with session.ws_connect(uri, headers=ws_auth_headers) as websocket:
            assert not websocket.closed
            print(f"🔗 Соединение установлено с {uri}")

            # Список для хранения UUID сообщений
            message_uuids = []
            messages_to_send = [
                "Привет, как дела?",
                "Я тут подумал...",
                "Давай созвонимся!"
            ]

            # Отправляем сообщения с интервалом 0.5 секунды
            for msg_text in messages_to_send:
                message_uuid = uuid4()
                message_uuids.append(message_uuid)
                await websocket.send_json({
                    "action": "send_message",
                    "text": msg_text,
                    "chat_id": str(ws_personal_chat.id),
                    "message_id": str(message_uuid)
                })
                print(f"📤 Сообщение отправлено: {msg_text} (UUID: {message_uuid})")
                await asyncio.sleep(0.5)  # Интервал между сообщениями

            # Ожидаем и проверяем получение всех сообщений
            received_messages = []
            try:
                for _ in range(len(messages_to_send)):
                    msg = await asyncio.wait_for(websocket.receive(), timeout=10.0)
                    if msg.type == WSMsgType.TEXT:
                        response = msg.json()
                        print(f"📥 Получено: {response}")
                        received_messages.append(response)
                    else:
                        print(f"🔴 Получен не текстовый тип: {msg.type}")
                        assert False, f"Ожидался текстовый тип, получен: {msg.type}"
            except asyncio.TimeoutError:
                print("🔴 Таймаут ожидания сообщения")
                assert False, "Не получены все сообщения от сервера"

            # Проверяем, что все сообщения получены
            for expected_text, received in zip(messages_to_send, received_messages):
                print(received)
                assert received["text"] == expected_text
                assert received["message_id"] in [str(uuid) for uuid in message_uuids]

            # Проверяем, что все сообщения сохранены в базе данных
            await asyncio.sleep(0.1)  # Даём серверу время зафиксировать транзакции
            async with db_session_factory() as check_session:
                for msg_uuid, msg_text in zip(message_uuids, messages_to_send):
                    message = await Message.first(id=msg_uuid, session=check_session)
                    assert message is not None, f"Сообщение {msg_uuid} не найдено в базе"
                    assert message.text == msg_text
                    assert message.chat_id == ws_personal_chat.id
                    assert message.sender_id == ws_test_user.id

            await websocket.close()
            print(f"🔴 Соединение закрыто")
