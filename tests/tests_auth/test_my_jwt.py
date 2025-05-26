import jwt
import pytest
from datetime import timedelta

from app.config import settings
from app.auth.my_jwt import JWTAuth
from app.auth.types import TokenType


@pytest.fixture
def jwt_auth():
    """Фикстура для создания экземпляра JWTAuth."""
    return JWTAuth()


@pytest.fixture
def mock_env(monkeypatch):
    """Фикстура для настройки переменных окружения для тестов."""
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-123")
    monkeypatch.setenv("AUTH_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_TTL", "1800")  # 30 минут в секундах
    monkeypatch.setenv("REFRESH_TOKEN_TTL", "604800")  # 7 дней в секундах
    yield
    # Очистка переменных окружения после теста (опционально)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("AUTH_ALGORITHM", raising=False)
    monkeypatch.delenv("ACCESS_TOKEN_TTL", raising=False)
    monkeypatch.delenv("REFRESH_TOKEN_TTL", raising=False)


def test_generate_access_token(jwt_auth, mock_env):
    """Проверяет генерацию access токена с TTL."""
    subject = "test-user"
    token = jwt_auth.generate_access_token(subject)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == subject
    assert payload["type"] == TokenType.ACCESS.value
    assert "exp" in payload
    exp_timestamp = payload["exp"]
    assert timedelta(seconds=exp_timestamp) > timedelta(seconds=payload["iat"]) + settings.ACCESS_TOKEN_TTL - timedelta(seconds=1)


def test_generate_refresh_token(jwt_auth, mock_env):
    """Проверяет генерацию refresh токена с TTL."""
    subject = "test-user"
    token = jwt_auth.generate_refresh_token(subject)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == subject
    assert payload["type"] == TokenType.REFRESH.value
    assert "exp" in payload
    exp_timestamp = payload["exp"]
    assert timedelta(seconds=exp_timestamp) > timedelta(seconds=payload["iat"]) + settings.REFRESH_TOKEN_TTL - timedelta(seconds=1)


def test_sign_token_with_ttl(jwt_auth, mock_env):
    """Проверяет генерацию токена с указанным TTL."""
    subject = "test-user"
    custom_ttl = timedelta(minutes=15)
    token = jwt_auth._JWTAuth__sign_token(type_token=TokenType.ACCESS, subject=subject, ttl=custom_ttl)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == subject
    assert payload["type"] == TokenType.ACCESS.value
    assert "exp" in payload
    assert timedelta(seconds=payload["exp"]) == timedelta(seconds=payload["nbf"]) + custom_ttl


def test_verify_token_valid(jwt_auth, mock_env):
    """Проверяет верификацию валидного токена."""
    subject = "test-user"
    token = jwt_auth.generate_access_token(subject)
    payload = jwt_auth.verify_token(token)
    assert payload["sub"] == subject
    assert payload["type"] == TokenType.ACCESS.value


def test_verify_token_invalid(jwt_auth, mock_env):
    """Проверяет, что невалидный токен вызывает исключение."""
    with pytest.raises(jwt.InvalidTokenError):
        jwt_auth.verify_token("invalid_token")


def test_get_jti(jwt_auth, mock_env):
    """Проверяет получение jti из токена."""
    subject = "test-user"
    token = jwt_auth.generate_access_token(subject)
    jti = jwt_auth.get_jti(token)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert jti == payload["jti"]
    assert isinstance(jti, str)


def test_get_sub(jwt_auth, mock_env):
    """Проверяет получение sub из токена."""
    subject = "test-user"
    token = jwt_auth.generate_access_token(subject)
    sub = jwt_auth.get_sub(token)
    assert sub == subject


def test_get_exp(jwt_auth, mock_env):
    """Проверяет получение exp из токена."""
    subject = "test-user"
    token = jwt_auth.generate_access_token(subject)
    exp = jwt_auth.get_exp(token)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert exp == payload["exp"]
    assert isinstance(exp, int)


def test_get_raw_jwt(jwt_auth, mock_env):
    """Проверяет получение сырого JWT без проверки подписи."""
    subject = "test-user"
    token = jwt_auth.generate_access_token(subject)
    raw_payload = jwt_auth.get_raw_jwt(token)
    assert raw_payload["sub"] == subject
    assert raw_payload["type"] == TokenType.ACCESS.value
    assert "jti" in raw_payload
