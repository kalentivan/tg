from builtins import staticmethod
from typing import Any

import jwt

from app.auth.config import get_auth_data


class JWTAuth:
    """
    Создание токенов
    """

    def __init__(self) -> None:
        self._config = get_auth_data()

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
