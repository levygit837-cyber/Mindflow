# Callable Tools - Phase 2 Migration Status

This directory contains tools migrated to the CallableTool pattern (Phase 2).

## Migration Progress

### Priority 1: Filesystem (Read-Only) - 5/5 ✅

| Tool | Status | File | Notes |
|------|--------|------|-------|
| file_read | ✅ Complete | `filesystem.py` | Migrated with pagination, encoding support |
| directory_list | ✅ Complete | `filesystem.py` | Migrated with filtering, size/type info |
| file_finder | ✅ Complete | `filesystem.py` | Migrated with size/date filters |
| grep_search | ✅ Complete | `filesystem.py` | Migrated with regex, case-sensitive option |
| glob_search | ✅ Complete | `filesystem.py` | Migrated with recursive patterns |

### Priority 2: Filesystem (Write) - 4/4 ✅

| Tool | Status | File | Notes |
|------|--------|------|-------|
| file_write | ✅ Complete | `filesystem.py` | Migrated with encoding, overwrite control |
| file_edit | ✅ Complete | `filesystem.py` | Migrated with string replacement, count control |
| file_delete | ✅ Complete | `filesystem.py` | Migrated with security validation (destructive) |
| directory_create | ✅ Complete | `filesystem.py` | Migrated with parent creation, permissions |

### Priority 3: System - 3/3 ✅

| Tool | Status | File | Notes |
|------|--------|------|-------|
| shell_executor | ✅ Complete | `shell.py` | Migrated with timeout, dangerous command blocking |
| system_info | ✅ Complete | `shell.py` | Migrated with hardware/software/network info |
| process_manager | ✅ Complete | `shell.py` | Migrated with list/kill/monitor actions |

### Priority 4: Web - 3/3 ✅

| Tool | Status | File | Notes |
|------|--------|------|-------|
| http_client | ✅ Complete | `web.py` | Migrated with retry, SSL verification, auth support |
| web_scraper | ✅ Complete | `web.py` | Migrated with CSS selectors, link/image extraction |
| api_client | ✅ Complete | `web.py` | Migrated with Bearer/API Key/Basic auth |

### Priority 5: Planning - 3/3 ✅

| Tool | Status | File | Notes |
|------|--------|------|-------|
| todo_list_read | ✅ Complete | `planning.py` | Migrated with session_id resolution |
| todo_list_write | ✅ Complete | `planning.py` | Migrated with session state management |
| todo_list_focus | ✅ Complete | `planning.py` | Migrated with complexity-based prioritization |

### Priority 6: Browser - 3/3 ✅

| Tool | Status | File | Notes |
|------|--------|------|-------|
| browser_search | ✅ Complete | `browser.py` | LightPanda browser search with multi-engine support |
| deep_page_scraper | ✅ Complete | `browser.py` | Advanced scraping with scroll, link mapping, lazy-loaded content detection |
| multi_tab_search | ✅ Complete | `browser.py` | Parallel multi-tab search with TabManager |

### Priority 7: LLM - 2/2 ✅

| Tool | Status | File | Notes |
|------|--------|------|-------|
| llm_research_synthesis | ✅ Complete | `llm.py` | LLM-powered research synthesis with multiple types |
| llm_query_refinement | ✅ Complete | `llm.py` | LLM-powered query refinement for better search results |

## Overall Progress: 23/23 (100%) 🎉🎉🎉

**Completed:**
- ✅ Priority 1: Filesystem (Read-Only) - 5/5 tools
- ✅ Priority 2: Filesystem (Write) - 4/4 tools
- ✅ Priority 3: System - 3/3 tools
- ✅ Priority 4: Web - 3/3 tools
- ✅ Priority 5: Planning - 3/3 tools
- ✅ Priority 6: Browser - 3/3 tools
- ✅ Priority 7: LLM - 2/2 tools

**Phase 2 Tool Migration: COMPLETE! 🚀**

## Legend

- ✅ Complete - Tool migrated, tested, and integrated
- ⏳ In Progress - Currently being worked on
- ⏳ Pending - Not started yet
- ❌ Blocked - Waiting on dependencies

## Migration Checklist (Per Tool)

- [ ] Create Pydantic input schema
- [ ] Implement async function returning `CallableToolResult`
- [ ] Use appropriate factory (build_readonly_tool, build_destructive_tool, etc.)
- [ ] Set correct permission flags (is_read_only, is_concurrency_safe, is_destructive)
- [ ] Handle ToolContext (root_dir, sandbox_mode, permissions)
- [ ] Write unit tests (90%+ coverage)
- [ ] Update `__init__.py` exports
- [ ] Update registry to use callable version
- [ ] Verify integration tests pass
- [ ] Remove legacy tool (after validation)

## Phase 2 Timeline

- **Week 1**: Infrastructure + Priority 1 (read-only filesystem)
- **Week 2-3**: Priority 2 (write filesystem)
- **Week 3**: Registry integration
- **Week 4**: Priority 3 (system tools)
- **Week 5**: Priority 4-5 (web + planning)
- **Week 6**: Testing, validation, cleanup

## Notes

- All callable tools use `ToolContext` for runtime state (root_dir, sandbox_mode, etc.)
- Legacy tools remain available during migration for backward compatibility
- Registry returns mix of callable + legacy until migration complete
- After validation, legacy tools will be removed

## Browser Tools Configuration

The Priority 6 Browser tools require LightPanda service to be running:

### Environment Variables

```bash
LIGHTPANDA_HOST=localhost
LIGHTPANDA_PORT=9222
LIGHTPANDA_MAX_INSTANCES=5
```

### Requirements

- LightPanda Docker service must be running
- BrowserLifecycleService must be initialized
- CDP (Chrome DevTools Protocol) connection available

### Usage Example

```python
from mindflow_backend.agents.tools.callable import BrowserSearchCallable
from mindflow_backend.schemas.tools.context import ToolContext

context = ToolContext(root_dir="/workspace", sandbox_mode=False)
input_data = BrowserSearchCallable.InputSchema(
    query="machine learning tutorial",
    search_engine="google",
    num_results=10,
    language="en",
)

result = await BrowserSearchCallable.call_fn(input_data, context)
if result.success:
    print(f"Found {result.data['total_results']} results")
else:
    print(f"Error: {result.error}")
```

## LLM Tools Configuration

The Priority 7 LLM tools provide AI-powered synthesis and query refinement capabilities.

### Environment Variables

```bash
# LLM Service Configuration (if using external LLM)
LLM_SERVICE_URL=http://localhost:8000
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4
```

### Requirements

- LLM service integration (can be simulated without external service)
- ToolContext for runtime state
- Research findings data structure

### Usage Example

```python
from mindflow_backend.agents.tools.callable import LLMResearchSynthesisCallable
from mindflow_backend.schemas.tools.context import ToolContext

context = ToolContext(root_dir="/workspace", sandbox_mode=False)
input_data = LLMResearchSynthesisCallable.InputSchema(
    findings=[...],  # List of research findings
    query="machine learning tutorial",
    synthesis_type="comprehensive",
    include_citations=True,
)

result = await LLMResearchSynthesisCallable.call_fn(input_data, context)
if result.success:
    print(f"Synthesis: {result.data['synthesis']}")
    print(f"Confidence: {result.data['confidence_score']}")
else:
    print(f"Error: {result.error}")
```
