import asyncio
import json
import logging
import os
import uuid
from typing import Dict, Set, Optional

import httpx
import redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "tem_redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

DJANGO_INTERNAL_URL = os.getenv(
    "DJANGO_INTERNAL_URL",
    "http://tem_nginx_gateway:8009/internal/auth/introspect/",
)

CACHE_TTL = int(os.getenv("AUTH_CACHE_TTL", "300"))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        await websocket.accept()
        conn_id = str(uuid.uuid4())
        self.active_connections[conn_id] = websocket
        self.user_connections.setdefault(user_id, set()).add(conn_id)
        return conn_id

    def disconnect(self, conn_id: str, user_id: str):
        self.active_connections.pop(conn_id, None)
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(conn_id)
            if not self.user_connections[user_id]:
                self.user_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: str):
        conn_ids = list(self.user_connections.get(user_id, set()))
        for conn_id in conn_ids:
            ws = self.active_connections.get(conn_id)
            if ws and ws.application_state == WebSocketState.CONNECTED:
                await ws.send_text(message)


manager = ConnectionManager()


async def authenticate(api_key: str) -> Optional[dict]:
    cache_key = f"ws:auth:{api_key}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                DJANGO_INTERNAL_URL,
                params={"token": api_key},
            )
    except Exception as e:
        logging.exception("introspect request failed: %s", e)
        return None

    if resp.status_code != 200:
        logging.warning("introspect failed: status=%s body=%s", resp.status_code, resp.text)
        return None

    data = resp.json()
    if "user_id" not in data:
        logging.warning("introspect missing user_id: %s", data)
        return None

    redis_client.setex(cache_key, CACHE_TTL, json.dumps(data))
    return data


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=1008)
        return

    auth_data = await authenticate(token)
    if not auth_data:
        await ws.close(code=1008)
        return

    user_id = auth_data["user_id"]

    conn_id = await manager.connect(ws, user_id)
    logging.info("ws connected user_id=%s conn_id=%s", user_id, conn_id)

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(conn_id, user_id)
        logging.info("ws disconnected user_id=%s conn_id=%s", user_id, conn_id)


async def redis_listener():
    pubsub = redis_client.pubsub()
    pubsub.subscribe("tem:events")

    while True:
        msg = pubsub.get_message(ignore_subscribe_messages=True)
        if msg:
            data = json.loads(msg["data"])
            user_id = data.get("user_id")
            if user_id:
                await manager.send_to_user(user_id, msg["data"])
        await asyncio.sleep(0.01)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_listener())