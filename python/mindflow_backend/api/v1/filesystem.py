"""Filesystem browsing API for folder path selection.

Provides endpoints for the frontend to browse the server's filesystem
so users can select a working directory for agents.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/filesystem", tags=["Filesystem"])


class FolderEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    is_git_repo: bool = False


class BrowseResponse(BaseModel):
    current_path: str
    parent_path: str | None
    entries: list[FolderEntry]


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def _safe_resolve(raw: str) -> Path:
    """Resolve and validate that the path is accessible."""
    try:
        resolved = Path(raw).expanduser().resolve()
        if not resolved.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {raw}")
        if not resolved.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {raw}")
        return resolved
    except (OSError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/browse", response_model=BrowseResponse)
async def browse_filesystem(
    path: str = Query(default="~", description="Directory path to browse"),
) -> BrowseResponse:
    """Browse the server filesystem to select a working directory.

    Returns directories and files in the given path, suitable for a folder picker UI.
    Only directories are returned (files are excluded).
    """
    resolved = _safe_resolve(path)

    entries: list[FolderEntry] = []
    try:
        for entry in sorted(resolved.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # Skip hidden directories (starting with .) except .git parent detection
            if entry.name.startswith("."):
                continue
            if not entry.is_dir():
                continue
            try:
                entries.append(
                    FolderEntry(
                        name=entry.name,
                        path=str(entry),
                        is_dir=True,
                        is_git_repo=_is_git_repo(entry),
                    )
                )
            except (PermissionError, OSError):
                continue
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"Permission denied: {resolved}") from e

    parent = str(resolved.parent) if resolved.parent != resolved else None

    return BrowseResponse(
        current_path=str(resolved),
        parent_path=parent,
        entries=entries,
    )


@router.get("/home", response_model=BrowseResponse)
async def browse_home() -> BrowseResponse:
    """Browse the user's home directory."""
    return await browse_filesystem(path="~")


@router.get("/cwd", response_model=BrowseResponse)
async def browse_cwd() -> BrowseResponse:
    """Browse the current working directory of the backend process."""
    return await browse_filesystem(path=str(Path.cwd()))
