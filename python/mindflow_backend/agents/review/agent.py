"""Minimal session review agent used by the queue rollout."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from mindflow_backend.schemas.session.review import (
    ReviewPriority,
    ReviewTask,
    ReviewExecutionContext,
    SessionReviewResult,
)


@dataclass(slots=True)
class _SessionReviewAgentConfig:
    capabilities: list[str] = field(
        default_factory=lambda: [
            "session_review",
            "context_summarization",
            "action_extraction",
            "insight_extraction",
        ]
    )


class SessionReviewAgentImplementation:
    """Deterministic review agent used until the dedicated agent is restored."""

    def __init__(self) -> None:
        self.agent_config = _SessionReviewAgentConfig()

    async def review_session_window(
        self,
        task: ReviewTask,
        context: ReviewExecutionContext,
        review_type: str = "comprehensive",
        **_: object,
    ) -> SessionReviewResult:
        messages = context.session_messages
        actions_documented = self._extract_actions(messages)
        insights_extracted = self._extract_insights(messages, task)
        summary_text = self._build_summary(messages, task, review_type)

        return SessionReviewResult(
            session_id=task.session_id,
            window_range=task.window_range,
            priority=task.priority if isinstance(task.priority, ReviewPriority) else ReviewPriority.MEDIUM,
            summary_text=summary_text,
            actions_documented=actions_documented,
            insights_extracted=insights_extracted,
            review_data={
                "review_type": review_type,
                "message_count": len(messages),
                "window_index": task.window_index,
                "summary_text": summary_text,
                "actions_documented": actions_documented,
                "insights_extracted": insights_extracted,
            },
        )

    def _extract_actions(self, messages: list[dict[str, object]]) -> list[str]:
        actions: list[str] = []
        for message in messages:
            role = str(message.get("role", "unknown"))
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            snippet = " ".join(content.split())[:120]
            actions.append(f"{role}: {snippet}")
            if len(actions) == 5:
                break
        return actions

    def _extract_insights(self, messages: list[dict[str, object]], task: ReviewTask) -> list[str]:
        insights = [
            f"Window {task.window_index} cobre {len(messages)} mensagens.",
            f"Faixa analisada: {task.window_range[0]}-{task.window_range[1]} tokens.",
        ]
        if any(str(message.get("role")) == "assistant" for message in messages):
            insights.append("A janela contém respostas do agente que podem ser consolidadas.")
        if any(str(message.get("role")) == "user" for message in messages):
            insights.append("A janela contém intenção explícita do usuário para contexto futuro.")
        return insights

    def _build_summary(
        self,
        messages: list[dict[str, object]],
        task: ReviewTask,
        review_type: str,
    ) -> str:
        if not messages:
            return (
                f"Review {review_type} executado para a janela {task.window_index}, "
                "sem mensagens disponíveis para consolidação."
            )

        return (
            f"Review {review_type} executado para a janela {task.window_index} "
            f"com {len(messages)} mensagens analisadas."
        )


@lru_cache(maxsize=1)
def get_session_review_agent() -> SessionReviewAgentImplementation:
    """Return the singleton session review agent implementation."""

    return SessionReviewAgentImplementation()
