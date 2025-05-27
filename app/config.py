from pydantic_settings import BaseSettings, SettingsConfigDict
from datetime import timedelta
from functools import lru_cache


class Settings(BaseSettings):
    # DB settings
    TG_DB_NAME: str
    TG_DB_USER: str
    TG_DB_PASSWORD: str
    TG_DB_HOST: str
    TG_DB_PORT: str
    TG_DB_TEST_NAME: str

    # JWT settings
    TG_SECRET_KEY: str
    TG_AUTH_ALGORITHM: str
    TG_ACCESS_TOKEN_TTL: int  # в секундах
    TG_REFRESH_TOKEN_TTL: int

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @property
    def database_url(self):
        return (f"postgresql+asyncpg://{self.TG_DB_USER}:{self.TG_DB_PASSWORD}@{self.TG_DB_HOST}:"
                f"{self.TG_DB_PORT}/{self.TG_DB_NAME}")

    @property
    def ACCESS_TOKEN_TTL(self) -> timedelta:
        return timedelta(seconds=self.TG_ACCESS_TOKEN_TTL)

    @property
    def REFRESH_TOKEN_TTL(self) -> timedelta:
        return timedelta(seconds=self.TG_REFRESH_TOKEN_TTL)

    @property
    def SECRET_KEY(self) -> str:
        return self.TG_SECRET_KEY

    @property
    def ALGORITHM(self) -> str:
        return self.TG_AUTH_ALGORITHM


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
