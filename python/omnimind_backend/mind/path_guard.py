from pathlib import Path

from sqlalchemy.orm import Session

from omnimind_backend.storage.repositories import AllowlistRepository


class PathValidationError(ValueError):
    pass


def normalize_and_validate_folder_path(
    *,
    folder_path: str,
    session: Session,
    allowlist_repository: AllowlistRepository,
) -> str:
    candidate = Path(folder_path)
    if not candidate.is_absolute():
        raise PathValidationError("folderPath must be an absolute path")

    resolved = candidate.expanduser().resolve()
    if not resolved.exists():
        raise PathValidationError("folderPath does not exist")

    normalized = str(resolved)
    if not allowlist_repository.is_allowed(session, normalized):
        raise PathValidationError("folderPath is not allowed by server policy")

    return normalized
