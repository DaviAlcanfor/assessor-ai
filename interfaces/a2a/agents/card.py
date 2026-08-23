from importlib.metadata import version

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentProvider

from config.settings import settings
from interfaces.a2a.agents.capabilites import SKILLS

AGENT_CARD = AgentCard(
    name="Assessor AI",
    description=(
        "Assistente pessoal de finanças e agenda, construído com LangChain/LangGraph."
    ),
    version=version("assessor-ai"),
    provider=AgentProvider(organization="Assessor AI"),
    supported_interfaces=[
        AgentInterface(
            url=f"{settings.A2A_BASE_URL}/a2a",
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        ),
    ],
    capabilities=AgentCapabilities(streaming=False, push_notifications=False),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=SKILLS,
)
