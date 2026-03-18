from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

from mindflow_desktop.main import run_ui


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _run_step(cmd: list[str], *, cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def _docker_compose_up(compose_file: Path, env_file: Path, *, cwd: Path) -> None:
    import re

    cmd = [
        "docker", "compose",
        "--env-file", str(env_file),
        "-f", str(compose_file),
        "up", "-d", "--remove-orphans",
    ]
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if result.returncode == 0:
        return

    combined = result.stderr + result.stdout

    # Container name conflict: a container with the same name exists but belongs
    # to a different compose project (e.g. started via the root docker-compose.yml).
    # Force-remove each conflicting container by name, then retry once.
    if "already in use" in combined:
        conflicting = re.findall(r'container name "/?([^"]+)"', combined)
        for name in conflicting:
            subprocess.run(["docker", "rm", "-f", name.lstrip("/")], capture_output=True)
        subprocess.run(cmd, cwd=str(cwd), check=True)
        return

    raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)


def _wait_for_postgres(container_name: str, user: str, db_name: str, *, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = subprocess.run(
            [
                "docker",
                "exec",
                container_name,
                "pg_isready",
                "-U",
                user,
                "-d",
                db_name,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(1)

    raise RuntimeError("PostgreSQL did not become ready in time")


def _wait_for_api(base_url: str, *, timeout_seconds: int = 60) -> None:
    health_url = f"{base_url.rstrip('/')}/health"
    deadline = time.time() + timeout_seconds

    with httpx.Client(timeout=3.0) as client:
        while time.time() < deadline:
            try:
                response = client.get(health_url)
                if response.status_code == 200:
                    return
            except Exception:
                pass
            time.sleep(1)

    raise RuntimeError(f"API health check failed: {health_url}")


def _start_background_process(cmd: list[str], *, cwd: Path, log_path: Path) -> subprocess.Popen[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8")

    return subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )


def run() -> None:
    python_root = Path(__file__).resolve().parents[1]
    env_file = python_root / ".env"
    env_example = python_root / ".env.example"

    if not env_file.exists():
        shutil.copy2(env_example, env_file)

    _load_env_file(env_file)

    compose_file = python_root / "docker-compose.backend.yml"

    _docker_compose_up(compose_file, env_file, cwd=python_root)

    container_name = os.getenv("POSTGRES_CONTAINER_NAME", "mindflow-postgres-v1")
    db_user = os.getenv("POSTGRES_USER", "mindflow_app")
    db_name = os.getenv("POSTGRES_DB", "mindflow_v1")
    _wait_for_postgres(container_name, db_user, db_name)

    # Migration 20260309_0009 requires pgvector which is not available in the
    # bundled PostgreSQL image.  Stop at the last safe revision.
    _run_step([sys.executable, "-m", "alembic", "upgrade", "20260308_0008"], cwd=python_root)

    api_url = os.getenv("MINDFLOW_API_URL", "http://127.0.0.1:8000")
    logs_dir = python_root / ".logs"

    # Always start local API for desktop runtime consistency.
    api_process = _start_background_process(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "mindflow_backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=python_root,
        log_path=logs_dir / "api.log",
    )

    processes: list[subprocess.Popen[str]] = [api_process]

    # Start the React frontend dev server unless a pre-built URL is configured.
    if not os.getenv("MINDFLOW_FRONTEND_URL"):
        frontend_root = python_root.parent / "frontend"
        if (frontend_root / "package.json").exists():
            frontend_process = _start_background_process(
                ["npm", "run", "dev"],
                cwd=frontend_root,
                log_path=logs_dir / "frontend.log",
            )
            processes.append(frontend_process)
            time.sleep(2)  # give Vite time to bind its port

    # Optional services for local power users.
    if _truthy(os.getenv("MINDFLOW_START_GRPC")):
        grpc_process = _start_background_process(
            [sys.executable, "-m", "mindflow_backend.grpc.server"],
            cwd=python_root,
            log_path=logs_dir / "grpc.log",
        )
        processes.append(grpc_process)

    if _truthy(os.getenv("MINDFLOW_START_WORKER")):
        worker_process = _start_background_process(
            [sys.executable, "-m", "mindflow_backend.workers.main"],
            cwd=python_root,
            log_path=logs_dir / "worker.log",
        )
        processes.append(worker_process)

    def _shutdown_background() -> None:
        for process in reversed(processes):
            if process.poll() is not None:
                continue
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                continue

        deadline = time.time() + 8
        while time.time() < deadline:
            if all(p.poll() is not None for p in processes):
                break
            time.sleep(0.2)

        for process in processes:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    try:
        _wait_for_api(api_url)

        if _truthy(os.getenv("MINDFLOW_DESKTOP_SKIP_UI")):
            return

        run_ui()
    finally:
        _shutdown_background()


if __name__ == "__main__":
    run()
