import os
from dataclasses import dataclass
from datetime import timedelta

from pydantic_settings import BaseSettings


@dataclass
class JWTConfig:
    secret: str = os.getenv("SECRET_KEY")
    algorithm: str = os.getenv("AUTH_ALGORITHM")
    access_token_ttl: timedelta = timedelta(int(os.getenv("ACCESS_TOKEN_TTL")))
    refresh_token_ttl: timedelta = timedelta(int(os.getenv("REFRESH_TOKEN_TTL")))


class Settings(BaseSettings):
    """
    Настройки для JWT
    """
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("AUTH_ALGORITHM")
    ACCESS_TOKEN_TTL: int = os.getenv("ACCESS_TOKEN_TTL")
    REFRESH_TOKEN_TTL: int = os.getenv("REFRESH_TOKEN_TTL")


settings = Settings()


def get_auth_data() -> JWTConfig:
    """
    Получить данные для генерации токенов
    :return:
    """
    return JWTConfig()
