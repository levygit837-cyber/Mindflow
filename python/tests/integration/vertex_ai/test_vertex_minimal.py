#!/usr/bin/env python3
"""Minimal test script for Vertex AI model integration."""

import asyncio
import os
import sys
import time

# Add the project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python')

async def test_vertex_minimal():
    """Test Vertex AI with minimal dependencies."""
    try:
        # Import only what we need
        
        # Import settings
        
        # Import the providers module directly
        sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python/mindflow_backend/runtime/providers')
        import providers
        
        print("✓ Successfully imported providers module")
        
        # Test model creation
        model = providers.get_model_for_provider("vertexai", "gemini-3-flash-preview")
        print("✓ Successfully created Vertex AI model instance")
        
        # Test basic message
        message = [{"role": "user", "content": "Hello! Respond with 'AI working'"}]
        
        print("Sending test message...")
        start_time = time.time()
        response = await model.ainvoke(message)
        response_time = time.time() - start_time
        
        print(f"✓ Response received in {response_time:.2f}s")
        print(f"Response type: {type(response)}")
        print(f"Response: {response}")
        
        # Extract content from AIMessage object
        if hasattr(response, 'content'):
            content = response.content
            print(f"Content: {content}")
            
            # Extract text from content
            if isinstance(content, list) and content:
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get('type') == 'text' and 'text' in part:
                            text_parts.append(part['text'])
                        elif part.get('type') == 'thinking' and 'thinking' in part:
                            text_parts.append(part['thinking'])
                    elif hasattr(part, 'text'):
                        text_parts.append(part.text)
                    elif isinstance(part, str):
                        text_parts.append(part)
                
                full_text = " ".join(text_parts)
                print(f"Extracted text: {full_text}")
                
                # Basic validation
                if full_text and len(full_text.strip()) > 0:
                    print("✓ Vertex AI model test PASSED")
                    return True
                else:
                    print("✗ ERROR: Empty text content")
                    return False
            else:
                print("✗ ERROR: Unexpected content format")
                return False
        else:
            print("✗ ERROR: Response has no content attribute")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run minimal test."""
    print("=== Minimal Vertex AI Test ===\n")
    
    # Check environment
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY")
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not api_key and not creds:
        print("⚠ WARNING: No authentication found")
        print("  Set GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS\n")
    
    # Run test
    result = await test_vertex_minimal()
    
    if result:
        print("\n🎉 Vertex AI model is working!")
        return 0
    else:
        print("\n❌ Vertex AI test failed.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
