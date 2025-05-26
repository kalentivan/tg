import uuid
from calendar import timegm
from datetime import datetime, timezone
from hashlib import sha256

import jwt
from fastapi import Request
from jwt.exceptions import InvalidTokenError
from starlette import status
from starlette.exceptions import HTTPException
from datetime import timedelta

from app.config import settings
from app.auth.types import TokenType
from app.models.models import IssuedJWTToken
from app.models.models import User


def generate_device_id() -> str:
    """
    Создание ID устройства
    :return:
    """
    return str(uuid.uuid4())


async def check_revoked(jti: str | uuid.UUID, session) -> bool:
    """

    :param jti:
    :return:
    """
    if isinstance(jti, str):
        jti = uuid.UUID(jti)
    note = await IssuedJWTToken.first(jti=jti, revoked=True, session=session)
    return bool(note)


def convert_to_timestamp(dt: datetime) -> timedelta:
    # Проверим наличие timezone
    if dt.tzinfo is None:
        raise ValueError("datetime object must be offset-aware (have timezone info)")

    # Получаем Unix-таймстамп в секундах
    timestamp_seconds = timegm(dt.utctimetuple())

    # Преобразуем в timedelta
    return timedelta(seconds=timestamp_seconds)


def get_sha256_hash(line: str) -> str:
    """
    :param line:
    :return:
    """
    return sha256(str.encode(line)).hexdigest()


def __try_to_get_clear_token(authorization_header: str | None) -> str:
    """
    Убрать из токена слово Bearer
    :param authorization_header:
    :return:
    """
    if authorization_header is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='authorization_header is None')

    if 'Bearer ' not in authorization_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer not in authorization_header")

    return authorization_header.replace('Bearer ', '')


async def check_access_token(request: Request,
                             session=None
                             ) -> str:
    """

    :param session:
    :param request:
    :return:
    """
    authorization_header = request.headers.get('Authorization')
    clear_token = __try_to_get_clear_token(authorization_header=authorization_header)
    try:
        payload = jwt.decode(jwt=clear_token, key=settings.SECRET_KEY, algorithms=settings.ALGORITHM,
                             options={"verify_exp": False})
        if payload['type'] != TokenType.ACCESS.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or malformed token"
            )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token"
        )

    if await check_revoked(payload['jti'], session=session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )

    user_id = payload['sub']
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    request.state.user = await User.get_or_404(id=user_id, session=session,
                                               er_status=status.HTTP_401_UNAUTHORIZED,
                                               er_msg="Token has been revoked")
    request.state.device_id = payload['device_id']
    return authorization_header


