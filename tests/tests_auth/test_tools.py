import uuid

import pytest
from jwt import InvalidTokenError

from app.config import settings
from app.auth.my_jwt import JWTAuth
from app.auth.tools import try_decode_token
from app.auth.types import TokenType


@pytest.fixture
def jwt_auth():
    """Фикстура для создания экземпляра JWTAuth с тестовыми данными."""
    return JWTAuth()


@pytest.fixture
def valid_token(jwt_auth):
    """Фикстура для создания валидного токена."""
    payload = {"sub": "test-user", "type": "access", "jti": str(uuid.uuid4())}
    token = jwt_auth._JWTAuth__sign_token(
        type_token=TokenType.ACCESS,
        subject="test-user",
        payload=payload,
        ttl=settings.ACCESS_TOKEN_TTL
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
