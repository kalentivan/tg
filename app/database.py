import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings as s

load_dotenv()

# Определяем URL базы данных в зависимости от режима
IS_TESTING = os.getenv("TESTING", "false").lower() == "true"

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{s.TG_DB_USER}:{s.TG_DB_PASSWORD}"
    f"@{s.TG_DB_HOST}:{s.TG_DB_PORT}/"
    f"{s.TG_DB_TEST_NAME if IS_TESTING else s.TG_DB_NAME}"
)

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSessionLocal:
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()
