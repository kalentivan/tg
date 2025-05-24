import uuid

import pytest
from jwt import InvalidTokenError
from app.auth.my_jwt import JWTAuth
from app.auth.config import get_auth_data
from app.auth.tools import try_decode_token


@pytest.fixture
def jwt_auth():
    """Фикстура для создания экземпляра JWTAuth с тестовыми данными."""
    return JWTAuth()


@pytest.fixture
def valid_token(jwt_auth):
    """Фикстура для создания валидного токена."""
    auth_data = get_auth_data()
    payload = {"sub": "test-user", "type": "access", "jti": "test-jti"}
    token = jwt_auth._JWTAuth__sign_token(
        type="access",
        subject="test-user",
        payload=payload,
        ttl=auth_data.access_token_ttl
    )
    return token


def test_try_decode_token_success(jwt_auth, valid_token):
    """Проверяет успешную декодировку валидного токена."""
    payload, error = try_decode_token(jwt_auth, valid_token)
    assert error is None
    assert payload is not None
    assert payload["sub"] == "test-user"
    assert payload["type"] == "access"
    assert isinstance(uuid.UUID(payload["jti"]), uuid.UUID)  # Проверяет, что строка является валидным UUID


def test_try_decode_token_invalid_token(jwt_auth):
    """Проверяет обработку невалидного токена."""
    invalid_token = "invalid_token_123"
    payload, error = try_decode_token(jwt_auth, invalid_token)
    assert payload is None
    assert isinstance(error, InvalidTokenError)


def test_try_decode_token_empty_token(jwt_auth):
    """Проверяет обработку пустого токена."""
    empty_token = ""
    payload, error = try_decode_token(jwt_auth, empty_token)
    assert payload is None
    assert isinstance(error, InvalidTokenError)


def test_try_decode_token_none_token(jwt_auth):
    """Проверяет обработку None вместо токена."""
    payload, error = try_decode_token(jwt_auth, None)
    assert payload is None
    assert isinstance(error, InvalidTokenError)
