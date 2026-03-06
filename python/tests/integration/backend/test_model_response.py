import asyncio
import json
import uuid
import sys
import os
from unittest.mock import MagicMock

# Load .env FROM ROOT (most reliable)
def get_api_key():
    # Try different keys
    keys_to_check = ["GOOGLE_CLOUD_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"]
    root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    if os.path.exists(root_env):
        with open(root_env) as f:
            lines = f.readlines()
            for key_name in keys_to_check:
                for line in lines:
                    if f"{key_name}=" in line:
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
    
    for key_name in keys_to_check:
        val = os.environ.get(key_name)
        if val: return val
    return None

api_key = get_api_key()
if api_key:
    # Set all of them to be safe
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["GOOGLE_CLOUD_API_KEY"] = api_key
    os.environ["GEMINI_API_KEY"] = api_key

# Ensure the backend is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the database
import mindflow_backend.storage.db as db_module
db_module.db_session = MagicMock()
db_module.db_session.return_value.__enter__.return_value = MagicMock()

from mindflow_backend.runtime.stream import AgentRuntime
from mindflow_backend.schemas.agent import AgentChatRequest
from mindflow_backend.agents._registry import register_all_personalities

async def test_gemini_3_1():
    print(f"🚀 Starting Gemini 3.1 Pro Test (API Key Found: {bool(api_key)})")
    
    register_all_personalities()
    runtime = AgentRuntime()
    runtime._chat_repo = MagicMock()
    
    payload = AgentChatRequest(
        message="Olá! Você é o Gemini 3.1 Pro? Por favor, faça um resumo técnico sobre os benefícios de arquiteturas orientadas a agentes com 'Decomposition Thinking'.",
        provider="vertexai", # Using Vertex AI with API Key as requested
        model="gemini-3.1-pro-preview",
        orchestrate=True
    )
    
    session_id = f"test-session-{uuid.uuid4()}"
    
    try:
        async for event in runtime.stream_chat(payload, session_id):
            if event.type == "thought":
                # Mostramos os pensamentos (Thinking)
                print(f"🧠 [THOUGHT]: {event.data[:100]}...")
            elif event.type == "response":
                print(event.data, end="", flush=True)
            elif event.type == "agent_step":
                try:
                    data = json.loads(event.data)
                    print(f"\n⚙️  [STEP]: {data.get('stepName')} - {data.get('action')}")
                except:
                    print(f"\n⚙️  [STEP]: {event.data}")
            elif event.type == "done":
                print("\n✅ Stream Completed.")
            elif event.type == "error":
                print(f"\n❌ [ERROR]: {event.data}")
                
    except Exception as e:
        print(f"\n🔥 [CRASH]: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_gemini_3_1())
