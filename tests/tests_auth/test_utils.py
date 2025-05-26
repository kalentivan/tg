import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import Request

from app.auth.config import settings
from app.auth.my_jwt import JWTAuth
from app.auth.types import TokenType
from app.auth.utils import __try_to_get_clear_token, check_access_token, check_revoked, convert_to_timestamp, \
    generate_device_id, get_sha256_hash
from app.models.models import IssuedJWTToken, User
from app.tools import validate_uuid


# Мок-объекты и фикстуры
@pytest.fixture
def mock_request():
    class State:
        def __init__(self):
            self.user = None
            self.device_id = None

    class MockRequest(Request):
        def __init__(self):
            scope = {"type": "http", "method": "GET", "headers": []}
            super().__init__(scope)
            self._headers = {}
            self._state = State()

        @property
        def headers(self) -> dict:
            return self._headers

        @headers.setter
        def headers(self, value):
            self._headers = value

        @property
        def state(self) -> State:
            return self._state

        @state.setter
        def state(self, value):
            self._state = value

    return MockRequest()


@pytest.fixture
def jwt_auth():
    """Фикстура для создания экземпляра JWTAuth."""
    return JWTAuth()


@pytest.fixture
async def valid_token(jwt_auth, test_user_success, db_session):
    """Фикстура для создания валидного access токена."""
    # Фиксированный user_id
    # Генерируем токен для этого пользователя
    jti = uuid.uuid4()
    payload = {
        "sub": str(test_user_success.id),
        "type": TokenType.ACCESS.value,
        "jti": str(jti),
        "device_id": "test-device-id"
    }
    token = jwt_auth._JWTAuth__sign_token(
        type_token=TokenType.ACCESS,
        subject=str(test_user_success.id),
        payload=payload,
        ttl=settings.ACCESS_TOKEN_TTL
    )
    await db_session.execute(
        delete(IssuedJWTToken).where(IssuedJWTToken.user_id == test_user_success.id)
    )
    token_obj = IssuedJWTToken(
        user_id=test_user_success.id,
        jti=jti,
        device_id="revoked-device-id",
        expired_time=datetime.now(timezone.utc) + settings.ACCESS_TOKEN_TTL
    )
    db_session.add(token_obj)
    await db_session.commit()
    return f"Bearer {token}"


