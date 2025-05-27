import logging
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Храним соединения: {chat_id: {user_id: set(websocket)}}
        self.active_connections: Dict[UUID, Dict[UUID, Set[WebSocket]]] = {}

    async def connect(self,
                      websocket: WebSocket,
                      chat_id: UUID,
                      user_id: UUID):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = {}
        if user_id not in self.active_connections[chat_id]:
            self.active_connections[chat_id][user_id] = set()
        self.active_connections[chat_id][user_id].add(websocket)

    def disconnect(self,
                   websocket: WebSocket,
                   chat_id: UUID,
                   user_id: UUID):
        if chat_id in self.active_connections and user_id in self.active_connections[chat_id]:
            self.active_connections[chat_id][user_id].discard(websocket)
            if not self.active_connections[chat_id][user_id]:
                del self.active_connections[chat_id][user_id]
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def send_message(self,
                           message: dict,
                           chat_id: UUID,
                           recipient_id: UUID | None = None):
        if chat_id not in self.active_connections:
            logger.info(f"🛑🛑 {chat_id=} not in self.active_connections!")
            return
        for user_id, websockets in self.active_connections[chat_id].items():
            if not (recipient_id is None or str(user_id) == str(recipient_id)):
                logger.info(f"🛑🛑 not (recipient_id is None or user_id == recipient_id)")
                continue
            for websocket in websockets:
                await websocket.send_json(message)
                logger.info(f"✅✅ {message=} Отправлено!")


connection_manager = ConnectionManager()
