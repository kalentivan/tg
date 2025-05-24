import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket
from starlette import status
from app.auth.token import get_token, get_ws_token, get_token_header_and_cookies, set_tokens, del_tokens
from fastapi import HTTPException
from http.cookies import SimpleCookie


# Мок-объекты для тестов
@pytest.fixture
def mock_request():
    class MockRequest(Request):
        def __init__(self):
            scope = {"type": "http", "method": "GET", "headers": []}
            super().__init__(scope)
            self._headers = {}
            self._cookies = {}

        @property
        def headers(self) -> dict:
            return self._headers

        @headers.setter
        def headers(self, value):
            self._headers = value

        @property
        def cookies(self):
            return self._cookies

        @cookies.setter
        def cookies(self, value):
            self._cookies = value

    return MockRequest()


@pytest.fixture
def mock_response():
    return Response()


@pytest.fixture
def mock_websocket():
    class MockWebSocket(WebSocket):
        def __init__(self):
            scope = {"type": "websocket", "headers": []}

            async def mock_receive():
                return {"type": "websocket.receive", "text": None}

            async def mock_send(data):
                pass

            super().__init__(scope, receive=mock_receive, send=mock_send)
            self._headers = {}
            self._closed = False
            self.close_code = None

        @property
        def headers(self) -> dict:
            return self._headers

        @headers.setter
        def headers(self, value):
            self._headers = value

        async def close(self, code=1000, **kwargs):
            self._closed = True
            self.close_code = code

    return MockWebSocket()


def test_get_token_from_header(mock_request):
    """Проверяет получение токена из заголовка Authorization."""
    mock_request.headers['Authorization'] = 'Bearer test_token_123'
    token = get_token(mock_request)
    assert token == 'test_token_123'


def test_get_token_from_cookie(mock_request):
    """Проверяет получение токена из cookies, если заголовок отсутствует."""
    mock_request.cookies['users_access_token'] = 'cookie_token_123'
    token = get_token(mock_request)
    assert token == 'cookie_token_123'


def test_get_token_missing(mock_request):
    """Проверяет, что отсутствие токена вызывает 401."""
    with pytest.raises(HTTPException) as exc:
        get_token(mock_request)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Token not found'


def test_get_token_invalid_scheme(mock_request):
    """Проверяет, что неверная схема в заголовке вызывает 401."""
    mock_request.headers['Authorization'] = 'Basic test_token_123'
    with pytest.raises(HTTPException) as exc:
        get_token(mock_request)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Invalid authorization scheme'


def test_get_token_invalid_format(mock_request):
    """Проверяет, что неверный формат заголовка вызывает 401."""
    mock_request.headers['Authorization'] = 'Bearer'
    with pytest.raises(HTTPException) as exc:
        get_token(mock_request)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Invalid authorization header format'


@pytest.mark.asyncio
async def test_get_ws_token_from_query(mock_websocket):
    """Проверяет получение токена из query-параметра для WebSocket."""
    token = "query_token_123"
    result = await get_ws_token(mock_websocket, token=token)
    assert result == token
    assert not mock_websocket._closed


@pytest.mark.asyncio
async def test_get_ws_token_from_header(mock_websocket):
    """Проверяет получение токена из заголовка Authorization для WebSocket."""
    mock_websocket.headers['Authorization'] = 'Bearer ws_token_123'
    token = await get_ws_token(mock_websocket)
    assert token == 'ws_token_123'
    assert not mock_websocket._closed


@pytest.mark.asyncio
async def test_get_ws_token_missing(mock_websocket):
    """Проверяет, что отсутствие токена для WebSocket закрывает соединение и вызывает 401."""
    with pytest.raises(HTTPException) as exc:
        await get_ws_token(mock_websocket)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Token not found'
    assert mock_websocket._closed
    assert mock_websocket.close_code == 1008


