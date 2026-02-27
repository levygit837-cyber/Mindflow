from omnimind_backend.storage.repositories import (
    AllowlistRepository,
    MindRepository,
    NeuralRepository,
    SessionRepository,
)


session_repository = SessionRepository()
mind_repository = MindRepository()
allowlist_repository = AllowlistRepository()
neural_repository = NeuralRepository()
