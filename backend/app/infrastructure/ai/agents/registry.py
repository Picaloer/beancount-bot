from app.infrastructure.ai.agents.base import AIAgent

_agents: dict[str, AIAgent] = {}


def register(agent: AIAgent) -> None:
    _agents[agent.agent_id] = agent


def get(agent_id: str) -> AIAgent:
    if agent_id not in _agents:
        raise KeyError(f"Agent not registered: {agent_id}")
    return _agents[agent_id]
