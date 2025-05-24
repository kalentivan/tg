import os
from dataclasses import dataclass
from datetime import timedelta

from pydantic_settings import BaseSettings


@dataclass
class JWTConfig:
    secret: str = os.getenv("TG_SECRET_KEY")
    algorithm: str = os.getenv("TG_AUTH_ALGORITHM")
    access_token_ttl: timedelta = timedelta(int(os.getenv("TG_ACCESS_TOKEN_TTL", 0)))
    refresh_token_ttl: timedelta = timedelta(int(os.getenv("TG_REFRESH_TOKEN_TTL", 0)))


class Settings(BaseSettings):
    """
    Настройки для JWT
    """
    SECRET_KEY: str = os.getenv("TG_SECRET_KEY")
    ALGORITHM: str = os.getenv("TG_AUTH_ALGORITHM")
    ACCESS_TOKEN_TTL: int = os.getenv("TG_ACCESS_TOKEN_TTL")
    REFRESH_TOKEN_TTL: int = os.getenv("TG_REFRESH_TOKEN_TTL")


settings = Settings()


def get_auth_data() -> JWTConfig:
    """
    Получить данные для генерации токенов
    :return:
    """
    return JWTConfig()
