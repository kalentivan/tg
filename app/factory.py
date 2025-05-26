from fastapi import FastAPI
from contextlib import asynccontextmanager

from starlette.middleware.cors import CORSMiddleware

from app.database import engine
from app.models.base import Base
from app.routes import user, websocket, chat


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()

    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Разрешить запросы с любых источников. Можете ограничить список доменов
        allow_credentials=True,
        allow_methods=["*"],  # Разрешить все методы (GET, POST, PUT, DELETE и т.д.)
        allow_headers=["*"],  # Разрешить все заголовки
    )

    app.include_router(user.router)
    app.include_router(chat.router)
    app.include_router(websocket.router)

    @app.get("/")
    async def root():
        return {"message": "Chat App is running"}

    return app
