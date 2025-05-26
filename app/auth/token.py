from fastapi import HTTPException
from starlette import status
from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket


def get_token(request: Request) -> str:
    """
    Универсальная функция - берем токен из headers, либо если там нет - из cookies
    :param request:
    :return:
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        if not (token := request.cookies.get('users_access_token')):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token not found')
        return token
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization scheme')
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization header format')
    return token


async def get_ws_token(websocket: WebSocket,
                       token: str = None) -> str:
    """
    Получить токен для websocket
    :param websocket:
    :param token:
    :return:
    """
    if token:  # Токен передан как query-параметр
        return token
    if not (auth_header := websocket.headers.get('Authorization')):
        await websocket.close(code=1008)  # Policy violation
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token not found')
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != 'bearer':
            await websocket.close(code=1008)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization scheme')
    except ValueError:
        await websocket.close(code=1008)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization header format')
    return token


def set_tokens(response: Response,
               access_token: str,
               refresh_token: str) -> Response:
    response.headers['Authorization'] = access_token
    response.set_cookie(key="users_access_token", value=access_token, httponly=True)
    response.set_cookie(key="users_refresh_token", value=refresh_token, httponly=True)
    return response


def del_tokens(response: Response) -> Response:
    response.headers['Authorization'] = ""
    response.delete_cookie(key="users_access_token")
    response.delete_cookie(key="users_refresh_token")
    return response
