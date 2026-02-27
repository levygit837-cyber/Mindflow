import os
import re
import uuid
from pathlib import Path

from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from omnimind_backend.mind.supervisor import session_supervisor
from omnimind_backend.schemas.agent import MindSandboxQueryRequest, MindSandboxQueryResponse
from omnimind_backend.storage.models import Conversation, Message
from omnimind_backend.storage.repositories import MindRepository, NeuralRepository, SessionRepository


SUPPORTED_TOOLS = {
    "Read",
    "Search_Function",
    "Search_code",
    "callSupervisor",
    "context_analysis",
    "context_tree",
    "create_neural",
    "call_analyst",
    "delete_session",
}


def _collect_messages(session: Session, session_ids: list[str]) -> dict[str, list[Message]]:
    out: dict[str, list[Message]] = {}
    for session_id in session_ids:
        rows = session.scalars(
            select(Message)
            .where(Message.conversation_id == session_id)
            .order_by(asc(Message.created_at))
        ).all()
        out[session_id] = rows
    return out


def _shorten(text: str, limit: int = 220) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


class MindSandboxService:
    def __init__(self) -> None:
        self._session_repository = SessionRepository()
        self._mind_repository = MindRepository()
        self._neural_repository = NeuralRepository()

    def execute(self, db: Session, payload: MindSandboxQueryRequest) -> MindSandboxQueryResponse:
        run_id = str(uuid.uuid4())
        tools = payload.tools or ["Read", "context_analysis"]
        tools = [t for t in tools if t in SUPPORTED_TOOLS]

        messages_by_session = _collect_messages(db, payload.sessionIds)
        session_meta = {
            row.id: row
            for row in db.scalars(
                select(Conversation).where(Conversation.id.in_(payload.sessionIds))
            ).all()
        }

        output_sections: list[str] = []
        used_tools: list[str] = []
        neural_file_path: str | None = None

        if "Read" in tools:
            used_tools.append("Read")
            lines: list[str] = ["Read context from selected sessions:"]
            for sid in payload.sessionIds:
                conv = session_meta.get(sid)
                msgs = messages_by_session.get(sid, [])
                title = conv.title if conv else sid
                lines.append(f"- {title} ({sid}) messages={len(msgs)}")
                for msg in msgs[-6:]:
                    lines.append(f"  - [{msg.role}] {_shorten(msg.content, 180)}")
            output_sections.append("\n".join(lines))

        if "Search_Function" in tools:
            used_tools.append("Search_Function")
            matches: list[str] = []
            regexes = [
                re.compile(r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("),
                re.compile(r"\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("),
                re.compile(r"\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)\b"),
            ]
            for sid, msgs in messages_by_session.items():
                for msg in msgs:
                    for rx in regexes:
                        for found in rx.findall(msg.content):
                            matches.append(f"{sid}: {found}")
            unique = sorted(set(matches))[:80]
            output_sections.append("Search_Function results:\n" + ("\n".join(unique) if unique else "No symbols found."))

        if "Search_code" in tools:
            used_tools.append("Search_code")
            query = (payload.query or "").strip().lower()
            rows: list[str] = []
            if query:
                for sid, msgs in messages_by_session.items():
                    for msg in msgs:
                        if query in msg.content.lower():
                            rows.append(f"{sid}: {_shorten(msg.content, 200)}")
            output_sections.append("Search_code results:\n" + ("\n".join(rows[:50]) if rows else "No matching code/content."))

        if "context_tree" in tools:
            used_tools.append("context_tree")
            lines = ["Context tree:"]
            for sid in payload.sessionIds:
                conv = session_meta.get(sid)
                node = conv.title if conv else sid
                msg_count = len(messages_by_session.get(sid, []))
                lines.append(f"- {node} ({sid})")
                lines.append(f"  - messages: {msg_count}")
                lines.append(f"  - type: {conv.topic_type.value if conv else 'unknown'}")
            output_sections.append("\n".join(lines))

        if "context_analysis" in tools:
            used_tools.append("context_analysis")
            total_messages = sum(len(v) for v in messages_by_session.values())
            total_chars = sum(len(m.content) for rows in messages_by_session.values() for m in rows)
            output_sections.append(
                "Context analysis:\n"
                f"- selected_sessions={len(payload.sessionIds)}\n"
                f"- total_messages={total_messages}\n"
                f"- total_chars={total_chars}\n"
                f"- query={payload.query or '<none>'}"
            )

        if "callSupervisor" in tools:
            used_tools.append("callSupervisor")
            if payload.folderPath:
                job = self._mind_repository.create_job(
                    db,
                    folder_path=payload.folderPath,
                    session_ids=payload.sessionIds,
                    query=payload.query,
                    source_session_id=payload.sessionIds[0],
                )
                session_supervisor.dispatch(job.id)
                output_sections.append(f"callSupervisor: queued job {job.id}")
            else:
                output_sections.append("callSupervisor: skipped (folderPath is required).")

        if "call_analyst" in tools:
            used_tools.append("call_analyst")
            findings = []
            query = (payload.query or "").lower()
            if "wrong" in query or "understood" in query:
                findings.append("Potential intent mismatch detected in user query semantics.")
            if not findings:
                findings.append("No critical analytical issues detected in selected context.")
            output_sections.append("Analyst findings:\n- " + "\n- ".join(findings))

        if "delete_session" in tools:
            used_tools.append("delete_session")
            # Strict policy: only deletes session rows, never filesystem paths.
            if payload.query and payload.query.startswith("delete_session:"):
                target_id = payload.query.split(":", 1)[1].strip()
                target = self._session_repository.get(db, target_id)
                if target is None:
                    output_sections.append(f"delete_session: session not found ({target_id})")
                elif target.topic_type == "project_main":
                    output_sections.append("delete_session: blocked for project_main sessions.")
                else:
                    deleted = self._session_repository.delete(db, target_id)
                    output_sections.append(
                        f"delete_session: {'deleted' if deleted else 'session not found'} ({target_id})"
                    )
            else:
                output_sections.append("delete_session: no target specified (use query 'delete_session:<id>').")

        if "create_neural" in tools:
            used_tools.append("create_neural")
            base = Path((Path.home() / ".codex") if "CODEX_HOME" not in os.environ else os.environ["CODEX_HOME"]) / "Neural-network"
            base.mkdir(parents=True, exist_ok=True)
            seq = self._neural_repository.next_sequence(db)
            filename = f"Neural-{seq}.md"
            file_path = base / filename

            content = (
                f"# Neural {seq}\n\n"
                f"Run: {run_id}\n\n"
                f"Query: {payload.query or '<none>'}\n\n"
                "## Sessions\n"
                + "\n".join(f"- {sid}" for sid in payload.sessionIds)
                + "\n\n## Structured Context\n"
                + "\n\n".join(output_sections[:4])
            )
            file_path.write_text(content, encoding="utf-8")

            self._neural_repository.create_document(
                db,
                session_id=payload.sessionIds[0] if payload.sessionIds else None,
                folder_path=payload.folderPath,
                file_path=str(file_path),
                filename=filename,
                sequence=seq,
                content=content,
            )
            neural_file_path = str(file_path)
            output_sections.append(f"create_neural: wrote {file_path}")

        if not output_sections:
            output_sections.append("No tool output generated.")

        return MindSandboxQueryResponse(
            output="\n\n".join(output_sections),
            usedTools=used_tools,
            sessionIds=payload.sessionIds,
            runId=run_id,
            neuralFilePath=neural_file_path,
        )
