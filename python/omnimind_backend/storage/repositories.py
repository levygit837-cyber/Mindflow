from sqlalchemy import func, select
from sqlalchemy.orm import Session

from omnimind_backend.storage.models import NeuralDocument


class NeuralRepository:
    def next_sequence(self, session: Session) -> int:
        value = session.scalar(select(func.max(NeuralDocument.sequence)))
        if value is None:
            return 1
        return int(value) + 1

    def create_document(
        self,
        session: Session,
        *,
        folder_path: str | None,
        file_path: str,
        filename: str,
        sequence: int,
        content: str,
    ) -> int:
        row = NeuralDocument(
            folder_path=folder_path,
            file_path=file_path,
            filename=filename,
            sequence=sequence,
            content=content,
        )
        session.add(row)
        session.flush()
        return row.id
