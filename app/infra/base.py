"""
Contrato mínimo das conexões de infra: `conectar()` inicializa lazy e devolve o client/engine.
Sem `executar()`/`fechar()` genérico de propósito — ORM, driver de documento e client key-value
não compartilham API de operação; cada `*Conn` continua expondo seus próprios métodos.
"""

from abc import ABC, abstractmethod


class Conector[T](ABC):
    @abstractmethod
    def conectar(self) -> T: ...


__all__ = ["Conector"]
