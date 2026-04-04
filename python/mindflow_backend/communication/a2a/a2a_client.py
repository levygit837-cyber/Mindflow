import httpx
from mindflow_backend.schemas.orchestration.delegation import DelegationTask, DelegationResult
from mindflow_backend.schemas.a2a.task import A2AMessage, TextPart
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

class A2AClient:
    """Client for calling external A2A agents from MindFlow DelegationEngine."""
    
    @staticmethod
    async def call_external_agent(task: DelegationTask, target_url: str) -> DelegationResult:
        """
        Translates a DelegationTask into an A2AMessage, sends it to the target A2A URL,
        and translates the resulting A2AArtifact back into a DelegationResult.
        """
        # Convert internal DelegationTask -> A2AMessage payload
        parts = [TextPart(text=task.objective)]
        
        if task.context_from_session:
            parts.append(TextPart(text=f"PREVIOUS CONTEXT:\n{task.context_from_session}"))

        message = A2AMessage(
            role="user",
            context_id=f"mindflow_{str(task.task_id)}",
            target_agent=task.agent_id or task.agent.value,
            parts=parts
        )
        
        _logger.info("a2a_client_dispatching_task", target_url=target_url, task_id=str(task.task_id))

        try:
            # 5-minute timeout for agent processing
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Se o target_url já apontar para /a2a/tasks/send, usamos direto
                endpoint = target_url
                if not target_url.endswith("/tasks/send"):
                    endpoint = f"{target_url.rstrip('/')}/a2a/tasks/send"

                res = await client.post(endpoint, json=message.model_dump())
                res.raise_for_status()
                
                artifact_data = res.json()
                
                # Convert the returned A2A Artifact generic parts -> DelegationResult
                full_text = ""
                for part in artifact_data.get("parts", []):
                    if part.get("type") == "text":
                        full_text += part.get("text", "") + "\n"

                return DelegationResult(
                    task_id=task.task_id,
                    agent=task.agent,
                    agent_id=target_url,
                    status="completed",
                    key_findings=full_text[:500] if len(full_text) > 500 else full_text,
                    full_output=full_text,
                    confidence=0.8,
                    tokens_consumed=0
                )
                
        except Exception as e:
            _logger.error("a2a_client_call_failed", target_url=target_url, error=str(e))
            return DelegationResult(
                task_id=task.task_id,
                agent=task.agent,
                agent_id=target_url,
                status="failed",
                key_findings="",
                full_output="",
                confidence=0.0,
                tokens_consumed=0,
                error_message=str(e)
            )
