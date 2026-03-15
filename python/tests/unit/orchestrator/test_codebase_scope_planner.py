from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_scope_planner_prioritizes_database_domains(tmp_path: Path) -> None:
    root = tmp_path
    for relative in (
        "models/user.py",
        "schemas/user_schema.py",
        "repositories/user_repository.py",
        "sql/user_queries.sql",
        "migrations/001_init.sql",
        "services/user_service.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# test\n", encoding="utf-8")

    from mindflow_backend.chains.planners.codebase_scope_planner import CodebaseScopePlanner

    planner = CodebaseScopePlanner(max_files_per_domain=3)
    plan = await planner.build_plan(
        message="explique a camada de banco e persistencia",
        root_dir=str(root),
    )

    assert plan.root_listing
    assert any(domain.name == "database" for domain in plan.domains)
    assert any("models/user.py" in candidate.path for candidate in plan.candidates)
    assert any("repositories/user_repository.py" in candidate.path for candidate in plan.candidates)
    assert any("sql/user_queries.sql" in candidate.path for candidate in plan.candidates)
    assert any("migrations/001_init.sql" in candidate.path for candidate in plan.candidates)
