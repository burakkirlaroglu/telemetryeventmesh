from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import redis
import uuid

app = FastAPI(title="telemetryeventmesh-ws-gateway")

r = redis.Redis(host="tem_redis", port=6379, decode_responses=True)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    connection_id = str(uuid.uuid4())
    r.sadd("active_ws_connections", connection_id)

    try:
        while True:
            data = await ws.receive_text()
            await ws.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        pass
    finally:
        r.srem("active_ws_connections", connection_id)
