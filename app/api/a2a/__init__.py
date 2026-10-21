"""Protocolo A2A (Agent2Agent): o Assessor.AI como agente que outros agentes chamam. É mais uma porta de
entrada sobre `services/chat_service.py`, como as rotas HTTP e o MCP."""

from app.api.a2a.routes import montar_rotas

__all__ = ["montar_rotas"]
