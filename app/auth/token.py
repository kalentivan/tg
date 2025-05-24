from fastapi import HTTPException
from starlette import status
from starlette.requests import Request
from starlette.websockets import WebSocket


def get_token(request: Request) -> str:
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        if token := request.cookies.get('users_access_token'):
            return token
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token not found')
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization scheme')
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization header format')
    return token


async def get_ws_token(websocket: WebSocket, token: str = None) -> str:
    if token:  # Токен передан как query-параметр
        return token
    auth_header = websocket.headers.get('Authorization')
    if not auth_header:
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


def get_token_header_and_cookies(request: Request) -> str:
    token = request.cookies.get('users_access_token')
    if not token:
        if not (auth_header := request.headers.get('Authorization')):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token not found')
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != 'bearer':
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization scheme')
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Invalid authorization header format')
    return token
