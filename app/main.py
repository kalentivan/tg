import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine, get_db
from app.models.base import Base
from app.routes import user, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
# app.include_router(message.router)
app.include_router(user.router)
app.include_router(websocket.router, prefix="/chat", tags=["chat"])


@app.get("/")
async def root():
    return {"message": "Chat App is running"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
