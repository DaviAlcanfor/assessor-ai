from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GROQ_API_KEY: str
    
    POSTGRES_URL: str 
    
    UPSTASH_REDIS_REST_URL: str 
    UPSTASH_REDIS_REST_TOKEN: str
    
    MONGO_USER: str
    MONGO_PASSWORD: str
    MONGO_URL: str
    MONGO_COLLECTION_NAME: str
    
    QDRANT_API_KEY: str
    QDRANT_CLUSTER_ENDPOINT: str
    QDRANT_COLLECTION_NAME: str
    
    JWT_SECRET_KEY: str

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,  
        "extra": "ignore",        
    }

settings = Settings()