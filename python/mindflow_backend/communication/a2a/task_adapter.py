import uuid
from typing import Any
from mindflow_backend.schemas.a2a.task import A2AMessage, A2AArtifact, TextPart, DataPart
from mindflow_backend.schemas.orchestration.delegation import DelegationTask, DelegationResult
from mindflow_backend.schemas.orchestration.orchestrator import AgentType

class TaskAdapter:
    """Adapter between A2A Task objects and MindFlow internal Delegation objects."""
    
    @staticmethod
    def a2a_task_to_delegation_task(a2a_message: A2AMessage) -> DelegationTask:
        # Pega a parte do texto como o objetivo principal
        objective = ""
        for part in a2a_message.parts:
            if part.type == "text":
                objective += getattr(part, 'text', '') + "\n"
        
        # Pega a identificação do agente ou define como orchestrator fallback
        target_agent = a2a_message.target_agent or "orchestrator"
        
        # Faz parsing do AgentType
        try:
            agent_type = AgentType(target_agent.split(":")[0])
        except ValueError:
            agent_type = AgentType.ORCHESTRATOR
            
        return DelegationTask(
            task_id=uuid.uuid4(),
            agent=agent_type,
            agent_id=target_agent,
            objective=objective.strip(),
            session_id=a2a_message.context_id
        )

    @staticmethod
    def delegation_result_to_a2a_artifact(result: DelegationResult) -> A2AArtifact:
        return A2AArtifact(
            parts=[
                TextPart(text=result.key_findings),
                DataPart(data={
                    "full_output": result.full_output,
                    "confidence": result.confidence,
                    "tokens_consumed": result.tokens_consumed,
                    "files_analyzed": result.files_analyzed,
                    "symbols_found": result.symbols_found,
                    "error_message": result.error_message
                })
            ]
        )
