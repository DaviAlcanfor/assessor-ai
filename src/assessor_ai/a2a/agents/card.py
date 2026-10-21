from importlib.metadata import version

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentProvider

from assessor_ai.a2a.agents.capabilites import SKILLS
from assessor_ai.settings import settings

AGENT_CARD = AgentCard(
    name="Assessor AI",
    description=(
        "Assistente pessoal de finanças e agenda, construído com LangChain/LangGraph."
    ),
    version=version("assessor-ai"),
    provider=AgentProvider(organization="Assessor AI"),
    supported_interfaces=[
        AgentInterface(
            url=f"{settings.api.a2a_base_url}/a2a",
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        ),
    ],
    capabilities=AgentCapabilities(streaming=False, push_notifications=False),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=SKILLS,
)
