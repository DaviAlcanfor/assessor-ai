from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GROQ_API_KEY: str
    DATABASE_URI: str

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,  
        "extra": "ignore",        
    }

settings = Settings()