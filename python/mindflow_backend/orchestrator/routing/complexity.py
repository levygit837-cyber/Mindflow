from __future__ import annotations

import re
from typing import Any

from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.runtime.chunk_extract import extract_chunk_parts
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ComplexityScorer:
    """Heuristic + LLM based task complexity assessment."""

    COMPLEXITY_KEYWORDS = [
        "refactor", "implement", "fix", "create new", "add feature",
        "multiple files", "entire project", "rewrite", "migration",
        "arquitetura", "refatorar", "implementar", "corrigir"
    ]

    def __init__(self, threshold: float = 0.65):
        self.threshold = threshold

    def calculate_heuristic_score(self, message: str) -> float:
        """Quick heuristic-based complexity score."""
        score = 0.0
        
        # 1. Message length (max 0.3)
        length_score = min(len(message) / 1000, 0.3)
        score += length_score
        
        # 2. Keyword density (max 0.4)
        matches = [kw for kw in self.COMPLEXITY_KEYWORDS if re.search(rf"\b{kw}\b", message.lower())]
        keyword_score = min(len(matches) * 0.1, 0.4)
        score += keyword_score
        
        # 3. Code block detection (max 0.2)
        if "```" in message:
            score += 0.2
            
        return round(score, 2)

    async def get_complexity_score(self, message: str, provider: str | None = None, model: str | None = None) -> float:
        """Assess task complexity using heuristics and optionally an LLM."""
        h_score = self.calculate_heuristic_score(message)
        
        # If heuristic is very high or very low, we might skip LLM to save time/cost
        if h_score >= 0.8:
            return h_score
        if h_score <= 0.2 and len(message) < 50:
            return h_score

        # LLM validation (Phase 3 requirement)
        try:
            settings = get_settings()
            p = provider or settings.default_provider
            m = model or settings.default_model
            llm = get_model_for_provider(p, m)
            
            prompt = (
                "Rate the technical complexity of the following user request from 0.0 to 1.0. "
                "0.0 means trivial/simple question, 1.0 means complex project-wide refactoring or implementation. "
                "Output ONLY the numeric score.\n\n"
                f"Request: {message}"
            )
            
            response = await llm.ainvoke(prompt)
            thought, text_parts = extract_chunk_parts(response)
            content = " ".join(text_parts).strip()
            if not content:
                content = thought
            if not content:
                content = str(getattr(response, "content", response))
            
            # Extract number from response
            match = re.search(r"(\d+\.\d+|\d+)", content)
            if match:
                llm_score = float(match.group(1))
                # Weighted average: 30% heuristic, 70% LLM
                final_score = (h_score * 0.3) + (llm_score * 0.7)
                return round(final_score, 2)
                
        except Exception as e:
            _logger.error("llm_complexity_scoring_error", error=str(e))
            
        return h_score

    def should_decompose(self, score: float) -> bool:
        """Determine if a task should be decomposed based on the complexity score."""
        return score >= self.threshold
