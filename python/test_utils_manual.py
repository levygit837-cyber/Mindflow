#!/usr/bin/env python3
"""Manual test script for utils restructure."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python')

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        # Core utilities
        from mindflow_backend.utils.core import (
            format_datetime_iso,
            slugify,
            generate_uuid4,
            estimate_token_count,
            hash_string,
            encode_base64
        )
        print("✅ Core imports successful")
        
        # Validation utilities
        from mindflow_backend.utils.validation import (
            validate_email,
            validate_url,
            sanitize_string
        )
        print("✅ Validation imports successful")
        
        # Formatting utilities
        from mindflow_backend.utils.formatting import (
            format_sse,
            extract_json_from_response
        )
        print("✅ Formatting imports successful")
        
        # Network utilities
        from mindflow_backend.utils.network import (
            retry_on_error,
            get_port_manager,
            parse_url
        )
        print("✅ Network imports successful")
        
        # Monitoring utilities
        from mindflow_backend.utils.monitoring import (
            HealthStatus,
            health_check_database
        )
        print("✅ Monitoring imports successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of migrated utilities."""
    print("\nTesting basic functionality...")
    
    try:
        # Test core utilities
        from mindflow_backend.utils.core import slugify, estimate_token_count
        
        slug_result = slugify("Hello World Test!")
        assert slug_result == "hello-world-test"
        print(f"✅ slugify: {slug_result}")
        
        token_count = estimate_token_count("This is a test string for token counting")
        assert token_count > 0
        print(f"✅ estimate_token_count: {token_count}")
        
        # Test validation
        from mindflow_backend.utils.validation import validate_email
        
        email_valid = validate_email("test@example.com")
        assert email_valid is True
        print(f"✅ validate_email: {email_valid}")
        
        # Test formatting
        from mindflow_backend.utils.formatting import format_sse
        
        sse_result = format_sse({"message": "test"})
        assert "data:" in sse_result
        assert "test" in sse_result
        print(f"✅ format_sse: {len(sse_result)} chars")
        
        # Test JSON extraction
        from mindflow_backend.utils.formatting import extract_json_from_response
        
        json_content = '```json\n{"key": "value"}\n```'
        extracted = extract_json_from_response(json_content)
        assert extracted == '{"key": "value"}'
        print(f"✅ extract_json_from_response: {extracted}")
        
        # Test network utilities
        from mindflow_backend.utils.network import parse_url
        
        url_parts = parse_url("https://example.com/path?query=value")
        assert url_parts.scheme == "https"
        assert url_parts.netloc == "example.com"
        print(f"✅ parse_url: {url_parts.scheme}://{url_parts.netloc}")
        
        # Test monitoring
        from mindflow_backend.utils.monitoring import HealthStatus
        
        status = HealthStatus("test", True, "Test status")
        assert status.name == "test"
        assert status.is_healthy is True
        print(f"✅ HealthStatus: {status.name} = {status.is_healthy}")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test backward compatibility."""
    print("\nTesting backward compatibility...")
    
    try:
        # Test that memory module still exports estimate_token_count
        from mindflow_backend import estimate_token_count
        from mindflow_backend.utils.core import estimate_token_count as core_token_count
        
        text = "Backward compatibility test"
        memory_result = estimate_token_count(text)
        core_result = core_token_count(text)
        
        assert memory_result == core_result
        print(f"✅ Backward compatibility: {memory_result} == {core_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False

def test_old_imports_fail():
    """Test that old import paths no longer work."""
    print("\nTesting that old imports fail...")
    
    old_imports = [
        "from mindflow_backend.memory.utils.validation import validate_memory_data",
        "from mindflow_backend.agents.research.utils.port_manager import get_port_manager",
        "from mindflow_backend.api.sse import format_sse",
        "from mindflow_backend.decomposition.utils import extract_json_from_response",
    ]
    
    failed_count = 0
    
    for import_statement in old_imports:
        try:
            exec(import_statement)
            print(f"❌ Old import should have failed: {import_statement}")
        except ImportError:
            print(f"✅ Old import correctly fails: {import_statement}")
            failed_count += 1
        except Exception as e:
            print(f"⚠️  Old import failed with unexpected error: {import_statement} - {e}")
    
    assert failed_count == len(old_imports), f"Expected {len(old_imports)} failures, got {failed_count}"
    print(f"✅ All {len(old_imports)} old imports correctly fail")
    
    return True

def main():
    """Run all tests."""
    print("🧪 Testing Utils Restructure")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Functionality Tests", test_basic_functionality),
        ("Backward Compatibility", test_backward_compatibility),
        ("Old Import Failure", test_old_imports_fail),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Utils restructure is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
