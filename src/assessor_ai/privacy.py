"""
Anonimização de PII — módulo neutro, sem dependência de nenhuma camada.

Vive aqui, e não em `agents/nodes/guardrail/`, porque tem três consumidores em três camadas
diferentes: o guardrail (entrada e saída), o `log_tool` de `core/logging.py` e a persistência de
mensagens em `repositories/chat_repository.py`. Enquanto morava dentro do guardrail, `core` e a
camada de serviço importavam
de `agents/nodes/` — inversão de dependência que forçava import lazy pra não fechar ciclo.
"""

import re
import uuid

# PII do usuário — redige na entrada E na saída
PII_USUARIO = [
    ("CPF",     r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}"),
    ("CNPJ",    r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"),
    ("CONTA",   r"\b\d{5,6}-\d{1}\b"),
    ("CARTAO",  r"\d{4}\s?\d{4}\s?\d{4}\s?\d{4}"),
]

PII = PII_USUARIO + [
    ("EMAIL",    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    ("TELEFONE", r"\(?\d{2}\)?\s?\d{4,5}-?\d{4}"),
]


def anonimizar_entrada(texto: str) -> tuple[str, dict]:
    mapa = {}

    for tipo, padrao in PII:
        for valor in re.findall(padrao, texto):
            token = f"[PII_{tipo}_{uuid.uuid4().hex[:6]}]"
            mapa[token] = valor
            texto = texto.replace(valor, token, 1)

    return texto, mapa


__all__ = ["PII", "PII_USUARIO", "anonimizar_entrada"]
