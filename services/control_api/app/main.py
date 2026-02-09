from fastapi import FastAPI
import os

app = FastAPI(title="telemetryeventmesh-control-api")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    # ileride: db, redis, rabbitmq check
    return {"ready": True}


@app.get("/version")
def version():
    return {
        "service": "control-api",
        "version": os.getenv("SERVICE_VERSION", "dev"),
    }
