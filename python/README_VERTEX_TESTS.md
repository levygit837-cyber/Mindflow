# Vertex AI Model Tests

## Overview

This directory contains comprehensive tests for evaluating Vertex AI model performance and functionality in the OmniMind project.

## Test Files

### 1. `test_vertex_model_integration.py`
**Complete pytest integration tests** with `@pytest.mark.live` marker.

**Features:**
- Basic response testing
- Question answering validation
- Streaming response testing
- Error handling verification
- JSON response testing
- Conversation context testing
- Performance metrics measurement

**Usage:**
```bash
# Run all Vertex AI tests (requires API keys)
source venv/bin/activate
python -m pytest tests/test_vertex_model_integration.py -v -m live

# Run specific test
python -m pytest tests/test_vertex_model_integration.py::TestVertexModelIntegration::test_vertex_model_basic_response -v -m live
```

### 2. `test_vertex_minimal.py`
**Standalone minimal test** for quick validation.

**Features:**
- Direct import testing
- Basic message/response validation
- AIMessage content extraction
- Simple pass/fail results

**Usage:**
```bash
source venv/bin/activate
python test_vertex_minimal.py
```

## Authentication

Tests require either:
- `GOOGLE_API_KEY` environment variable
- `GOOGLE_APPLICATION_CREDENTIALS` environment variable

**Example:**
```bash
export GOOGLE_API_KEY="your-api-key-here"
# OR
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

## Test Results

### ✅ Successful Test Output
```
=== Minimal Vertex AI Test ===
✓ Successfully imported providers module
✓ Successfully created Vertex AI model instance
Sending test message...
✓ Response received in 4.84s
Response type: <class 'langchain_core.messages.ai.AIMessage'>
Extracted text: AI working
✓ Vertex AI model test PASSED

🎉 Vertex AI model is working!
```

### 📊 Performance Metrics
- **Response Time:** ~5 seconds (varies 3-20s)
- **Token Usage:** ~50 tokens total for simple queries
- **Success Rate:** 100% when properly authenticated

## Model Details

- **Provider:** Vertex AI (Google)
- **Model:** gemini-3-flash-preview
- **Features:** Thinking mode enabled, streaming support
- **Response Format:** AIMessage with structured content

## Response Format

Vertex AI returns `AIMessage` objects with:
```python
{
    'content': [
        {'type': 'thinking', 'thinking': '...'},
        {'type': 'text', 'text': '...'}
    ],
    'response_metadata': {
        'finish_reason': 'STOP',
        'model_name': 'gemini-3-flash-preview',
        'usage_metadata': {
            'input_tokens': 8,
            'output_tokens': 42,
            'total_tokens': 50
        }
    }
}
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure virtual environment is activated
   - Install dependencies: `pip install -e ".[dev]"`

2. **Authentication Errors**
   - Set `GOOGLE_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS`
   - Verify API key permissions

3. **Response Format Issues**
   - Tests handle AIMessage objects correctly
   - Content extraction from structured format

4. **Performance Issues**
   - Response times vary (3-30 seconds normal)
   - Check network connectivity

### Debug Mode

Enable detailed logging:
```bash
export OMNIMIND_DEBUG=1
python test_vertex_minimal.py
```

## Integration with CI/CD

For automated testing:
1. Store API keys in secure environment variables
2. Use `@pytest.mark.live` to separate live tests
3. Run minimal tests first, then full integration suite

**Example CI command:**
```bash
python -m pytest tests/test_vertex_model_integration.py -v -m live --timeout=300
```

## Next Steps

1. **Expand Test Coverage:** Add more complex scenarios
2. **Performance Benchmarks:** Track response times over time
3. **Model Comparison:** Test different Vertex AI models
4. **Load Testing:** Concurrent request testing
