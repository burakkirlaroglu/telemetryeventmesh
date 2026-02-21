from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
import redis
import asyncio
import os

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "tem_redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        print("client bağlandı")
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # ignore client input
    except WebSocketDisconnect:
        manager.disconnect(ws)

async def redis_listener():
    pubsub = redis_client.pubsub()
    pubsub.subscribe("tem:events")

    while True:
        message = pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            await manager.broadcast(message["data"])
        await asyncio.sleep(0.01)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_listener())
