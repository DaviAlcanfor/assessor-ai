# consts
API_KEY_TTL_TIME = 3600 * 24 
CHAT_TTL_TIME = 60
N_MESSAGES_ACCEPTED = 10



# Chaves redis por enquanto: 

# - chat:user:message -> guarda a quantidade de mensagens enviadas pelo usuário 
# - api_key:user -> guarda a chave de API alocada para o usuário
# ...

def _chave_mensagem(user_id: str) -> str:
    return f"chat:{user_id}:message"

def _chave_api_key(user_id: str) -> str:
    return f"api_key:{user_id}"