import os
from dataclasses import dataclass
from datetime import timedelta

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Настройки для JWT
    """
    SECRET_KEY: str = os.getenv("TG_SECRET_KEY")
    ALGORITHM: str = os.getenv("TG_AUTH_ALGORITHM")
    ACCESS_TOKEN_TTL: timedelta = timedelta(seconds=int(os.getenv("TG_ACCESS_TOKEN_TTL", 0)))
    REFRESH_TOKEN_TTL: timedelta = timedelta(seconds=int(os.getenv("TG_REFRESH_TOKEN_TTL", 0)))


settings = Settings()

