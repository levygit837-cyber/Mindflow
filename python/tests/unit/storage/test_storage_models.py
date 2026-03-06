from mindflow_backend.storage.postgresql.models import NeuralDocument


def test_neural_document_no_session_id_column() -> None:
    assert "session_id" not in NeuralDocument.__table__.c
