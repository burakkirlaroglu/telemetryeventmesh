from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uuid
import os
import time
import redis

app = FastAPI(title="telemetryeventmesh-ws-gateway")

REDIS_HOST = os.getenv("REDIS_HOST", "tem_redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
GATEWAY_ID = os.getenv("GATEWAY_ID", "unknown-gateway")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "300"))


def session_key(user_id: str) -> str:
    return f"ws:session:{user_id}"


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    user_id = ws.query_params.get("user_id")
    if not user_id:
        await ws.close(code=1008)
        return

    await ws.accept()

    now = int(time.time())
    conn_id = str(uuid.uuid4())

    old = r.hgetall(session_key(user_id))
    if old:
        last_seq = old.get("last_msg_seq", "0")
        await ws.send_text(f"resume:last_msg_seq={last_seq}")

    r.hset(
        session_key(user_id),
        mapping={
            "user_id": user_id,
            "conn_id": conn_id,
            "gateway_id": GATEWAY_ID,
            "status": "connected",
            "connected_at": str(now),
            "last_seen_at": str(now),
            "last_msg_seq": old.get("last_msg_seq", "0") if old else "0",
        },
    )
    r.expire(session_key(user_id), SESSION_TTL_SECONDS)

    try:
        while True:
            msg = await ws.receive_text()

            seq = r.hincrby(session_key(user_id), "last_msg_seq", 1)
            r.hset(session_key(user_id), mapping={"last_seen_at": str(int(time.time()))})
            r.expire(session_key(user_id), SESSION_TTL_SECONDS)

            await ws.send_text(f"seq={seq} echo={msg}")

    except WebSocketDisconnect:
        r.hset(session_key(user_id), mapping={"status": "disconnected", "last_seen_at": str(int(time.time()))})
        r.expire(session_key(user_id), SESSION_TTL_SECONDS)
