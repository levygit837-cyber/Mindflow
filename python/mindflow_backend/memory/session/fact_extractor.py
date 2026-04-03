"""Session Fact Extractor - LLM-based extraction of structured facts from sessions.

This module provides intelligent fact extraction from conversation sessions using LLM analysis.
Unlike extractive methods (regex, keyword matching), this uses semantic understanding to
identify and consolidate key outcomes, decisions, and discoveries from entire sessions.
"""

from __future__ import annotations

import json
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.storage.models import SessionEmbedding, SessionFact
from mindflow_backend.runtime import get_model_for_provider
from mindflow_backend.schemas.core.common import LLMProvider

_logger = get_logger(__name__)

# Constants
MAX_MESSAGE_LENGTH = 2000
"""Maximum length for individual messages before truncation."""

MAX_EMBEDDING_CONTENT_LENGTH = 1500
"""Maximum content length for embedding storage."""

RESPONSE_PREVIEW_LENGTH = 200
"""Maximum length for response preview in error logs."""

VALID_FACT_TYPES = {"action", "decision", "discovery", "error", "state"}
"""Valid fact types that can be extracted."""

DEFAULT_IMPORTANCE = 0.5
"""Default importance score when not specified or invalid."""

MARKDOWN_JSON_PREFIX = "```json"
MARKDOWN_CODE_PREFIX = "```"
"""Markdown code block prefixes to strip from LLM responses."""


