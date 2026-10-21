from enum import StrEnum


class TransactionType(StrEnum):
    INCOME   = "INCOME"
    EXPENSES = "EXPENSES"
    TRANSFER = "TRANSFER"


class PaymentType(StrEnum):
    DINHEIRO       = "DINHEIRO"
    PIX            = "PIX"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO  = "CARTAO_DEBITO"
    BOLETO         = "BOLETO"
    OUTRO          = "OUTRO"


__all__ = ["PaymentType", "TransactionType"]
