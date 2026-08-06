from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from assessor_ai.tools.mongo.connection import banco
from assessor_ai.tools.redis.connection import get_client
from interfaces.api.schemas.health import HealthCheckResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", status_code=status.HTTP_200_OK, response_model=HealthCheckResponse)
def liveness():
    return HealthCheckResponse(status="ok", message="service is running")


@router.get("/ready", status_code=status.HTTP_200_OK, response_model=HealthCheckResponse)
def readiness():
    checks = {"redis": False, "mongo": False}

    try:
        get_client().ping()
        checks["redis"] = True

        banco.client.admin.command("ping")
        checks["mongo"] = True

    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthCheckResponse(
                status="unavailable", message="one or more dependencies are down", checks=checks
            ).model_dump(),
        )

    return HealthCheckResponse(status="ready", message="all systems operational", checks=checks)