@pytest.fixture
async def revoked_token(jwt_auth, test_user_revoke, db_session):
    """Фикстура для создания отозванного токена."""
    jti = uuid.uuid4()
    payload = {"sub": str(test_user_revoke.id), "type": TokenType.ACCESS.value, "jti": str(jti),
               "device_id": "revoked-device-id"}
    token = jwt_auth._JWTAuth__sign_token(
        type_token=TokenType.ACCESS,
        subject=str(test_user_revoke.id),
        payload=payload,
        ttl=settings.ACCESS_TOKEN_TTL
    )
    await db_session.execute(
        delete(IssuedJWTToken).where(IssuedJWTToken.user_id == test_user_revoke.id)
    )
    await db_session.commit()
    obj = IssuedJWTToken(
        user_id=test_user_revoke.id,
        jti=jti,
        device_id="revoked-device-id",
        revoked=True,
        expired_time=datetime.now(timezone.utc) + settings.ACCESS_TOKEN_TTL
    )
    db_session.add(obj)
    await db_session.commit()
    return f"Bearer {token}"


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Фикстура для создания тестового пользователя."""
    user_id = uuid.UUID("550e8400-e29b-41d4-a716-44665544dd00")
    user = User(id=user_id, username="testuser", email="test@example.com", password="hashed_password")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def test_user_token(db_session: AsyncSession):
    """Фикстура для создания тестового пользователя."""
    user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655d4dd00")
    user = User(id=user_id, username="test_user_token", email="test_user_token@example.com", password="hashed_password")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def test_user_revoke(db_session: AsyncSession):
    """Фикстура для создания тестового пользователя."""
    user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655d4dd00")
    user = User(id=user_id, username="test_user_token", email="test_user_revoke@example.com",
                password="hashed_password")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def test_user_success(db_session: AsyncSession):
    """Фикстура для создания тестового пользователя."""
    user_id = uuid.uuid4()
    user = User(id=user_id, username="test_user_token", email="test_user_success@example.com",
                password="hashed_password")
    db_session.add(user)
    await db_session.commit()
    return user


def test_generate_device_id():
    """Проверяет генерацию уникального device_id."""
    device_id1 = generate_device_id()
    device_id2 = generate_device_id()
    assert isinstance(device_id1, str)
    assert isinstance(device_id2, str)
    assert device_id1 != device_id2
    # Проверяем, что это валидный UUID версии 4
    uuid.UUID(device_id1)
    uuid.UUID(device_id2)


async def test_check_revoked_not_revoked(db_session: AsyncSession):
    """Проверяет, что не отозванный токен возвращает False."""
    user_id = uuid.uuid4()
    user = await User.create(id=user_id, username="test_check_revoked_not_revoked",
                             email="test_check_revoked_not_revoked@y.ru", session=db_session)
    jti = uuid.uuid4()
    token = IssuedJWTToken(
        user_id=user.id,
        jti=jti,
        device_id="test-device-id",
        revoked=False,
        expired_time=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db_session.add(token)
    await db_session.commit()
    assert await check_revoked(jti, session=db_session) is False


async def test_check_revoked_revoked(db_session: AsyncSession):
    """Проверяет, что отозванный токен возвращает True."""
    user_id = uuid.uuid4()
    user = await User.create(id=user_id, username="test_check_revoked_not_revoked",
                             email="test_check_revoked_not_revoked@y.ru", session=db_session)
    jti = uuid.uuid4()
    token = IssuedJWTToken(
        user_id=user.id,
        jti=jti,
        device_id="test-device-id",
        revoked=True,
        expired_time=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    db_session.add(token)
    await db_session.commit()
    assert await check_revoked(jti, session=db_session) is True


def test_convert_to_timestamp():
    """Проверяет преобразование datetime в timestamp."""
    dt = datetime(2025, 5, 24, 16, 23, tzinfo=timezone.utc)
    timestamp = convert_to_timestamp(dt)
    assert isinstance(timestamp, timedelta)
    assert timestamp == timedelta(seconds=1748103780)  # TODO 1748146980 - Ожидаемое значение для 2025-05-24 16:23 UTC


def test_get_sha256_hash():
    """Проверяет генерацию SHA-256 хэша."""
    test_string = "test_string"
    hash_value = get_sha256_hash(test_string)
    assert isinstance(hash_value, str)
    assert len(hash_value) == 64  # SHA-256 хэш имеет длину 64 символа в hex
    assert hash_value == "4b641e9a923d1ea57e18fe41dcb543e2c4005c41ff210864a710b0fbb2654c11"  # Исправленное значение


def test_try_to_get_clear_token_valid():
    """Проверяет извлечение токена из валидного заголовка."""
    header = "Bearer test_token_123"
    clear_token = __try_to_get_clear_token(header)
    assert clear_token == "test_token_123"


def test_try_to_get_clear_token_none():
    """Проверяет, что None в заголовке вызывает 401."""
    with pytest.raises(HTTPException) as exc:
        __try_to_get_clear_token(None)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "authorization_header is None"


def test_try_to_get_clear_token_no_bearer():
    """Проверяет, что отсутствие 'Bearer' вызывает 401."""
    with pytest.raises(HTTPException) as exc:
        __try_to_get_clear_token("test_token_123")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "Bearer not in authorization_header"


@pytest.mark.asyncio
async def test_check_access_token_success(mock_request, jwt_auth, valid_token, db_session: AsyncSession,
                                          test_user_success):
    """Проверяет успешную проверку access токена."""
    token = str(valid_token)
    mock_request.headers['Authorization'] = token
    result = await check_access_token(mock_request, session=db_session)
    assert result == token
    assert mock_request.state.user == test_user_success
    assert mock_request.state.device_id == "test-device-id"


@pytest.mark.asyncio
async def test_check_access_token_invalid_token(mock_request, db_session: AsyncSession):
    """Проверяет, что невалидный токен вызывает 401."""
    mock_request.headers['Authorization'] = "Bearer invalid_token_123"
    with pytest.raises(HTTPException) as exc:
        await check_access_token(mock_request, session=db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "Invalid or malformed token"


@pytest.mark.asyncio
async def test_check_access_token_revoked(mock_request, revoked_token, db_session: AsyncSession):
    """Проверяет, что отозванный токен вызывает 401."""
    token = str(revoked_token)
    mock_request.headers['Authorization'] = token
    with pytest.raises(HTTPException) as exc:
        await check_access_token(mock_request, session=db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "Token has been revoked"


@pytest.mark.asyncio
async def test_check_access_token_no_user(mock_request, jwt_auth, db_session: AsyncSession):
    """Проверяет, что несуществующий пользователь вызывает 401."""
    user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440004")
    token = jwt_auth._JWTAuth__sign_token(
        type_token=TokenType.ACCESS,
        subject=str(user_id),
        payload={"device_id": "test-device-id"},
        ttl=settings.ACCESS_TOKEN_TTL
    )
    mock_request.headers['Authorization'] = f"Bearer {token}"
    with pytest.raises(HTTPException) as exc:
        await check_access_token(mock_request, session=db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_validate_uuid_valid():
    """Проверяет, что валидный UUID корректно преобразуется."""
    valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
    result = validate_uuid(valid_uuid)
    assert isinstance(result, uuid.UUID)
    assert str(result) == valid_uuid


def test_validate_uuid_invalid():
    """Проверяет, что невалидный UUID вызывает HTTPException."""
    invalid_uuid = "invalid-uuid-string"
    with pytest.raises(HTTPException) as exc:
        validate_uuid(invalid_uuid)
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Invalid validate_uuid ID format"


def test_validate_uuid_empty():
    """Проверяет, что пустая строка возвращает None."""
    result = validate_uuid("")
    assert result is None


def test_validate_uuid_custom_error():
    """Проверяет, что кастомные параметры ошибки работают."""
    invalid_uuid = "invalid-uuid-string"
    custom_status = status.HTTP_401_UNAUTHORIZED
    custom_msg = "Custom UUID error"
    with pytest.raises(HTTPException) as exc:
        validate_uuid(invalid_uuid, er_status=custom_status, er_msg=custom_msg)
    assert exc.value.status_code == custom_status
    assert exc.value.detail == custom_msg
