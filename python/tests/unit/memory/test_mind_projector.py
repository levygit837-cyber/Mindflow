from __future__ import annotations

from datetime import UTC, datetime

from mindflow_backend.memory.mind_md import GENERATED_END, GENERATED_START, MindProjector
from mindflow_backend.schemas.memory.contracts import ProjectSnapshot, ProjectSnapshotSection


def test_mind_projector_render_and_merge_preserve_manual_content(tmp_path) -> None:
    projector = MindProjector()
    snapshot = ProjectSnapshot(
        project_name="Mindflow",
        project_root=str(tmp_path),
        generated_at=datetime(2026, 4, 4, tzinfo=UTC),
        sections=[
            ProjectSnapshotSection(title="Project", entries=["Project root: `/tmp/project`"]),
            ProjectSnapshotSection(title="Facts", entries=["Canonical orchestrator is the GA surface."]),
            ProjectSnapshotSection(title="Changes", entries=["Stream chat defaults to orchestrated mode."]),
            ProjectSnapshotSection(title="Decisions", entries=["ADR 0018 adopted orchestrator-first runtime."]),
            ProjectSnapshotSection(title="Open Questions", entries=[]),
        ],
    )

    target = tmp_path / ".mindflow" / "MIND.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "# Team Notes\n\nManual content before.\n\n"
        f"{GENERATED_START}\nold generated\n{GENERATED_END}\n\n"
        "Manual content after.\n",
        encoding="utf-8",
    )

    written_path = projector.write(snapshot, output_path=str(target))
    content = target.read_text(encoding="utf-8")

    assert written_path == str(target)
    assert "Manual content before." in content
    assert "Manual content after." in content
    assert "Canonical orchestrator is the GA surface." in content
    assert "Stream chat defaults to orchestrated mode." in content
    assert "ADR 0018 adopted orchestrator-first runtime." in content
    assert content.count(GENERATED_START) == 1
    assert content.count(GENERATED_END) == 1
