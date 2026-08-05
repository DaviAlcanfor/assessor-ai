import hashlib

from assessor_ai.tools.redis.schemas import (
    _chave_api_key,
    _chave_api_key_lookup,
    _chave_mensagem,
    _chave_perfil,
    _hash_api_key,
)


def test_hash_api_key_e_sha256_deterministico():
    resultado = _hash_api_key("minha-chave")

    assert resultado == hashlib.sha256(b"minha-chave").hexdigest()
    assert _hash_api_key("minha-chave") == resultado


def test_hash_api_key_chaves_diferentes_geram_hashes_diferentes():
    assert _hash_api_key("chave-a") != _hash_api_key("chave-b")


def test_chave_mensagem():
    assert _chave_mensagem("user-1") == "chat:user-1:message"


def test_chave_api_key():
    assert _chave_api_key("user-1") == "auth:user:user-1:api-key-hash"


def test_chave_api_key_lookup():
    assert _chave_api_key_lookup("abc123") == "auth:api-key:abc123"


def test_chave_perfil():
    assert _chave_perfil("user-1") == "user:user-1:profile"
