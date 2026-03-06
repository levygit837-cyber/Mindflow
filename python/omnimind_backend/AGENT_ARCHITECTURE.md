# OmniMind Agent Architecture

## Overview

The OmniMind agent system has been restructured to resolve architectural inconsistencies and provide a clean, modular foundation. This document explains the new organization and how to use it.

## 🏗️ New Structure

```
python/omnimind_backend/agents/
├── core/                    # Core interfaces, DI, exceptions
│   ├── interfaces.py       # All component contracts
│   ├── container.py        # Dependency injection
│   ├── exceptions.py       # Custom exceptions
│   └── initialization.py   # System initialization
├── context/                 # Context retrieval subsystem
│   ├── __init__.py         # Public API
│   ├── retriever.py        # AgentContextRetriever (moved)
│   ├── cache.py            # LRU cache with TTL
│   ├── vector_store.py     # Vector store with embeddings
│   └── analyzer.py         # Content analysis
├── personality/            # Personality system (unified)
│   ├── __init__.py         # Public API
│   ├── selector.py         # PersonalitySelector (moved)
│   ├── cache.py            # Personality cache
│   ├── rule_engine.py      # Rule evaluation
│   ├── configuration.py    # Config builders
│   ├── sub_personalities.py # Sub-personalities (unified)
│   └── dynamic_prompts.py  # Dynamic prompt system
├── prompts/                # Legacy prompts (deprecated)
├── personalities/          # Legacy personalities (deprecated)
└── _base.py, _registry.py   # Core system (unchanged)
```

## 🔧 Key Changes

### 1. **Resolved Structure Issues**
- **Before**: Files mixed in `agents/` root
- **After**: Organized into logical subsystems (`context/`, `personality/`, `review/`)

### 2. **Unified Personality System**
- **Before**: Ambiguous distinction between `prompts/` and `personalities/`
- **After**: Single `personality/` module containing:
  - Core personalities (analyst, coder, researcher)
  - Sub-personalities (security_guard, critic, creative, arch_tech)
  - Dynamic prompt generation
  - Rule-based selection

### 3. **Sub-Personalities Integration**
Previously separate agents are now sub-personalities:
- `creative` → `CreativePersonality` (sub-personality)
- `arch_tech` → `ArchTechPersonality` (sub-personality)  
- `critic` → `CriticPersonality` (sub-personality)
- `security_guard` → `SecurityGuardPersonality` (sub-personality)
- `brainstorm` → `BrainstormPersonality` (sub-personality)
- `deep_iteration` → `DeepIterationPersonality` (sub-personality)

### 4. **Dynamic Prompt System**
- **Before**: Static prompts in `prompts/`
- **After**: Dynamic prompts that adapt based on:
  - Task context
  - Personality/sub-personality
  - Conversation history
  - User preferences

## 📖 Usage Examples

### Context Retrieval
```python
from omnimind_backend.agents.context import get_agent_context_retriever

# Get context retriever for an agent
retriever = get_agent_context_retriever("agent_id")
context = await retriever.get_relevant_context(
    agent_id="agent_id",
    query="find security vulnerabilities",
    session_id="session_123"
)
```

### Personality Selection
```python
from omnimind_backend.agents.personality import get_personality_selector

# Select personality for a task
selector = get_personality_selector()
result = selector.select_personality(
    task_id="task_123",
    task_description="Review code for security issues",
    task_complexity="medium"
)

# Result includes sub-personality selection
if result.selection.selected_personality == "core":
    # Might select security_guard sub-personality
    sub_personality = result.delegation_task.get("sub_personality")
```

### Sub-Personalities
```python
from omnimind_backend.agents.personality.sub_personalities import (
    get_sub_personality,
    find_best_sub_personality
)

# Get specific sub-personality
security_guard = get_sub_personality("security_guard")

# Find best match for task
best_match = find_best_sub_personality(
    task_description="Audit authentication system",
    context=["security", "vulnerability"],
    base_personality="core"
)
```

### Dynamic Prompts
```python
from omnimind_backend.agents.personality.dynamic_prompts import (
    get_dynamic_prompt_builder,
    PromptContext
)

# Build dynamic prompt
builder = get_dynamic_prompt_builder()
context = PromptContext(
    task_description="Implement secure authentication",
    task_complexity="complex",
    personality="core",
    sub_personality="security_guard"
)

prompt = builder.build_system_prompt(context)
```

### Session Review
```python
from omnimind_backend.agents.review import get_session_review_agent

# Review session window
agent = get_session_review_agent()
result = await agent.review_session_window(task, context)
```

## 🔄 Migration Guide

### For Existing Code

**Old imports:**
```python
from omnimind_backend.agents.context_retriever import AgentContextRetriever
from omnimind_backend.agents.personality_selector import PersonalitySelector
```

**New imports:**
```python
from omnimind_backend.agents.context import AgentContextRetriever
from omnimind_backend.agents.personality import PersonalitySelector
```

### Legacy Compatibility

Legacy imports still work but are deprecated:
```python
# Still works but deprecated
from omnimind_backend.agents import get_agent_context_retriever
from omnimind_backend.agents import get_personality_selector
```

## 🎯 Benefits

1. **Clear Organization**: Logical grouping by functionality
2. **Unified System**: No ambiguity between prompts and personalities
3. **Dynamic Behavior**: Adaptive prompts and personality selection
4. **Better Testing**: Modular components are easier to test
5. **Maintainability**: Clear separation of concerns
6. **Extensibility**: Easy to add new sub-personalities

## 🚀 Next Steps

1. **Update Import Statements**: Migrate to new module structure
2. **Explore Sub-Personalities**: Use specialized variants for specific tasks
3. **Implement Dynamic Prompts**: Replace static prompts with adaptive ones
4. **Test Integration**: Verify all components work together
5. **Documentation**: Update project documentation

## 📚 Reference

- **Core Interfaces**: `agents/core/interfaces.py`
- **Dependency Injection**: `agents/core/container.py`
- **Configuration**: `config/agents.py`, `config/personality_rules.py`
- **Initialization**: `agents/core/initialization.py`

This architecture provides a solid foundation for the OmniMind agent system with clear separation of concerns, dynamic behavior, and excellent maintainability.
