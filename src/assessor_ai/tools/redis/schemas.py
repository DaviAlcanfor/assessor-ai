import hashlib

API_KEY_TTL_TIME = 3600 * 24
CHAT_TTL_TIME = 60
N_MESSAGES_ACCEPTED = 10
PROFILE_TTL_TIME = 3600

def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

def _chave_mensagem(user_id: str) -> str:
    return f"chat:{user_id}:message"

def _chave_api_key(user_id: str) -> str:
    return f"auth:user:{user_id}:api-key-hash"

def _chave_api_key_lookup(hashed_key: str) -> str:
    return f"auth:api-key:{hashed_key}"

def _chave_perfil(user_id: str) -> str:
    return f"user:{user_id}:profile"