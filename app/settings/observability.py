from pydantic import BaseModel, SecretStr


class ObservabilitySettings(BaseModel):
    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr = SecretStr("")
    langsmith_project: str = "assessor-ai"
