from pydantic import BaseModel, Field

class AgentCardCapability(BaseModel):
    """Capabilities supported by the agent."""
    streaming: bool = True
    pushNotifications: bool = False
    stateTransitionHistory: bool = False

class AgentCardSkill(BaseModel):
    """Specific skill metadata for the agent."""
    id: str
    name: str
    description: str

class AgentCardAuthentication(BaseModel):
    """Authentication required to hit the agent."""
    schemes: list[str] = Field(default_factory=lambda: ["bearer"])

class AgentCard(BaseModel):
    """AgentCard schema compliant with A2A specification."""
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    skills: list[AgentCardSkill]
    defaultInputModes: list[str] = Field(default_factory=lambda: ["text/plain"])
    defaultOutputModes: list[str] = Field(default_factory=lambda: ["text/plain", "application/json"])
    capabilities: AgentCardCapability = Field(default_factory=AgentCardCapability)
    authentication: AgentCardAuthentication = Field(default_factory=AgentCardAuthentication)
