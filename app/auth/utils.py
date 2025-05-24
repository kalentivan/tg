import uuid
from datetime import datetime, timezone
from hashlib import sha256

import jwt
from fastapi import Request
from jwt.exceptions import InvalidTokenError
from starlette import status
from starlette.exceptions import HTTPException

from app.auth.config import get_auth_data
from app.auth.types import TokenType
from app.models.models import IssuedJWTToken
from app.models.models import User


def generate_device_id() -> str:
    """
    Создание ID устройства
    :return:
    """
    return str(uuid.uuid4())


async def check_revoked(jti: str, session) -> bool:
    """

    :param jti:
    :return:
    """
    if isinstance(jti, str):
        jti = uuid.UUID(jti)
    note = await IssuedJWTToken.first(jti=jti, revoked=True, session=session)
    return bool(note)


def convert_to_timestamp(dt: datetime) -> int:
    """
    Преобразует datetime в timestamp
    :param dt: Объект datetime
    :return: timestamp в секундах
    """
    if dt.tzinfo is None:
        raise ValueError("Datetime must have timezone information")

    # Приводим время к UTC
    dt_utc = dt.astimezone(timezone.utc)

    # Вычисляем количество секунд вручную
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

    # Разница в днях
    delta_days = (dt_utc.date() - epoch.date()).days
    seconds_in_days = delta_days * 86400

    # Время в секундах
    seconds_in_time = dt_utc.hour * 3600 + dt_utc.minute * 60 + dt_utc.second

    # Итоговый timestamp
    return seconds_in_days + seconds_in_time


def get_sha256_hash(line: str) -> str:
    """

    :param line:
    :return:
    """
    return sha256(str.encode(line)).hexdigest()


def __try_to_get_clear_token(authorization_header: str) -> str:
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
        auth_data = get_auth_data()
        payload = jwt.decode(jwt=clear_token, key=auth_data.secret, algorithms=[auth_data.algorithm],
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


