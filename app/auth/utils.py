from calendar import timegm
from datetime import datetime
from hashlib import sha256

from fastapi import HTTPException
from starlette import status


def convert_to_timestamp(dt: datetime) -> int:
    """
    :param dt:
    :return:
    """
    return timegm(dt.utctimetuple())


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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Invalid authorization header format')

    if 'Bearer ' not in authorization_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Invalid authorization header format')

    return authorization_header.replace('Bearer ', '')


