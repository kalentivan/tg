import uuid
from builtins import staticmethod
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.auth.config import get_auth_data
from app.auth.types import TokenType
from app.auth.utils import convert_to_timestamp


class JWTAuth:
    """
    Создание токенов
    """

    def __init__(self) -> None:
        self._config = get_auth_data()

    def generate_unlimited_access_token(self,
                                        subject: str,
                                        payload: dict[str, Any] = None) -> str:
        """
        Создать бесконечный access токен
        :param subject:
        :param payload:
        :return:
        """
        return self.__sign_token(type=TokenType.ACCESS.value,
                                 subject=subject,
                                 payload=payload or dict()
                                 )

    def generate_access_token(self,
                              subject: str,
                              payload: dict[str, Any] = None) -> str:
        """
        Создать access токен
        :param subject:
        :param payload:
        :return:
        """
        return self.__sign_token(
            type=TokenType.ACCESS.value,
            subject=subject,
            payload=payload or dict(),
            ttl=self._config.access_token_ttl,
        )

    def generate_refresh_token(self,
                               subject: str,
                               payload: dict[str, Any] = None) -> str:
        """
        Создать refresh токен
        :param subject:
        :param payload:
        :return:
        """
        return self.__sign_token(
            type=TokenType.REFRESH.value,
            subject=subject,
            payload=payload or dict(),
            ttl=self._config.refresh_token_ttl,
        )

    def __sign_token(self,
                     type: str,
                     subject: str,
                     payload: dict[str, Any] = None,
                     ttl: timedelta = None) -> str:
        """
        Генерация токена
        :param type: тип шифрования
        :param subject: объект
        :param payload: данные в токене
        :param ttl:
        :return:
        """
        payload = payload or dict()
        current_timestamp = convert_to_timestamp(datetime.now(tz=timezone.utc))

        data = dict(
            iss='tg',
            sub=subject,
            type=type,
            jti=self.__generate_jti(),
            iat=current_timestamp,
            nbf=payload['nbf'] if payload.get('nbf') else current_timestamp,
        )
        data.update(dict(exp=data['nbf'] + int(ttl.total_seconds()))) if ttl else None
        payload.update(data)
        return jwt.encode(payload, self._config.secret, algorithm=self._config.algorithm)

    @staticmethod
    def __generate_jti() -> str:
        """

        :return:
        """
        return str(uuid.uuid4())

    def verify_token(self,
                     token) -> dict[str, Any]:
        """

        :param token:
        :return:
        """
        return jwt.decode(token, self._config.secret, algorithms=[self._config.algorithm])

    def get_jti(self,
                token) -> str:
        """

        :param token:
        :return:
        """
        return self.verify_token(token)['jti']

    def get_sub(self,
                token) -> str:
        """

        :param token:
        :return:
        """
        return self.verify_token(token)['sub']

    def get_exp(self,
                token) -> int:
        """

        :param token:
        :return:
        """
        return self.verify_token(token)['exp']

    @staticmethod
    def get_raw_jwt(token) -> dict[str, Any]:
        """
        Return the payload of the token without checking the validity of the token
        """
        return jwt.decode(token, options={'verify_signature': False})
