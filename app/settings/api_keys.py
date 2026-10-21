from pydantic import BaseModel, SecretStr


class ApiKeysSettings(BaseModel):
    """Segredos que o próprio Assessor.AI exige de quem chama (não as chaves de provedores externos)."""

    signup_secret: SecretStr
