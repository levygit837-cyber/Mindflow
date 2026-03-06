.PHONY: format lint typecheck test check precommit-install precommit-run

format:
	uv run --extra dev ruff check --fix .
	uv run --extra dev ruff format .

lint:
	uv run --extra dev ruff check .

typecheck:
	uv run --extra dev mypy mindflow_backend mindflow_cli mindflow_desktop

test:
	uv run --extra dev pytest

check:
	uv run --extra dev ruff check .
	uv run --extra dev ruff format --check .
	uv run --extra dev mypy mindflow_backend mindflow_cli mindflow_desktop
	uv run --extra dev pytest

precommit-install:
	uvx pre-commit install

precommit-run:
	uvx pre-commit run --all-files
