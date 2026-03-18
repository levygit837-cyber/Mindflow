"""Intelligent planning trigger using LLM-based semantic analysis.

This module replaces keyword-based planning triggers with semantic understanding,
allowing the system to intelligently determine when a user request requires
decomposition into a structured TODO-list.
"""

from __future__ import annotations

import json
import re
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime import get_model_for_provider, normalize_response_for_json
from mindflow_backend.schemas.orchestration.planning import (
    PlanningAnalysisRequest,
    PlanningDecision,
)

_logger = get_logger(__name__)


class IntelligentPlanningAnalyzer:
    """LLM-powered analyzer to determine if a request needs planning/TODO-list.
    
    This analyzer uses semantic understanding rather than keyword matching to
    detect when a user request requires decomposition into multiple subtasks.
    
    Features:
    - Semantic intent analysis via LLM
    - Structural feature extraction for fallback
    - Confidence scoring
    - Reasoning transparency
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    async def should_trigger_planning(
        self,
        request: PlanningAnalysisRequest,
    ) -> PlanningDecision:
        """Analyze request and decide if planning is needed.
        
        Args:
            request: Analysis request with message and context
            
        Returns:
            PlanningDecision with requires_planning flag and reasoning
        """
        from mindflow_backend.orchestrator.planning.cache import get_decision_cache
        
        # Check cache first
        cache = get_decision_cache()
        cached_decision = cache.get(request.message)
        if cached_decision is not None:
            _logger.info("planning_decision_from_cache", confidence=cached_decision.confidence)
            return cached_decision
        
        # Extract structural features for fallback
        features = self._extract_structural_features(request.message)
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(request, features)
        
        # Call LLM
        try:
            decision = await self._call_llm(prompt)
            
            _logger.info(
                "planning_decision",
                requires_planning=decision.requires_planning,
                confidence=decision.confidence,
                reasoning=decision.reasoning[:100],
            )
            
            # Cache the decision
            cache.set(request.message, decision)
            
            return decision
            
        except Exception as exc:
            _logger.error("planning_analysis_failed", error=str(exc))
            # Fallback: use structural heuristics
            return self._fallback_decision(features)
    
    async def _call_llm(self, prompt: str) -> PlanningDecision:
        """Call LLM to analyze planning need."""
        
        llm = get_model_for_provider(
            self.settings.default_provider,
            self.settings.default_model,
        )
        
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt(),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]
        
        response = await llm.ainvoke(messages)
        
        # Extract content
        if hasattr(response, "content"):
            content = response.content
        else:
            content = str(response)
        
        # Normalize and parse JSON
        content = normalize_response_for_json(content)
        
        # Try to parse JSON
        try:
            decision_data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                decision_data = json.loads(json_match.group(1))
            else:
                # Try to find any JSON object
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    decision_data = json.loads(json_match.group(0))
                else:
                    raise
        
        return PlanningDecision.model_validate(decision_data)
    
    def _extract_structural_features(self, message: str) -> dict[str, Any]:
        """Extract structural features from message for fallback logic.
        
        These features are used when LLM is unavailable or as additional
        signals for the decision.
        """
        return {
            "message_length": len(message),
            "word_count": len(message.split()),
            "has_code_blocks": "```" in message,
            "has_file_paths": bool(re.search(r"[\w/]+\.\w{2,4}", message)),
            "has_multiple_sentences": message.count(".") + message.count("?") > 2,
            "has_list_markers": bool(re.search(r"^[\s]*[\d\-\*•]\s", message, re.MULTILINE)),
            "question_count": message.count("?"),
        }
    
    def _get_system_prompt(self) -> str:
        """System prompt for planning analysis."""
        return """You are the MindFlow Planning Analyzer. Your job is to determine if a user request requires decomposition into a structured TODO-list with multiple subtasks.

## When Planning IS Needed

Planning is needed when the request involves:

1. **Multi-step implementation**:
   - "Implementar sistema de autenticação JWT"
   - "Criar API REST completa para gerenciar produtos"
   - "Migrar banco de dados de MySQL para PostgreSQL"

2. **Multiple files/components**:
   - "Refatorar a camada de serviços e repositórios"
   - "Adicionar testes para todos os endpoints"
   - "Criar feature completa de notificações (backend + frontend)"

3. **Complex refactoring**:
   - "Reorganizar estrutura de pastas do projeto"
   - "Aplicar padrão Repository em toda a codebase"
   - "Migrar de REST para GraphQL"

