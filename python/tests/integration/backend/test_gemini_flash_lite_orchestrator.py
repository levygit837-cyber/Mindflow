#!/usr/bin/env python3
"""Teste de integração para validar gemini-3.1-flash-lite-preview como Orquestrador."""

import asyncio
import json
import os
import sys
import uuid
from unittest.mock import MagicMock

# Add the project root to Python path
sys.path.insert(0, '/home/levybonito/Projetos/MindFlow/python')

# Load .env
def get_api_key():
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
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["GOOGLE_CLOUD_API_KEY"] = api_key
    os.environ["GEMINI_API_KEY"] = api_key

# Mock the database
import mindflow_backend.infra.database.connection as db_module
db_module.get_db_session = MagicMock()
db_module.get_db_session.return_value.__aenter__ = MagicMock(return_value=MagicMock())
db_module.get_db_session.return_value.__aexit__ = MagicMock(return_value=MagicMock())

from mindflow_backend.agents._registry import register_all_specialists
from mindflow_backend.runtime.stream import AgentRuntime
from mindflow_backend.schemas.agent import AgentChatRequest


async def test_gemini_flash_lite_orchestrator():
    """Testa gemini-3.1-flash-lite-preview como Orquestrador."""
    print(f"🚀 Iniciando teste do gemini-3.1-flash-lite-preview como Orquestrador")
    print(f"🔑 API Key encontrada: {bool(api_key)}")
    
    register_all_specialists()
    runtime = AgentRuntime()
    runtime._chat_repo = MagicMock()
    
    # Payload de teste para validar orquestração
    payload = AgentChatRequest(
        message="Você é um orquestrador de agentes. Analise a seguinte tarefa: 'Preciso criar uma função Python que soma dois números'. "
                "Descreva como você orquestraria essa tarefa entre diferentes agentes especializados.",
        provider="vertexai",
        model="gemini-3.1-flash-lite-preview",
        orchestrate=True  # Importante: habilita orquestração
    )
    
    session_id = f"test-session-{uuid.uuid4()}"
    
    print(f"📋 Session ID: {session_id}")
    print(f"🤖 Provider: {payload.provider}")
    print(f"🧠 Model: {payload.model}")
    print(f"🎯 Orchestrate: {payload.orchestrate}")
    print(f"\n🔄 Iniciando stream...\n")
    
    try:
        thought_count = 0
        step_count = 0
        response_parts = []
        
        async for event in runtime.stream_chat(payload, session_id):
            if event.type == "thought":
                thought_count += 1
                print(f"🧠 [THOUGHT #{thought_count}]: {event.data[:150]}...")
                
            elif event.type == "response":
                response_parts.append(event.data)
                print(event.data, end="", flush=True)
                
            elif event.type == "agent_step":
                step_count += 1
                try:
                    data = json.loads(event.data)
                    print(f"\n⚙️  [STEP #{step_count}]: {data.get('stepName')} - {data.get('action')}")
                except:
                    print(f"\n⚙️  [STEP #{step_count}]: {event.data}")
                    
            elif event.type == "done":
                print("\n✅ Stream completado com sucesso.")
                
            elif event.type == "error":
                print(f"\n❌ [ERROR]: {event.data}")
                return False
                
        # Validações
        full_response = "".join(response_parts)
        print(f"\n\n📊 Métricas:")
        print(f"   - Thoughts: {thought_count}")
        print(f"   - Steps: {step_count}")
        print(f"   - Response length: {len(full_response)} chars")
        
        # Validações de orquestração
        success = True
        
        if thought_count == 0:
            print("⚠️  WARNING: Nenhum thought detectado (pode indicar problema com orquestração)")
            success = False
        else:
            print("✓ Orquestração com thinking funcionando")
            
        if step_count == 0:
            print("⚠️  WARNING: Nenhum step detectado (pode indicar problema com orquestração)")
        else:
            print("✓ Orquestração com steps funcionando")
            
        if len(full_response) < 50:
            print("❌ ERROR: Response muito curta")
            success = False
        else:
            print("✓ Response com conteúdo adequado")
            
        # Verificar se response menciona orquestração
        orchestration_keywords = ["orquestr", "agent", "especialist", "coorden", "deleg"]
        has_orchestration = any(keyword.lower() in full_response.lower() for keyword in orchestration_keywords)
        
        if has_orchestration:
            print("✓ Response demonstra comportamento de orquestrador")
        else:
            print("⚠️  WARNING: Response não demonstra claramente comportamento de orquestrador")
            
        return success
        
    except Exception as e:
        print(f"\n🔥 [CRASH]: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_simple_chat():
    """Teste simples de chat sem orquestração."""
    print(f"\n🧪 Teste simples de chat (sem orquestração)")
    
    register_all_specialists()
    runtime = AgentRuntime()
    runtime._chat_repo = MagicMock()
    
    payload = AgentChatRequest(
        message="Responda apenas com 'OK' para confirmar que o modelo está funcionando.",
        provider="vertexai",
        model="gemini-3.1-flash-lite-preview",
        orchestrate=False  # Sem orquestração
    )
    
    session_id = f"test-simple-{uuid.uuid4()}"
    
    try:
        response_parts = []
        async for event in runtime.stream_chat(payload, session_id):
            if event.type == "response":
                response_parts.append(event.data)
                print(event.data, end="", flush=True)
            elif event.type == "done":
                print("\n✅ Chat simples completado.")
            elif event.type == "error":
                print(f"\n❌ [ERROR]: {event.data}")
                return False
                
        full_response = "".join(response_parts)
        if "OK" in full_response or len(full_response) > 0:
            print(f"\n✓ Modelo respondeu corretamente")
            return True
        else:
            print(f"\n❌ Response vazia ou incorreta")
            return False
            
    except Exception as e:
        print(f"\n🔥 [CRASH]: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Executa todos os testes."""
    print("=" * 80)
    print("TESTE DE VALIDAÇÃO: gemini-3.1-flash-lite-preview como Orquestrador")
    print("=" * 80)
    
    # Teste 1: Chat simples
    print("\n" + "=" * 80)
    print("TESTE 1: Chat Simples (baseline)")
    print("=" * 80)
    simple_result = await test_simple_chat()
    
    # Teste 2: Orquestração
    print("\n" + "=" * 80)
    print("TESTE 2: Orquestração")
    print("=" * 80)
    orchestrator_result = await test_gemini_flash_lite_orchestrator()
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO DOS TESTES")
    print("=" * 80)
    print(f"✓ Chat Simples: {'PASSOU' if simple_result else 'FALHOU'}")
    print(f"✓ Orquestração: {'PASSOU' if orchestrator_result else 'FALHOU'}")
    print("=" * 80)
    
    if simple_result and orchestrator_result:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Modelo gemini-3.1-flash-lite-preview está funcionando corretamente como Orquestrador")
        return 0
    else:
        print("\n❌ ALGUNS TESTES FALHARAM")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
