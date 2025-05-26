import uuid
from builtins import staticmethod
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.auth.config import settings
from app.auth.types import TokenType
from app.auth.utils import convert_to_timestamp


class JWTAuth:
    """
    Создание токенов
    """
    def generate_access_token(self,
                              subject: str,
                              payload: dict[str, Any] = None) -> str:
        """
        Создать access токен
        :param subject: ID пользователя
        :param payload: данные токена
        :return:
        """
        return self.__sign_token(
            type_token=TokenType.ACCESS,
            subject=subject,
            payload=payload or dict(),
            ttl=settings.ACCESS_TOKEN_TTL,
        )

    def generate_refresh_token(self,
                               subject: str,
                               payload: dict[str, Any] = None) -> str:
        """
        Создать refresh токен
        :param subject: ID пользователя
        :param payload: данные токена
        :return:
        """
        return self.__sign_token(
            type_token=TokenType.REFRESH,
            subject=subject,
            payload=payload or dict(),
            ttl=settings.REFRESH_TOKEN_TTL,
        )

    def __sign_token(self,
                     type_token: TokenType,
                     subject: str,
                     ttl: timedelta,
                     payload: dict[str, Any] = None) -> str:
        """
        Генерация токена
        :param type_token: тип токена
        :param subject: объект
        :param payload: данные в токене
        :param ttl: время жизни токена
        :return:
        """
        payload = payload or dict()
        current_timestamp = convert_to_timestamp(datetime.now(tz=timezone.utc))
        c_time = int(current_timestamp.total_seconds())
        data = dict(
            iss='tg',
            sub=subject,
            type=type_token.value,
            jti=self.__generate_jti() if not payload.get('jti') else payload.get('jti'),
            iat=c_time,
            nbf=payload['nbf'] if payload.get('nbf') else c_time,
        )
        exp: timedelta = timedelta(seconds=data['nbf']) + ttl
        data.update(dict(exp=int(exp.total_seconds()))) if ttl else None
        payload.update(data)
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def __generate_jti() -> str:
        return str(uuid.uuid4())

    def verify_token(self,
                     token) -> dict[str, Any]:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    def get_jti(self,
                token) -> str:
        return self.verify_token(token)['jti']

    def get_sub(self,
                token) -> str:
        return self.verify_token(token)['sub']

    def get_exp(self,
                token) -> int:
        return self.verify_token(token)['exp']

    @staticmethod
    def get_raw_jwt(token) -> dict[str, Any]:
        """Получить токен без проверки сигнатуры"""
        return jwt.decode(token, options={'verify_signature': False})
