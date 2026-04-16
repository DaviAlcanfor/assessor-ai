from dotenv import load_dotenv
import os

load_dotenv()

def _require(key: str) -> str:
    value = os.getenv(key)
    
    if not value:
        raise EnvironmentError(f"Variável de ambiente não definida: {key}")
    
    return value

GEMINI_API_KEY = _require("GEMINI_API_KEY")
GROQ_API_KEY   = _require("GROQ_API_KEY")
ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")
DATABASE_URI   = _require("DATABASE_URI")
