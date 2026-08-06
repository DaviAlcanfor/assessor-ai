from uuid import uuid4

from assessor_ai.tools.mongo.connection import banco
from assessor_ai.tools.mongo.users.schemas import UserDocument
from config.logging import get_logger

logger = get_logger(__name__)

collection = banco["users"]


def inserir(nome: str, email: str) -> str:
    logger.info(f"Inserindo novo usuário: {email}")

    user_id = str(uuid4())
    document = UserDocument(
        user_id=user_id,
        nome=nome,
        email=email,
    )
    collection.insert_one(document.model_dump())

    return user_id


def buscar(user_id: str) -> dict | None:
    logger.info(f"Buscando usuário para user_id: {user_id}")

    return collection.find_one({"user_id": user_id})


def buscar_por_email(email: str) -> dict | None:
    logger.info(f"Buscando usuário para email: {email}")

    return collection.find_one({"email": email})


def buscar_algum() -> dict | None:
    logger.info("Buscando algum usuário existente")

    return collection.find_one()


def atualizar_perfil(user_id: str, perfil: str) -> None:
    logger.info(f"Atualizando perfil para user_id: {user_id}")

    collection.update_one(
        {"user_id": user_id},
        {"$set": {"profile": perfil}}
    )
    
    
def garantir_usuario(user_id: str, nome: str, email: str) -> None:
    collection.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {
            "user_id":  user_id,
            "nome":     nome,
            "email":    email,
            "profile":  "",
        }},
        upsert=True
    )