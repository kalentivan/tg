import uuid

import pytest
from starlette.exceptions import HTTPException
from starlette import status
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.auth import authenticate_user, get_current_user, get_current_ws_user, get_admin_user
from app.auth.config import get_auth_data
from app.auth.password import get_password_hash
from app.models.models import User


@pytest.mark.asyncio
async def test_authenticate_user_success(test_user, db_session: AsyncSession):
    """
    Проверяет успешную аутентификацию пользователя с правильными email и паролем.
    """
    user = await authenticate_user(email="test@example.com", password="test123", session=db_session)
    assert user is not None
    assert user.email == "test@example.com"
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_authenticate_user_invalid_email(db_session: AsyncSession):
    """
    Проверяет, что аутентификация с несуществующим email вызывает 401.
    """
    with pytest.raises(HTTPException) as exc:
        await authenticate_user(email="invalid@example.com", password="test123", session=db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(test_user, db_session: AsyncSession):
    """
    Проверяет, что аутентификация с неправильным паролем вызывает 401.
    """
    with pytest.raises(HTTPException) as exc:
        await authenticate_user(email="test@example.com", password="wrongpassword", session=db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_get_current_user_success(test_user, db_session: AsyncSession):
    """
    Проверяет получение пользователя по валидному токену.
    """
    auth_data = get_auth_data()
    token = jwt.encode({"sub": str(test_user.id)}, auth_data.secret, algorithm=auth_data.algorithm)
    user = await get_current_user(token=token, session=db_session)
    assert user is not None
    assert user.id == test_user.id
    assert user.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db_session: AsyncSession):
    """
    Проверяет, что невалидный токен вызывает 401.
    """
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token="invalid_token", session=db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "Токен не валидный!"


@pytest.mark.asyncio
async def test_get_current_user_no_user_id(db_session: AsyncSession):
    """
    Проверяет, что токен без user_id вызывает 401.
    """
    auth_data = get_auth_data()
    token = jwt.encode({"no_sub": "value"}, auth_data.secret, algorithm=auth_data.algorithm)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token, session=db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "Не найден ID пользователя"


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(db_session: AsyncSession):
    """
    Проверяет, что токен с несуществующим user_id вызывает 401.
    """
    auth_data = get_auth_data()
    token = jwt.encode({"sub": "non-existent-id"}, auth_data.secret, algorithm=auth_data.algorithm)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token, session=db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_ws_user_success(test_user, db_session: AsyncSession):
    """
    Проверяет получение пользователя по валидному токену для WebSocket.
    """
    auth_data = get_auth_data()
    token = jwt.encode({"sub": str(test_user.id)}, auth_data.secret, algorithm=auth_data.algorithm)
    user = await get_current_ws_user(token=token, session=db_session)
    assert user is not None
    assert user.id == test_user.id
    assert user.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_current_ws_user_invalid_token(db_session: AsyncSession):
    """
    Проверяет, что невалидный токен для WebSocket вызывает 401.
    """
    with pytest.raises(HTTPException) as exc:
        await get_current_ws_user(token="invalid_token", session=db_session)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "Токен не валидный!"


@pytest.mark.asyncio
async def test_get_admin_user_success(db_session: AsyncSession):
    """
    Проверяет получение администратора по валидному токену.
    """
    admin_user = User(
        id=uuid.uuid4(),
        username="adminuser",
        email="admin@example.com",
        password=get_password_hash("admin123"),
        is_admin=True
    )
    db_session.add(admin_user)
    await db_session.commit()

    auth_data = get_auth_data()
    device_id = str(uuid.uuid4())
    token = jwt.encode({"sub": str(admin_user.id), "device_id": device_id}, auth_data.secret, algorithm=auth_data.algorithm)
    user = await get_admin_user(token=token, session=db_session)
    assert user is not None
    assert user.email == "admin@example.com"
    assert user.is_admin is True


@pytest.mark.asyncio
async def test_get_admin_user_not_admin(test_user, db_session: AsyncSession):
    """
    Проверяет, что не-админ пользователь вызывает 403.
    """
    auth_data = get_auth_data()
    token = jwt.encode({"sub": str(test_user.id)}, auth_data.secret, algorithm=auth_data.algorithm)
    with pytest.raises(HTTPException) as exc:
        await get_admin_user(token=token, session=db_session)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Нет прав доступа"


@pytest.mark.asyncio
async def test_get_admin_user_invalid_token(db_session: AsyncSession):
    """
    Проверяет, что невалидный токен для админа вызывает 401.
    """
    with pytest.raises(HTTPException) as exc:
        await get_admin_user(token="invalid_token")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "Токен не валидный!"
