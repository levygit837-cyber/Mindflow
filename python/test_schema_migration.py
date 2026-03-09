#!/usr/bin/env python3
"""
Test script to verify schema migration is working correctly.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python')

def test_web_schemas():
    """Test web tool schemas."""
    print("Testing Web Schemas...")
    
    try:
        from mindflow_backend.schemas.tools.web_schemas import WEB_SCHEMAS
        print(f"✅ WEB_SCHEMAS loaded: {list(WEB_SCHEMAS.keys())}")
        
        # Test individual schemas
        from mindflow_backend.schemas.tools.web_schemas import API_CLIENT_SCHEMA, HTTP_CLIENT_SCHEMA, WEB_SCRAPER_SCHEMA, BROWSER_SEARCH_SCHEMA
        
        print(f"✅ API_CLIENT_SCHEMA: {API_CLIENT_SCHEMA.name}")
        print(f"✅ HTTP_CLIENT_SCHEMA: {HTTP_CLIENT_SCHEMA.name}")
        print(f"✅ WEB_SCRAPER_SCHEMA: {WEB_SCRAPER_SCHEMA.name}")
        print(f"✅ BROWSER_SEARCH_SCHEMA: {BROWSER_SEARCH_SCHEMA.name}")
        
    except Exception as e:
        print(f"❌ Error loading web schemas: {e}")
        return False
    
    return True

def test_system_schemas():
    """Test system tool schemas."""
    print("\nTesting System Schemas...")
    
    try:
        from mindflow_backend.schemas.tools.system_schemas import SYSTEM_SCHEMAS
        print(f"✅ SYSTEM_SCHEMAS loaded: {list(SYSTEM_SCHEMAS.keys())}")
        
        # Test individual schemas
        from mindflow_backend.schemas.tools.system_schemas import PROCESS_MANAGER_SCHEMA, RESOURCE_MONITOR_SCHEMA, SANDBOX_SCHEMA, SHELL_EXECUTOR_SCHEMA, SYSTEM_INFO_SCHEMA
        
        print(f"✅ PROCESS_MANAGER_SCHEMA: {PROCESS_MANAGER_SCHEMA.name}")
        print(f"✅ RESOURCE_MONITOR_SCHEMA: {RESOURCE_MONITOR_SCHEMA.name}")
        print(f"✅ SANDBOX_SCHEMA: {SANDBOX_SCHEMA.name}")
        print(f"✅ SHELL_EXECUTOR_SCHEMA: {SHELL_EXECUTOR_SCHEMA.name}")
        print(f"✅ SYSTEM_INFO_SCHEMA: {SYSTEM_INFO_SCHEMA.name}")
        
    except Exception as e:
        print(f"❌ Error loading system schemas: {e}")
        return False
    
    return True

def test_filesystem_schemas():
    """Test filesystem tool schemas."""
    print("\nTesting Filesystem Schemas...")
    
    try:
        from mindflow_backend.schemas.tools.filesystem_schemas import FILESYSTEM_SCHEMAS
        print(f"✅ FILESYSTEM_SCHEMAS loaded: {list(FILESYSTEM_SCHEMAS.keys())}")
        
        # Test individual schemas
        from mindflow_backend.schemas.tools.filesystem_schemas import READ_FILE_SCHEMA, WRITE_FILE_SCHEMA, EDIT_FILE_SCHEMA, DELETE_FILE_SCHEMA, LIST_DIRECTORY_SCHEMA, GREP_SEARCH_SCHEMA, GLOB_SEARCH_SCHEMA, FILE_FINDER_SCHEMA
        
        print(f"✅ READ_FILE_SCHEMA: {READ_FILE_SCHEMA.name}")
        print(f"✅ WRITE_FILE_SCHEMA: {WRITE_FILE_SCHEMA.name}")
        print(f"✅ EDIT_FILE_SCHEMA: {EDIT_FILE_SCHEMA.name}")
        print(f"✅ DELETE_FILE_SCHEMA: {DELETE_FILE_SCHEMA.name}")
        print(f"✅ LIST_DIRECTORY_SCHEMA: {LIST_DIRECTORY_SCHEMA.name}")
        print(f"✅ GREP_SEARCH_SCHEMA: {GREP_SEARCH_SCHEMA.name}")
        print(f"✅ GLOB_SEARCH_SCHEMA: {GLOB_SEARCH_SCHEMA.name}")
        print(f"✅ FILE_FINDER_SCHEMA: {FILE_FINDER_SCHEMA.name}")
        
    except Exception as e:
        print(f"❌ Error loading filesystem schemas: {e}")
        return False
    
    return True

def test_integration_schemas():
    """Test integration tool schemas."""
    print("\nTesting Integration Schemas...")
    
    try:
        from mindflow_backend.schemas.tools.integration_schemas import INTEGRATION_SCHEMAS
        print(f"✅ INTEGRATION_SCHEMAS loaded: {list(INTEGRATION_SCHEMAS.keys())}")
        
        # Test individual schemas
        from mindflow_backend.schemas.tools.integration_schemas import GIT_SCHEMA, DOCKER_SCHEMA
        
        print(f"✅ GIT_SCHEMA: {GIT_SCHEMA.name}")
        print(f"✅ DOCKER_SCHEMA: {DOCKER_SCHEMA.name}")
        
    except Exception as e:
        print(f"❌ Error loading integration schemas: {e}")
        return False
    
    return True

def test_data_schemas():
    """Test data tool schemas."""
    print("\nTesting Data Schemas...")
    
    try:
        from mindflow_backend.schemas.tools.data_schemas import DATA_SCHEMAS
        print(f"✅ DATA_SCHEMAS loaded: {list(DATA_SCHEMAS.keys())}")
        
        # Test individual schemas
        from mindflow_backend.schemas.tools.data_schemas import DATABASE_SCHEMA, CSV_PROCESSOR_SCHEMA
        
        print(f"✅ DATABASE_SCHEMA: {DATABASE_SCHEMA.name}")
        print(f"✅ CSV_PROCESSOR_SCHEMA: {CSV_PROCESSOR_SCHEMA.name}")
        
    except Exception as e:
        print(f"❌ Error loading data schemas: {e}")
        return False
    
    return True

def test_tool_imports():
    """Test that tools can import schemas correctly."""
    print("\nTesting Tool Imports...")
    
    try:
        # Test web tools
        from mindflow_backend.agents.tools.web.api_client import ApiClientTool
        api_client = ApiClientTool()
        print(f"✅ ApiClientTool schema: {api_client._schema.name}")
        
        from mindflow_backend.agents.tools.web.http_client import HttpClientTool
        http_client = HttpClientTool()
        print(f"✅ HttpClientTool schema: {http_client._schema.name}")
        
        from mindflow_backend.agents.tools.web.browser_search import BrowserSearchTool
        browser_search = BrowserSearchTool()
        print(f"✅ BrowserSearchTool schema: {browser_search._schema.name}")
        
        # Test data tools
        from mindflow_backend.agents.tools.data.data_tools import DatabaseTool, CSVProcessorTool
        db_tool = DatabaseTool()
        print(f"✅ DatabaseTool schema: {db_tool._schema.name}")
        
        csv_tool = CSVProcessorTool()
        print(f"✅ CSVProcessorTool schema: {csv_tool._schema.name}")
        
    except ImportError as e:
        if "asyncpg" in str(e):
            print(f"⚠️  Warning: asyncpg not available (optional dependency): {e}")
            return True  # This is not a schema migration error
        else:
            print(f"❌ Error importing tools: {e}")
            return False
    except Exception as e:
        print(f"❌ Error importing tools: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("🧪 Schema Migration Test Suite")
    print("=" * 50)
    
    results = []
    results.append(test_web_schemas())
    results.append(test_system_schemas())
    results.append(test_filesystem_schemas())
    results.append(test_integration_schemas())
    results.append(test_data_schemas())
    results.append(test_tool_imports())
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total}/{total} tests PASSED!")
        print("🎉 Schema migration appears to be working correctly!")
    else:
        print(f"❌ {total - passed}/{total} tests FAILED!")
        print("🔧 Schema migration needs attention.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