4. **Architecture/design work**:
   - "Desenhar arquitetura de microserviços"
   - "Planejar sistema de cache distribuído"
   - "Estruturar módulos do sistema"

5. **Explicit planning request**:
   - "Crie um plano para..."
   - "Quero planejar a implementação de..."
   - "Me ajude a estruturar as etapas para..."

## When Planning is NOT Needed

Planning is NOT needed for:

1. **Single-file changes**:
   - "Adiciona validação de email neste arquivo"
   - "Corrige o bug na função X"
   - "Renomeia variável Y para Z"

2. **Questions/explanations**:
   - "Como funciona o sistema de autenticação?"
   - "Explica o que faz esta função"
   - "Qual a diferença entre X e Y?"

3. **Simple research**:
   - "Pesquisa sobre FastAPI"
   - "Busca documentação do LangGraph"

4. **Quick fixes**:
   - "Remove console.log"
   - "Formata este código"
   - "Adiciona type hints"

5. **Greetings/meta**:
   - "Olá"
   - "Como você está?"
   - "Obrigado"

## Response Format

Return ONLY valid JSON (no markdown):

{
  "requires_planning": true,
  "confidence": 0.85,
  "reasoning": "Multi-step implementation requiring authentication flow, token management, and refresh logic across multiple files",
  "estimated_subtasks": 6,
  "complexity_factors": ["security", "state_management", "multi-file"],
  "suggested_work_type": "feature"
}

## Confidence Guidelines

- 0.9-1.0: Extremely clear (explicit planning request or obvious multi-step work)
- 0.7-0.9: High confidence (clear multi-component work)
- 0.5-0.7: Moderate (could go either way, lean towards structural features)
- 0.3-0.5: Low confidence (probably doesn't need planning)
- 0.0-0.3: Very unlikely to need planning

If confidence < 0.6, set requires_planning = false unless there are strong structural indicators."""
    
    def _build_analysis_prompt(
        self,
        request: PlanningAnalysisRequest,
        features: dict[str, Any],
    ) -> str:
        """Build the analysis prompt with context."""
        
        context_section = ""
        if request.session_context:
            context_section = f"\n\n## Session Context\n{request.session_context[:500]}"
        
        history_section = ""
        if request.conversation_history:
            recent = request.conversation_history[-3:]
            history_section = "\n\n## Recent Conversation\n" + "\n".join(
                f"- {msg['role']}: {msg['content'][:100]}"
                for msg in recent
            )
        
        features_section = f"""

## Structural Features (for reference)
- Message length: {features['word_count']} words
- Has code blocks: {features['has_code_blocks']}
- Has file paths: {features['has_file_paths']}
- Has list markers: {features['has_list_markers']}
- Question count: {features['question_count']}
"""
        
        return f"""## User Request

{request.message}
{context_section}
{history_section}
{features_section}

Analyze this request and determine if it requires planning/TODO-list decomposition."""
    
    def _fallback_decision(self, features: dict[str, Any]) -> PlanningDecision:
        """Fallback heuristic-based decision if LLM fails.
        
        Uses structural features to make a conservative decision about
        whether planning is needed.
        """
        
        # Simple heuristic: long message + multiple sentences + file paths = likely needs planning
        score = 0.0
        factors = []
        
        if features["word_count"] > 50:
            score += 0.2
            factors.append("long_message")
        
        if features["has_multiple_sentences"]:
            score += 0.2
            factors.append("multi_sentence")
        
        if features["has_file_paths"]:
            score += 0.15
            factors.append("file_paths")
        
        if features["has_list_markers"]:
            score += 0.25
            factors.append("list_structure")
        
        if features["has_code_blocks"]:
            score += 0.1
            factors.append("code_blocks")
        
        requires_planning = score >= 0.5
        
        return PlanningDecision(
            requires_planning=requires_planning,
            confidence=min(score, 0.6),  # Cap at 0.6 for fallback
            reasoning="Fallback heuristic decision (LLM unavailable)",
            estimated_subtasks=3 if requires_planning else 0,
            complexity_factors=factors + ["fallback_mode"],
            suggested_work_type="unknown",
        )


# Singleton instance
_analyzer: IntelligentPlanningAnalyzer | None = None


def get_planning_analyzer() -> IntelligentPlanningAnalyzer:
    """Get or create the global planning analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = IntelligentPlanningAnalyzer()
    return _analyzer
