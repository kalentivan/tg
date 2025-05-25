from typing import Dict, Set

from fastapi import WebSocket

from core.types import ID


class ConnectionManager:
    def __init__(self):
        # Храним соединения: {chat_id: {user_id: set(websocket)}}
        self.active_connections: Dict[ID, Dict[ID, Set[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, chat_id: ID, user_id: ID):
        chat_id = str(chat_id)
        user_id = str(user_id)
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = {}
        if user_id not in self.active_connections[chat_id]:
            self.active_connections[chat_id][user_id] = set()
        self.active_connections[chat_id][user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, chat_id: ID, user_id: ID):
        chat_id = str(chat_id)
        user_id = str(user_id)
        if chat_id in self.active_connections and user_id in self.active_connections[chat_id]:
            self.active_connections[chat_id][user_id].discard(websocket)
            if not self.active_connections[chat_id][user_id]:
                del self.active_connections[chat_id][user_id]
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def send_message(self, message: dict, chat_id: ID):
        chat_id = str(chat_id)
        if chat_id in self.active_connections:
            for user_id, websockets in self.active_connections[chat_id].items():
                for websocket in websockets:
                    await websocket.send_json(message)


connection_manager = ConnectionManager()