@pytest.mark.asyncio
async def test_get_ws_token_invalid_scheme(mock_websocket):
    """Проверяет, что неверная схема для WebSocket закрывает соединение и вызывает 401."""
    mock_websocket.headers['Authorization'] = 'Basic ws_token_123'
    with pytest.raises(HTTPException) as exc:
        await get_ws_token(mock_websocket)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Invalid authorization scheme'
    assert mock_websocket._closed
    assert mock_websocket.close_code == 1008


@pytest.mark.asyncio
async def test_get_ws_token_invalid_format(mock_websocket):
    """Проверяет, что неверный формат заголовка для WebSocket вызывает 401."""
    mock_websocket.headers['Authorization'] = 'Bearer'
    with pytest.raises(HTTPException) as exc:
        await get_ws_token(mock_websocket)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Invalid authorization header format'
    assert mock_websocket._closed
    assert mock_websocket.close_code == 1008


def test_get_token_header_and_cookies_from_cookie(mock_request):
    """Проверяет получение токена из cookies."""
    mock_request.cookies['users_access_token'] = 'cookie_token_123'
    token = get_token_header_and_cookies(mock_request)
    assert token == 'cookie_token_123'


def test_get_token_header_and_cookies_from_header(mock_request):
    """Проверяет получение токена из заголовка Authorization."""
    mock_request.headers['Authorization'] = 'Bearer header_token_123'
    token = get_token_header_and_cookies(mock_request)
    assert token == 'header_token_123'


def test_get_token_header_and_cookies_missing(mock_request):
    """Проверяет, что отсутствие токена вызывает 401."""
    with pytest.raises(HTTPException) as exc:
        get_token_header_and_cookies(mock_request)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Token not found'


def test_get_token_header_and_cookies_invalid_scheme(mock_request):
    """Проверяет, что неверная схема в заголовке вызывает 401."""
    mock_request.headers['Authorization'] = 'Basic header_token_123'
    with pytest.raises(HTTPException) as exc:
        get_token_header_and_cookies(mock_request)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Invalid authorization scheme'


def test_get_token_header_and_cookies_invalid_format(mock_request):
    """Проверяет, что неверный формат заголовка вызывает 401."""
    mock_request.headers['Authorization'] = 'Bearer'
    with pytest.raises(HTTPException) as exc:
        get_token_header_and_cookies(mock_request)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Invalid authorization header format'


def test_set_tokens(mock_response):
    """Проверяет установку токенов в заголовки и cookies."""
    access_token = "access_token_123"
    refresh_token = "refresh_token_456"
    response = set_tokens(mock_response, access_token, refresh_token)

    # Проверяем заголовок Authorization
    assert response.headers['Authorization'] == access_token

    # Парсим заголовки Set-Cookie
    cookies = SimpleCookie()
    for cookie in response.headers.getlist('Set-Cookie'):
        cookies.load(cookie)

    # Проверяем cookies
    assert cookies['users_access_token'].value == access_token
    assert cookies['users_refresh_token'].value == refresh_token
    assert cookies['users_access_token']['httponly'] is True
    assert cookies['users_refresh_token']['httponly'] is True


def test_del_tokens(mock_response):
    """Проверяет удаление токенов из заголовков и cookies."""
    mock_response.headers['Authorization'] = 'old_token'
    mock_response.set_cookie('users_access_token', 'old_access_token')
    mock_response.set_cookie('users_refresh_token', 'old_refresh_token')
    response = del_tokens(mock_response)

    # Проверяем заголовок Authorization
    assert response.headers['Authorization'] == ""

    # Парсим заголовки Set-Cookie
    cookies = SimpleCookie()
    for cookie in response.headers.getlist('Set-Cookie'):
        cookies.load(cookie)

    # Проверяем, что cookies удалены (установлены с пустым значением и истёкшим сроком)
    assert 'users_access_token' in cookies
    assert cookies['users_access_token'].value == ""
    assert 'users_refresh_token' in cookies
    assert cookies['users_refresh_token'].value == ""
