import hashlib

from assessor_ai.tools.usuarios.schemas import (
    chave_api_key,
    chave_api_key_lookup,
    hash_api_key,
)


def testhash_api_key_e_sha256_deterministico():
    resultado = hash_api_key("minha-chave")

    assert resultado == hashlib.sha256(b"minha-chave").hexdigest()
    assert hash_api_key("minha-chave") == resultado


def testhash_api_key_chaves_diferentes_geram_hashes_diferentes():
    assert hash_api_key("chave-a") != hash_api_key("chave-b")


def testchave_api_key():
    assert chave_api_key("user-1") == "auth:user:user-1:api-key-hash"


def testchave_api_key_lookup():
    assert chave_api_key_lookup("abc123") == "auth:api-key:abc123"
