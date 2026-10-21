from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.health import HealthCheckResponse
from app.services import health_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", status_code=status.HTTP_200_OK, response_model=HealthCheckResponse)
def liveness() -> HealthCheckResponse:
    return HealthCheckResponse(status="ok", message="service is running")


@router.get("/ready", status_code=status.HTTP_200_OK, response_model=HealthCheckResponse)
def readiness() -> HealthCheckResponse | JSONResponse:
    checks = health_service.checar_dependencias()

    if not all(checks.values()):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthCheckResponse(
                status="unavailable", message="one or more dependencies are down", checks=checks
            ).model_dump(),
        )

    return HealthCheckResponse(status="ready", message="all systems operational", checks=checks)
