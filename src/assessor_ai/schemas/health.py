from enum import StrEnum

from pydantic import BaseModel


class HealthStatus(StrEnum):
    OK = "ok"
    READY = "ready"
    UNAVAILABLE = "unavailable"


class HealthCheckResponse(BaseModel):
    status: HealthStatus
    message: str
    checks: dict[str, bool] | None = None


__all__ = ["HealthCheckResponse", "HealthStatus"]