from typing import List
from mindflow_backend.schemas.a2a.agent_card import AgentCard, AgentCardSkill
from mindflow_backend.agents.specialists.runtime_policy import list_agent_runtime_policies

class AgentCardRegistry:
    """Registry to expose MindFlow agents as A2A AgentCards."""
    
    @classmethod
    def get_agent_cards(cls) -> List[AgentCard]:
        policies = list_agent_runtime_policies()
        cards = []
        
        for policy in policies:
            agent_id = policy.agent_id
            
            # Specialized mapping for A2A compliance
            name = f"MindFlow {agent_id.title()}"
            description = policy.summary or f"Specialized AI Agent with {policy.comm_role.value} role"
            
            if agent_id == "analyst":
                name = "MindFlow Strategic Analyst"
                description = "Expert in codebase analysis, architectural review, and strategic planning. Can analyze complex patterns and provide deep insights."
            elif agent_id == "coder":
                name = "MindFlow Senior Software Engineer"
                description = "Specialized in code generation, refactoring, and debugging. Proficient in multiple languages and frameworks with filesystem access."
            elif agent_id == "orchestrator":
                name = "MindFlow Meta-Orchestrator"
                description = "Central gateway for agent coordination, task decomposition, and multi-agent collaborative session management."

            # Map skills from MissionType or Policy Summary
            skills = []
            if policy.mission_types:
                for m_type in policy.mission_types:
                    skills.append(
                        AgentCardSkill(
                            id=f"{agent_id}:{m_type}", 
                            name=m_type.title().replace("_", " "), 
                            description=f"Advanced capability in {m_type.replace('_', ' ')} operations."
                        )
                    )
            else:
                # Fallback skill for agents without explicit mission types
                skills.append(
                    AgentCardSkill(
                        id=f"{agent_id}:general",
                        name="General Problem Solving",
                        description=f"General capabilities as a {agent_id} specialized agent."
                    )
                )

            # In production, this would be the public URL
            agent_url = f"http://mindflow-gateway.local/a2a/tasks/{agent_id}"

            card = AgentCard(
                name=name,
                description=description,
                url=agent_url,
                skills=skills
            )
            cards.append(card)
            
        return cards
