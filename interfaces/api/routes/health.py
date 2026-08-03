from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from tools.redis.connection import get_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", status_code=status.HTTP_200_OK)
def liveness():
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
def readiness():
    checks = {"redis": False}

    try:
        client = get_client()
        client.ping()
        checks["redis"] = True

    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "checks": checks},
        )

    return {"status": "ready", "checks": checks}