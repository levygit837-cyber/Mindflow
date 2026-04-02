"""
MemoryObserver — Agente em modo passivo que monitora missões e anota memória.

Ativado quando agente com can_observe=True conclui sua missão em uma TeamSession.
Nunca bloqueia execução — apenas escuta AgentLogBus e grava anotações significativas.

Fase 3B — SPADE Memory Observer Protocol
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from mindflow_backend.execution.observers.directory_mapper import DirectoryMapper
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.memory.annotation import (
    EVENT_IMPORTANCE_MAP,
    IMPORTANCE_THRESHOLDS,
    MemoryAnnotation,
)

if TYPE_CHECKING:
    from mindflow_backend.memory.facade import MemoryFacade

logger = get_logger(__name__)

ANNOTATION_RATE_LIMIT = 10
"""Máximo de anotações por minuto por observer."""


class MemoryObserver:
    """
    Monitor passivo que anota memória durante execução de outros agentes.

    Roda em background (asyncio task).
    Nunca bloqueia o agente sendo observado.
    Filtro de importância: só anota eventos com score >= threshold.
    """

    def __init__(
        self,
        observer_agent_id: str,
        memory_facade: "MemoryFacade",
        session_id: str,
        project_root: str | None = None,
        project_name: str | None = None,
    ) -> None:
        self._observer_id = observer_agent_id
        self._memory = memory_facade
        self._session_id = session_id
        self._running = False
        self._task: asyncio.Task | None = None
        self._annotations_count = 0
        self._annotations_this_minute = 0
        self._observed_missions: set[str] = set()
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=500)

        # Phase 2: Directory-aware categorization
        self._directory_mapper: DirectoryMapper | None = None
        self._project_root = project_root
        self._project_name = project_name or "Unknown"
        if project_root:
            self._directory_mapper = DirectoryMapper(project_root)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start_observing(self, mission_ids: list[str]) -> None:
        """
        Inicia observação em background de uma ou mais missões.

        Retorna imediatamente — observação ocorre em asyncio Task separada.
        """
        self._observed_missions.update(mission_ids)
        self._running = True
        self._task = asyncio.create_task(
            self._observation_loop(),
            name=f"observer_{self._observer_id}",
        )
        logger.info(
            "observer_started",
            extra={
                "observer": self._observer_id,
                "missions": mission_ids,
            },
        )

    async def stop_observing(self) -> None:
        """Para a observação gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(
            "observer_stopped",
            extra={
                "observer": self._observer_id,
                "total_annotations": self._annotations_count,
            },
        )

    # ------------------------------------------------------------------
    # Event reception
    # ------------------------------------------------------------------

    async def receive_event(self, event: dict[str, Any]) -> None:
        """
        Recebe evento do AgentLogBus.

        Chamado pelo AgentLogBus quando há evento nas missões observadas.
        Enfileira para processamento assíncrono.
        """
        if not self._running:
            return
        try:
            self._event_queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.debug("observer_queue_full", extra={"observer": self._observer_id})

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _observation_loop(self) -> None:
        """Loop principal de processamento de eventos."""
        rate_limit_reset_task = asyncio.create_task(
            self._rate_limit_reset_loop(),
            name=f"observer_ratereset_{self._observer_id}",
        )

        try:
            while self._running:
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=1.0,
                    )
                    await self._process_event(event)
                except TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.debug(
                        "observer_event_error",
                        extra={"observer": self._observer_id, "error": str(exc)},
                    )
        finally:
            rate_limit_reset_task.cancel()
            try:
                await rate_limit_reset_task
            except asyncio.CancelledError:
                pass

    async def _process_event(self, event: dict[str, Any]) -> None:
        """Processa um evento e anota memória se relevante.

        Phase 2: Detecta code changes e usa DirectoryMapper para categorização automática.
        """
        # Rate limiting
        if self._annotations_this_minute >= ANNOTATION_RATE_LIMIT:
            return

        importance = self._score_importance(event)
        if importance < 0.3:
            return

        annotation_type = self._classify_event(event)
        threshold = IMPORTANCE_THRESHOLDS.get(annotation_type, 0.3)
        if importance < threshold:
            return

        # Phase 2: Detectar code changes
        code_change_info = self._extract_code_change(event)

        if code_change_info and self._directory_mapper:
            # Code change detectado - usar contexto rico e categorização automática
            content = self._generate_rich_context(event, code_change_info)
            category, subcategory = self._directory_mapper.categorize_file(
                code_change_info["file_path"]
            )

            # Adicionar tags de categoria
            tags = self._extract_tags(event)
            tags.extend([category.lower(), subcategory.lower() if subcategory else ""])
            tags = [t for t in tags if t]  # Remove empty strings

            annotation = MemoryAnnotation(
                observer_agent_id=self._observer_id,
                source_agent_id=event.get("agent_id", ""),
                mission_id=event.get("mission_id", ""),
                session_id=self._session_id,
                content=content,
                raw_event_type=event.get("type", ""),
                importance=importance,
                annotation_type="code_change",
                tags=tags,
            )
        else:
            # Evento normal - usar summarize_event
            content = self._summarize_event(event)
            if not content:
                return

            annotation = MemoryAnnotation(
                observer_agent_id=self._observer_id,
                source_agent_id=event.get("agent_id", ""),
                mission_id=event.get("mission_id", ""),
                session_id=self._session_id,
                content=content,
                raw_event_type=event.get("type", ""),
                importance=importance,
                annotation_type=annotation_type,
                tags=self._extract_tags(event),
            )

        if not annotation.is_significant():
            return

        try:
            await self._save_annotation(
                annotation,
                code_change_info=code_change_info,
                category=category if code_change_info and self._directory_mapper else None,
                subcategory=subcategory if code_change_info and self._directory_mapper else None,
            )
            self._annotations_count += 1
            self._annotations_this_minute += 1
            logger.debug(
                "observer_annotated",
                extra={
                    "observer": self._observer_id,
                    "type": annotation.annotation_type,
                    "importance": importance,
                    "code_change": code_change_info is not None,
                },
            )
        except Exception as exc:
            logger.debug(
                "observer_save_failed",
                extra={"observer": self._observer_id, "error": str(exc)},
            )

    # ------------------------------------------------------------------
    # Scoring and classification
    # ------------------------------------------------------------------

    @staticmethod
    def _score_importance(event: dict[str, Any]) -> float:
        """Calcula score de importância do evento (0.0–1.0)."""
        event_type = event.get("type", "")
        level = event.get("level", "INFO")

        base_score = EVENT_IMPORTANCE_MAP.get(event_type, 0.2)

        # Boosts por nível
        if level == "ERROR":
            base_score = max(base_score, 0.9)
        elif level == "WARNING":
            base_score = max(base_score, 0.7)

        # Eventos tardios têm menos novidade
        if event.get("iteration", 1) > 10:
            base_score *= 0.8

        return min(base_score, 1.0)

    @staticmethod
    def _classify_event(event: dict[str, Any]) -> str:
        """Classifica evento em tipo de anotação."""
        event_type = event.get("type", "")
        level = event.get("level", "INFO")

        if level in ("ERROR", "WARNING"):
            return "warning"
        if event_type in ("agent_decision", "finding"):
            return "finding"
        if event_type == "mission_complete":
            return "insight"
        return "observation"

    @staticmethod
    def _summarize_event(event: dict[str, Any]) -> str:
        """Gera resumo textual do evento para memória."""
        agent_id = event.get("agent_id", "unknown")
        event_type = event.get("type", "event")
        message = event.get("message", "")
        data = event.get("data", {})

        if not message and not data:
            return ""

        summary = f"{agent_id} [{event_type}]: {message}"
        if data and isinstance(data, dict):
            key_data = {
                k: v
                for k, v in data.items()
                if k in ("result", "finding", "error", "file", "pattern")
            }
            if key_data:
                summary += f" | {key_data}"

        return summary[:500]  # Máximo 500 chars por anotação

    @staticmethod
    def _extract_tags(event: dict[str, Any]) -> list[str]:
        """Extrai tags do evento para classificação."""
        tags: list[str] = []
        if event.get("type"):
            tags.append(f"event:{event['type']}")
        if event.get("agent_id"):
            tags.append(f"agent:{event['agent_id']}")
        if event.get("level") in ("ERROR", "WARNING"):
            tags.append(event["level"].lower())
        return tags

    # ------------------------------------------------------------------
    # Phase 2: Code change detection
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_code_change(event: dict[str, Any]) -> dict[str, Any] | None:
        """Extrai informações de code change do evento.

        Detecta tool_result events de file operations (write_file, edit_file, etc.)
        e extrai file_path, lines_modified, diff.

        Returns:
            Dict com file_path, lines, diff, operation ou None se não for code change
        """
        event_type = event.get("type", "")
        data = event.get("data", {})

        # Detectar tool_result de file operations
        if event_type == "tool_result":
            tool_name = data.get("tool_name", "")

            if tool_name in ("write_file", "edit_file", "replace_in_file", "create_file"):
                file_path = data.get("file_path") or data.get("path") or data.get("file")
                if not file_path:
                    return None

                return {
                    "file_path": str(file_path),
                    "lines": data.get("lines_modified", {}),
                    "diff": data.get("diff", ""),
                    "operation": tool_name,
                }

        # Detectar eventos de file_written, file_modified
        if event_type in ("file_written", "file_modified", "file_created"):
            file_path = data.get("file_path") or data.get("path")
            if not file_path:
                return None

            return {
                "file_path": str(file_path),
                "lines": data.get("lines_modified", {}),
                "diff": data.get("diff", ""),
                "operation": event_type,
            }

        return None

    def _generate_rich_context(self, event: dict[str, Any], code_info: dict[str, Any]) -> str:
        """Gera contexto RICO em linguagem natural (sem limite de 500 chars).

        Args:
            event: Evento original
            code_info: Informações de code change extraídas

        Returns:
            Descrição detalhada em linguagem natural
        """
        agent = event.get("agent_id", "unknown")
        file_path = code_info["file_path"]
        lines = code_info.get("lines", {})
        operation = code_info.get("operation", "modified")
        message = event.get("message", "")
        diff = code_info.get("diff", "")

        # Categorizar automaticamente se DirectoryMapper disponível
        category_info = ""
        if self._directory_mapper:
            category, subcategory = self._directory_mapper.categorize_file(file_path)
            category_info = f"\nCategory: {category}"
            if subcategory:
                category_info += f" > {subcategory}"

        # Formatar lines_modified
        lines_info = ""
        if lines:
            start = lines.get("start", "?")
            end = lines.get("end", "?")
            change_type = lines.get("type", "modified")
            lines_info = f"\nLines {change_type}: {start}-{end}"

        # Formatar diff preview
        diff_preview = ""
        if diff:
            diff_preview = f"\n\nDiff preview:\n```\n{diff[:500]}\n```"

        context = f"""Agent {agent} {operation} file: {file_path}{category_info}{lines_info}

Change summary:
{message or 'No description provided'}
{diff_preview}

Context: This change was made during mission {event.get('mission_id')} in session {self._session_id}.
"""
        return context.strip()

    # ------------------------------------------------------------------
    # Memory save
    # ------------------------------------------------------------------

    async def _save_annotation(
        self,
        annotation: MemoryAnnotation,
        code_change_info: dict[str, Any] | None = None,
        category: str | None = None,
        subcategory: str | None = None,
    ) -> None:
        """Salva anotação via MemoryFacade.

        Phase 3: Usa save_hierarchical_annotation quando code_change_info existe.
        """
        # Phase 3: Salvamento hierárquico para code changes
        if code_change_info and self._project_root and hasattr(self._memory, "save_hierarchical_annotation"):
            from mindflow_backend.infra.database.connection import get_db_session

            async with get_db_session() as db:
                await self._memory.save_hierarchical_annotation(
                    db,
                    annotation=annotation,
                    project_name=self._project_name,
                    project_root=self._project_root,
                    category_name=category,
                    subcategory_name=subcategory,
                    file_path=code_change_info.get("file_path"),
                    lines_modified=code_change_info.get("lines"),
                    diff_summary=code_change_info.get("diff", "")[:1000],  # Limit to 1000 chars
                )
                await db.commit()
            return

        # Fallback: método antigo (save_annotation ou record_message)
        if hasattr(self._memory, "save_annotation"):
            await self._memory.save_annotation(annotation)
        else:
            # Último fallback: apenas log
            logger.debug(
                "observer_annotation_not_saved",
                extra={
                    "observer": self._observer_id,
                    "reason": "no_save_method_available",
                },
            )

    # ------------------------------------------------------------------
    # Rate limit reset
    # ------------------------------------------------------------------

    async def _rate_limit_reset_loop(self) -> None:
        """Reseta contador de rate limit a cada 60s."""
        while True:
            await asyncio.sleep(60)
            self._annotations_this_minute = 0

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Retorna estatísticas do observer."""
        return {
            "observer_id": self._observer_id,
            "running": self._running,
            "total_annotations": self._annotations_count,
            "rate_this_minute": self._annotations_this_minute,
            "observed_missions": sorted(self._observed_missions),
        }