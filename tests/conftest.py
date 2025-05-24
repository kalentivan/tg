import os
import random
import uuid
from datetime import datetime, timedelta

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Загружаем переменные окружения из .env
load_dotenv()

from app.auth.service import AuthService
from app.database import get_db
from app.dto import UserPwdDTO
from app.main import app
from app.models.models import Base, Chat, GroupMember, Message, MessageRead, User

# Тестовая база данных (SQLite в памяти)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///test.sqlite")
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Переопределяем зависимость get_db для тестов
async def override_get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def db_engine():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Сбрасываем таблицы перед созданием
        await conn.run_sync(Base.metadata.create_all)  # Создаём таблицы
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(db_engine):
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def client(db_engine):
    return TestClient(app)


@pytest.fixture
async def test_user(db_session):
    if user := await User.first(email="test@example.com", session=db_session):
        return user
    user_data = UserPwdDTO(
        username="testuser",
        email="test@example.com",
        password="test123"
    )
    auth_service = AuthService()
    user, tokens = await auth_service.register(user_data, session=db_session)
    return user


@pytest.fixture
async def test_user2(db_session):
    if user := await User.first(email="test2@example.com", session=db_session):
        return user
    user_data = UserPwdDTO(
        username="testuser2",
        email="test2@example.com",
        password="test123"
    )
    auth_service = AuthService()
    user, tokens = await auth_service.register(user_data, session=db_session)
    return user


@pytest.fixture
async def auth_headers(test_user):
    auth_service = AuthService()
    payload = {"device_id": str(uuid.uuid4())}
    token = auth_service._jwt_auth.generate_access_token(subject=str(test_user.id), payload=payload)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def personal_chat(db_session, test_user, test_user2):
    chat = await Chat.create(
        name=None,
        is_group=False,
        admin_id=test_user.id,
        session=db_session
    )
    await GroupMember.create(user_id=test_user.id, chat_id=chat.id, session=db_session)
    await GroupMember.create(user_id=test_user2.id, chat_id=chat.id, session=db_session)
    return chat


@pytest.fixture
async def group_chat(db_session, test_user, test_user2):
    if not (chat := await Chat.first(name="Test Group", session=db_session)):
        chat = await Chat.create(
            name="Test Group",
            is_group=True,
            admin_id=test_user.id,
            session=db_session
        )
    chat.is_group = True
    chat.admin_id = test_user.id
    await chat.save(update_fields=["is_group", "admin_id"], session=db_session)
    await GroupMember.create(user_id=test_user.id, chat_id=chat.id, session=db_session)
    await GroupMember.create(user_id=test_user2.id, chat_id=chat.id, session=db_session)
    return chat


@pytest.fixture
async def test_data(db_session):
    """
    Создает тестовые данные: пользователи, чаты, участники и сообщения.
    Возвращает словарь с созданными объектами.
    """
    auth_service = AuthService()

    # Создаем 10 пользователей
    users = []
    for i in range(10):
        user_data = UserPwdDTO(
            username=f"user{i}",
            email=f"user{i}@example.com",
            password="test123"
        )
        if not (user := await User.first(email=f"user{i}@example.com", session=db_session)):
            user, tokens = await auth_service.register(user_data, session=db_session)
        users.append(user)

    # Создаем 5 личных чатов
    personal_chats = []
    used_pairs = set()
    for _ in range(5):
        user1, user2 = random.sample(users, 2)
        pair = tuple(sorted([str(user1.id), str(user2.id)]))
        if pair in used_pairs:
            continue
        used_pairs.add(pair)
        chat = await Chat.create(
            name=None,
            is_group=False,
            admin_id=user1.id,
            session=db_session
        )
        await GroupMember.create(user_id=user1.id, chat_id=chat.id, session=db_session)
        await GroupMember.create(user_id=user2.id, chat_id=chat.id, session=db_session)
        personal_chats.append(chat)

    # Создаем 3 групповых чата
    group_chats = []
    group_chat_members = {}
    for i in range(3):
        if not (chat := await Chat.first(name=f"Group Chat {i}", session=db_session)):
            chat = await Chat.create(
                name=f"Group Chat {i}",
                is_group=True,
                admin_id=random.choice(users).id,
                session=db_session
            )
        num_members = random.randint(3, 5)
        members = random.sample(users, num_members)
        for member in members:
            await GroupMember.create(user_id=member.id, chat_id=chat.id, session=db_session)
        group_chats.append(chat)
        group_chat_members[chat.id] = len(await GroupMember.list(chat_id=chat.id, session=db_session))

    # Создаем сообщения в каждом чате
    messages = []
    chat_messages = {}  # Храним количество сообщений для каждого чата
    messages_with_reads = {}  # Храним сообщения с прочтениями для каждого чата
    for chat in personal_chats + group_chats:
        await db_session.execute(
            delete(Message).where(Message.chat_id == chat.id)
        )
        await db_session.commit()
        members = await GroupMember.list(session=db_session, chat_id=chat.id)
        member_ids = [m.user_id for m in members]
        num_messages = random.randint(10, 50)
        chat_messages[chat.id] = num_messages
        messages_with_reads[chat.id] = []
        for i in range(num_messages):
            sender_id = random.choice(member_ids)
            message = await Message.create(
                chat_id=chat.id,
                sender_id=sender_id,
                text=f"Message {i} in chat {chat.id}",
                timestamp=datetime.utcnow() - timedelta(minutes=random.randint(0, 1000)),
                is_read=random.choice([True, False]) if not chat.is_group else False,
                id=uuid.uuid4(),
                session=db_session
            )
            messages.append(message)
            # Для групповых чатов добавляем случайные прочтения
            if chat.is_group:
                eligible_members = [m for m in members if m.user_id != sender_id]
                num_readers = random.randint(0, len(eligible_members) - 1)
                num_readers = min(num_readers, len(eligible_members))
                if eligible_members and num_readers > 0:
                    readers = random.sample(eligible_members, num_readers)
                    for reader in readers:
                        await MessageRead.create(
                            message_id=message.id,
                            user_id=reader.user_id,
                            session=db_session
                        )
                    messages_with_reads[chat.id].append(message.id)

    return {
        "users": users,
        "personal_chats": personal_chats,
        "group_chats": group_chats,
        "messages": messages,
        "group_chat_members": group_chat_members,
        "chat_messages": chat_messages,  # Количество сообщений для каждого чата
        "messages_with_reads": messages_with_reads  # Сообщения с прочтениями для каждого чата
    }
