# Tests Structure Documentation

This directory contains the reorganized test suite for the MindFlow backend.

## 📁 Structure

```
tests/
├── unit/                    # Fast unit tests
│   ├── agents/             # Agent components (5 tests)
│   ├── orchestrator/       # Orchestration logic (5 tests)  
│   ├── runtime/            # Runtime & parsing (3 tests)
│   ├── api/                # API endpoints & security (4 tests)
│   ├── storage/            # Storage models (1 test)
│   ├── grpc/               # gRPC components (3 tests)
│   ├── tools/              # Tools system (6 tests)
│   ├── workers/            # Worker system (1 test)
│   └── utils/              # Utilities & schemas (40+ tests)
├── integration/            # Component integration tests
│   ├── backend/            # Backend integration (5 tests)
│   ├── grpc/               # gRPC integration (2 tests)
│   ├── tools/              # Tools integration (2 tests)
│   ├── vertex_ai/          # Vertex AI integration (2 tests)
│   ├── research/           # Research workflows (1 test)
│   └── workflows/          # Workflow tests (empty)
├── e2e/                    # End-to-end tests
│   ├── scenarios/          # Full scenarios (1 test)
│   ├── migration/          # Migration process tests (3 tests)
│   ├── validation/         # Validation tests (1 test)
│   └── performance/        # Performance tests (empty)
├── live/                   # Tests requiring external services
├── fixtures/               # Shared test data
├── helpers/                # Test utilities
└── conftest.py             # Pytest configuration
```

## 🚀 Usage

### Run All Tests
```bash
pytest tests/
```

### Run Specific Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only  
pytest tests/integration/

# E2E tests only
pytest tests/e2e/

# Live tests (requires credentials)
pytest tests/live/ -m live
```

### Run Specific Components
```bash
# Agent tests
pytest tests/unit/agents/

# Runtime tests
pytest tests/unit/runtime/

# Tools tests
pytest tests/unit/tools/

# Workers tests
pytest tests/unit/workers/

# gRPC tests
pytest tests/unit/grpc/

# Tools integration tests
pytest tests/integration/tools/

# Vertex AI integration
pytest tests/integration/vertex_ai/

# Migration tests
pytest tests/e2e/migration/
```

## 📊 Test Count

- **Total:** ~81 test files (+14 migrated)
- **Unit:** 66 tests (fast, isolated)
- **Integration:** 12 tests (component integration)
- **E2E:** 5 tests (full scenarios, migration, validation)
- **Live:** External service tests

## 🔄 Migration Notes

All test imports have been updated to use proper module paths instead of sys.path manipulation. Tests moved from root directory now reside in appropriate subdirectories based on their functionality.

**Recently migrated (14 files):**
- 6 tools unit tests → `tests/unit/tools/`
- 2 tools integration tests → `tests/integration/tools/`
- 1 workers unit test → `tests/unit/workers/`
- 1 gRPC integration test → `tests/integration/grpc/`
- 3 migration e2e tests → `tests/e2e/migration/`
- 1 validation e2e test → `tests/e2e/validation/`

## 🛠️ Requirements

- Python 3.11+
- pytest (for running tests)
- pytest-asyncio (for async tests)
- Project dependencies installed
