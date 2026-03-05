# Tests Structure Documentation

This directory contains the reorganized test suite for the OmniMind backend.

## 📁 Structure

```
tests/
├── unit/                    # Fast unit tests
│   ├── agents/             # Agent components (5 tests)
│   ├── orchestrator/       # Orchestration logic (5 tests)  
│   ├── runtime/            # Runtime & parsing (3 tests)
│   ├── api/                # API endpoints & security (4 tests)
│   ├── storage/            # Storage models (1 test)
│   └── utils/              # Utilities & schemas (40+ tests)
├── integration/            # Component integration tests
│   ├── backend/            # Backend integration (5 tests)
│   ├── vertex_ai/          # Vertex AI integration (2 tests)
│   ├── research/           # Research workflows (1 test)
│   └── workflows/          # Workflow tests (empty)
├── e2e/                    # End-to-end tests
│   ├── scenarios/          # Full scenarios (1 test)
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

# Vertex AI integration
pytest tests/integration/vertex_ai/
```

## 📊 Test Count

- **Total:** ~67 test files
- **Unit:** 58 tests (fast, isolated)
- **Integration:** 8 tests (component integration)
- **E2E:** 1 test (full scenarios)
- **Live:** External service tests

## 🔄 Migration Notes

All test imports have been updated to use proper module paths instead of sys.path manipulation. Tests moved from root directory now reside in appropriate subdirectories based on their functionality.

## 🛠️ Requirements

- Python 3.11+
- pytest (for running tests)
- pytest-asyncio (for async tests)
- Project dependencies installed