class SessionFactExtractor:
    """Extract structured facts from a session using LLM analysis.

    This extractor analyzes complete conversation sessions and identifies:
    - Actions taken (code changes, file modifications)
    - Decisions made (architecture choices, approach selections)
    - Discoveries (bugs found, patterns identified)
    - Errors encountered and their resolutions
    - Current state when session ended

    Facts are persisted with embeddings for semantic retrieval in future sessions.
    """

    EXTRACTION_PROMPT = """Analyze this conversation session and extract key facts.

For each fact, provide:
- type: Must be one of: "action", "decision", "discovery", "error", "state"
- content: Clear natural language description (1-3 sentences)
- category: Project area affected (e.g., "api", "auth", "database", "frontend", "tests")
- importance: Score from 0.0 to 1.0 (0.0=trivial, 0.5=moderate, 1.0=critical)
- related_files: List of file paths mentioned (empty list if none)

Return a JSON array of facts. Maximum 15 facts per session.

Focus on:
1. **Actions** - What was DONE: code changes, file modifications, implementations
2. **Decisions** - What was DECIDED: architecture choices, approach selections, trade-offs
3. **Discoveries** - What was DISCOVERED: bugs found, patterns identified, insights gained
4. **Errors** - What ERRORS occurred and how they were resolved
5. **State** - What STATE the work was in when the session ended (completed, in-progress, blocked)

Guidelines:
- Be specific and actionable
- Include file paths when mentioned
- Prioritize facts that would be useful in future sessions
- Consolidate related information into single facts
- Omit trivial or redundant information

Session messages:
{messages}

Return ONLY valid JSON array, no markdown formatting:
[
  {{
    "type": "action",
    "content": "Implemented JWT authentication middleware in api/middleware/auth.py with token validation and refresh logic",
    "category": "api",
    "importance": 0.9,
    "related_files": ["api/middleware/auth.py"]
  }},
  ...
]
"""

    def __init__(
        self,
        *,
        provider: LLMProvider | None = None,
        model: str | None = None,
        max_facts: int = 15,
    ) -> None:
        """Initialize fact extractor with LLM configuration.

        Args:
            provider: LLM provider to use (defaults to settings)
            model: Model name (defaults to settings)
            max_facts: Maximum facts to extract per session
        """
        self._settings = get_settings()
        self._provider = provider or self._settings.default_provider
        self._model = model or self._settings.default_model
        self._max_facts = max_facts

    async def extract(
        self,
        messages: list[dict[str, Any]],
        session_id: str,
        agent_id: str,
    ) -> list[SessionFact]:
        """Extract facts from session messages using LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            session_id: Session identifier
            agent_id: Agent identifier

        Returns:
            List of SessionFact instances (not yet persisted)
        """
        if not messages:
            _logger.debug("fact_extraction_skipped_empty", session_id=session_id)
            return []

        try:
            # Format messages for LLM
            messages_text = self._format_messages(messages)

            # Call LLM for fact extraction
            llm_response = await self._call_llm(messages_text)

            # Parse JSON response into SessionFact instances
            facts = self._parse_facts(llm_response, session_id, agent_id)

            _logger.info(
                "facts_extracted",
                session_id=session_id,
                agent_id=agent_id,
                fact_count=len(facts),
            )

            return facts[:self._max_facts]  # Enforce limit

        except Exception as exc:
            _logger.warning(
                "fact_extraction_failed",
                session_id=session_id,
                error=str(exc),
            )
            # Graceful degradation - return empty list instead of failing
            return []

    async def _call_llm(self, messages_text: str) -> str:
        """Call configured LLM provider for fact extraction.

        Args:
            messages_text: Formatted session messages

        Returns:
            LLM response text (expected to be JSON)

        Raises:
            Exception: If LLM call fails after retries
        """
        try:
            # Get LLM instance
            llm = get_model_for_provider(
                provider=self._provider,
                model=self._model,
            )

            # Build prompt
            prompt = self.EXTRACTION_PROMPT.format(messages=messages_text)

            # Call LLM
            messages = [
                {"role": "system", "content": "You are a precise fact extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ]

            response = await llm.ainvoke(messages)

            # Extract text content from response
            content = None
            if hasattr(response, "content"):
                content = response.content
            elif isinstance(response, dict) and "content" in response:
                content = response["content"]
            else:
                content = str(response)

            # Handle list content (some providers return list of content blocks)
            if isinstance(content, list):
                # Extract text from list of content blocks
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
                    elif isinstance(item, str):
                        text_parts.append(item)
                    else:
                        text_parts.append(str(item))
                return "".join(text_parts)

            return str(content)

        except Exception as exc:
            _logger.error("llm_call_failed", error=str(exc))
            raise

    def _format_messages(self, messages: list[dict[str, Any]]) -> str:
        """Format session messages for LLM prompt.

        Args:
            messages: List of message dicts

        Returns:
            Formatted text representation
        """
        formatted_lines = []

        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Truncate very long messages
            if len(content) > MAX_MESSAGE_LENGTH:
                content = content[:MAX_MESSAGE_LENGTH] + "... [truncated]"

            formatted_lines.append(f"[{i}] {role.upper()}: {content}")

        return "\n\n".join(formatted_lines)

    def _parse_facts(
        self,
        llm_response: str,
        session_id: str,
        agent_id: str,
    ) -> list[SessionFact]:
        """Parse LLM JSON response into SessionFact instances.

        Args:
            llm_response: LLM response text (expected JSON)
            session_id: Session identifier
            agent_id: Agent identifier

        Returns:
            List of SessionFact instances
        """
        try:
            # Clean response - remove markdown code blocks if present
            cleaned = llm_response.strip()
            if cleaned.startswith(MARKDOWN_JSON_PREFIX):
                cleaned = cleaned[len(MARKDOWN_JSON_PREFIX):]
            if cleaned.startswith(MARKDOWN_CODE_PREFIX):
                cleaned = cleaned[len(MARKDOWN_CODE_PREFIX):]
            if cleaned.endswith(MARKDOWN_CODE_PREFIX):
                cleaned = cleaned[:-len(MARKDOWN_CODE_PREFIX)]
            cleaned = cleaned.strip()

            # Extract JSON array - find first '[' and matching ']'
            start_idx = cleaned.find('[')
            if start_idx == -1:
                _logger.warning("no_json_array_found", response_preview=cleaned[:RESPONSE_PREVIEW_LENGTH])
                return []

            # Find matching closing bracket
            bracket_count = 0
            end_idx = -1
            for i in range(start_idx, len(cleaned)):
                if cleaned[i] == '[':
                    bracket_count += 1
                elif cleaned[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break

            if end_idx == -1:
                _logger.warning("no_matching_bracket", response_preview=cleaned[:RESPONSE_PREVIEW_LENGTH])
                return []

            # Extract only the JSON array part
            json_str = cleaned[start_idx:end_idx]

            # Parse JSON
            facts_data = json.loads(json_str)

            if not isinstance(facts_data, list):
                _logger.warning("llm_response_not_array", response_type=type(facts_data).__name__)
                return []

            # Convert to SessionFact instances
            facts = []
            for fact_dict in facts_data:
                try:
                    fact = self._dict_to_fact(fact_dict, session_id, agent_id)
                    if fact:
                        facts.append(fact)
                except Exception as exc:
                    _logger.debug("fact_parse_error", error=str(exc), fact_dict=fact_dict)
                    continue

            return facts

        except json.JSONDecodeError as exc:
            _logger.warning("json_parse_failed", error=str(exc), response_preview=llm_response[:RESPONSE_PREVIEW_LENGTH])
            return []
        except Exception as exc:
            _logger.warning("fact_parsing_failed", error=str(exc))
            return []

    def _dict_to_fact(
        self,
        fact_dict: dict[str, Any],
        session_id: str,
        agent_id: str,
    ) -> SessionFact | None:
        """Convert fact dictionary to SessionFact instance.

        Args:
            fact_dict: Fact data from LLM
            session_id: Session identifier
            agent_id: Agent identifier

        Returns:
            SessionFact instance or None if invalid
        """
        # Validate required fields
        fact_type = fact_dict.get("type")
        content = fact_dict.get("content")

        if not fact_type or not content:
            return None

        # Validate fact_type
        if fact_type not in VALID_FACT_TYPES:
            _logger.debug("invalid_fact_type", fact_type=fact_type)
            return None

        # Extract optional fields with defaults
        category = fact_dict.get("category")
        importance = fact_dict.get("importance", DEFAULT_IMPORTANCE)
        related_files = fact_dict.get("related_files", [])

        # Validate importance range
        try:
            importance = float(importance)
            importance = max(0.0, min(1.0, importance))  # Clamp to [0, 1]
        except (TypeError, ValueError):
            importance = DEFAULT_IMPORTANCE

        # Validate related_files is a list
        if not isinstance(related_files, list):
            related_files = []

        # Create SessionFact instance
        return SessionFact(
            session_id=session_id,
            agent_id=agent_id,
            fact_type=fact_type,
            content=content,
            category=category,
            importance=importance,
            related_files=related_files,
        )

    async def persist_facts(
        self,
        db: Any,
        facts: list[SessionFact],
        *,
        generate_embeddings: bool = True,
    ) -> int:
        """Persist facts with embeddings to database.

        Args:
            db: AsyncSession database connection
            facts: List of SessionFact instances to persist
            generate_embeddings: Whether to generate embeddings for facts

        Returns:
            Number of facts successfully persisted
        """
        if not facts:
            return 0

        persisted_count = 0

        try:
            for fact in facts:
                # Add fact to session
                db.add(fact)
                await db.flush()  # Get fact.id

                # Generate embedding if requested
                if generate_embeddings:
                    try:
                        embedding_vector = await self._generate_embedding(fact.content)

                        if embedding_vector:
                            session_embedding = SessionEmbedding(
                                session_id=fact.session_id,
                                agent_id=fact.agent_id,
                                content=fact.content[:MAX_EMBEDDING_CONTENT_LENGTH],
                                embedding=embedding_vector,
                                source_message_id=None,
                                content_kind="fact",
                                session_metadata={
                                    "source_type": "session_fact",
                                    "fact_type": fact.fact_type,
                                    "category": fact.category,
                                    "importance": fact.importance,
                                    "related_files": fact.related_files,
                                },
                            )
                            db.add(session_embedding)
                            await db.flush()

                            # Link embedding to fact
                            fact.embedding_id = session_embedding.id

                    except Exception as exc:
                        _logger.debug(
                            "embedding_generation_failed",
                            fact_id=fact.id,
                            error=str(exc),
                        )
                        # Continue without embedding - graceful degradation

                persisted_count += 1

            await db.commit()

            _logger.info(
                "facts_persisted",
                count=persisted_count,
                with_embeddings=generate_embeddings,
            )

            return persisted_count

        except Exception as exc:
            _logger.error("fact_persistence_failed", error=str(exc))
            await db.rollback()
            return 0

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if generation fails
        """
        try:
            from mindflow_backend.services.context.embedding_service import EmbeddingService

            embedding_service = EmbeddingService()
            vector = await embedding_service.generate_embedding(text)

            return vector

        except Exception as exc:
            _logger.debug("embedding_generation_error", error=str(exc))
            return None
