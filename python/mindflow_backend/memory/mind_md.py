"""Mind.md projection helpers for canonical structured memory."""

from __future__ import annotations

from pathlib import Path

from mindflow_backend.schemas.memory.contracts import ProjectSnapshot

GENERATED_START = "<!-- mindflow:generated:start -->"
GENERATED_END = "<!-- mindflow:generated:end -->"


class MindProjector:
    """Render and persist Mind.md from a structured project snapshot."""

    def render(self, snapshot: ProjectSnapshot) -> str:
        lines = [
            "# Mind.md",
            "",
            GENERATED_START,
            f"_Generated from canonical memory on {snapshot.generated_at.isoformat()}._",
            "",
        ]

        for section in snapshot.sections:
            lines.append(f"## {section.title}")
            if section.entries:
                lines.extend(f"- {entry}" for entry in section.entries)
            else:
                lines.append("- None recorded.")
            lines.append("")

        if snapshot.references:
            lines.append("## References")
            lines.extend(f"- {reference}" for reference in snapshot.references)
            lines.append("")

        lines.append(GENERATED_END)
        lines.append("")
        return "\n".join(lines)

    def merge(self, existing_content: str, generated_content: str) -> str:
        if GENERATED_START not in existing_content or GENERATED_END not in existing_content:
            existing = existing_content.strip()
            if not existing:
                return generated_content
            return f"{existing}\n\n{generated_content}"

        before, remainder = existing_content.split(GENERATED_START, 1)
        _, after = remainder.split(GENERATED_END, 1)
        merged = f"{before.rstrip()}\n\n{generated_content}\n{after.lstrip()}"
        return merged.strip() + "\n"

    def write(self, snapshot: ProjectSnapshot, *, output_path: str | None = None) -> str:
        target = Path(output_path or snapshot.output_path or Path(snapshot.project_root) / ".mindflow" / "MIND.md")
        target.parent.mkdir(parents=True, exist_ok=True)

        generated_content = self.render(snapshot)
        existing_content = target.read_text(encoding="utf-8") if target.exists() else ""
        merged_content = self.merge(existing_content, generated_content)
        target.write_text(merged_content, encoding="utf-8")
        return str(target)
