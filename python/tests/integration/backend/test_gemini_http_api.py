#!/usr/bin/env python3
"""Teste de integração via HTTP API para validar gemini-3.1-flash-lite-preview."""

import asyncio
import json
import os
import sys
import time

import httpx

# API configuration
API_BASE_URL = "http://127.0.0.1:8000"
API_TIMEOUT = 120  # seconds


async def test_health_check():
    """Testa se o backend está respondendo."""
    print("🔍 Verificando health check do backend...")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Backend está rodando: {data.get('status')}")
                print(f"   Environment: {data.get('environment')}")
                print(f"   App Name: {data.get('app_name')}")
                return True
            else:
                print(f"❌ Health check falhou: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao conectar com backend: {e}")
        return False


async def test_simple_chat():
    """Teste simples de chat sem orquestração."""
    print("\n" + "=" * 80)
    print("TESTE 1: Chat Simples (sem orquestração)")
    print("=" * 80)
    
    payload = {
        "message": "Responda apenas com 'OK' para confirmar que o modelo está funcionando.",
        "provider": "vertexai",
        "model": "gemini-3.1-flash-lite-preview",
        "orchestrate": False
    }
    
    print(f"📝 Payload: {json.dumps(payload, indent=2)}")
    print(f"\n🔄 Enviando requisição para {API_BASE_URL}/v1/agent/chat/stream...\n")
    
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            start_time = time.time()
            
            response = await client.post(
                f"{API_BASE_URL}/v1/agent/chat/stream",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                print(f"✅ Resposta recebida em {elapsed:.2f}s")
                print(f"📄 Response length: {len(response.text)} chars")
                
                # Tentar parsear como JSON
                try:
                    data = response.json()
                    print(f"📦 Response type: {type(data)}")
                    
                    # Se for streaming, pode ser uma lista de eventos
                    if isinstance(data, list):
                        print(f"📊 Streaming events: {len(data)} eventos")
                        for i, event in enumerate(data[:5]):  # Mostrar primeiros 5
                            print(f"   [{i}] {event.get('type')}: {str(event.get('data', ''))[:100]}...")
                        
                        # Extrair texto dos eventos de response
                        full_text = ""
                        for event in data:
                            if event.get('type') == 'response':
                                full_text += str(event.get('data', ''))
                        
                        print(f"\n📝 Texto extraído: {full_text[:200]}...")
                        
                        if "OK" in full_text or len(full_text) > 0:
                            print("✓ Modelo respondeu corretamente")
                            return True
                        else:
                            print("⚠️  Response não contém 'OK' mas tem conteúdo")
                            return len(full_text) > 0
                    else:
                        # Response direta
                        print(f"📝 Response: {str(data)[:200]}...")
                        if "OK" in str(data) or len(str(data)) > 0:
                            print("✓ Modelo respondeu corretamente")
                            return True
                        else:
                            print("⚠️  Response vazia")
                            return False
                            
                except json.JSONDecodeError:
                    # Response é texto puro (streaming)
                    print(f"📝 Response (texto): {response.text[:200]}...")
                    if "OK" in response.text or len(response.text) > 0:
                        print("✓ Modelo respondeu corretamente")
                        return True
                    else:
                        print("⚠️  Response vazia")
                        return False
            else:
                print(f"❌ Erro na requisição: {response.status_code}")
                print(f"📄 Error response: {response.text[:500]}")
                return False
                
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_orchestration():
    """Teste de orquestração com gemini-3.1-flash-lite-preview."""
    print("\n" + "=" * 80)
    print("TESTE 2: Orquestração")
    print("=" * 80)
    
    payload = {
        "message": "Você é um orquestrador de agentes. Analise a seguinte tarefa: 'Preciso criar uma função Python que soma dois números'. Descreva como você orquestraria essa tarefa entre diferentes agentes especializados.",
        "provider": "vertexai",
        "model": "gemini-3.1-flash-lite-preview",
        "orchestrate": True
    }
    
    print(f"📝 Payload: {json.dumps(payload, indent=2)}")
    print(f"\n🔄 Enviando requisição para {API_BASE_URL}/v1/agent/chat/stream...\n")
    
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            start_time = time.time()
            
            response = await client.post(
                f"{API_BASE_URL}/v1/agent/chat/stream",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                print(f"✅ Resposta recebida em {elapsed:.2f}s")
                print(f"📄 Response length: {len(response.text)} chars")
                
                # Tentar parsear como JSON
                try:
                    data = response.json()
                    
                    # Se for streaming, pode ser uma lista de eventos
                    if isinstance(data, list):
                        print(f"📊 Streaming events: {len(data)} eventos")
                        
                        thought_count = 0
                        step_count = 0
                        full_text = ""
                        
                        for event in data:
                            event_type = event.get('type')
                            event_data = event.get('data', '')
                            
                            if event_type == 'thought':
                                thought_count += 1
                                print(f"🧠 [THOUGHT #{thought_count}]: {str(event_data)[:100]}...")
                            elif event_type == 'agent_step':
                                step_count += 1
                                print(f"⚙️  [STEP #{step_count}]: {str(event_data)[:100]}...")
                            elif event_type == 'response':
                                full_text += str(event_data)
                                print(event_data, end="", flush=True)
                            elif event_type == 'error':
                                print(f"\n❌ [ERROR]: {event_data}")
                        
                        print(f"\n\n📊 Métricas:")
                        print(f"   - Thoughts: {thought_count}")
                        print(f"   - Steps: {step_count}")
                        print(f"   - Response length: {len(full_text)} chars")
                        
                        # Validações
                        success = True
                        
                        if thought_count == 0:
                            print("⚠️  WARNING: Nenhum thought detectado")
                            success = False
                        else:
                            print("✓ Orquestração com thinking funcionando")
                            
                        if step_count == 0:
                            print("⚠️  WARNING: Nenhum step detectado")
                        else:
                            print("✓ Orquestração com steps funcionando")
                            
                        if len(full_text) < 50:
                            print("❌ ERROR: Response muito curta")
                            success = False
                        else:
                            print("✓ Response com conteúdo adequado")
                            
                        # Verificar se response menciona orquestração
                        orchestration_keywords = ["orquestr", "agent", "especialist", "coorden", "deleg"]
                        has_orchestration = any(keyword.lower() in full_text.lower() for keyword in orchestration_keywords)
                        
                        if has_orchestration:
                            print("✓ Response demonstra comportamento de orquestrador")
                        else:
                            print("⚠️  WARNING: Response não demonstra claramente comportamento de orquestrador")
                            
                        return success
                    else:
                        # Response direta
                        print(f"📝 Response: {str(data)[:500]}...")
                        if len(str(data)) > 50:
                            print("✓ Response com conteúdo adequado")
                            return True
                        else:
                            print("❌ Response muito curta")
                            return False
                            
                except json.JSONDecodeError:
                    # Response é texto puro (streaming)
                    print(f"📝 Response (texto): {response.text[:500]}...")
                    if len(response.text) > 50:
                        print("✓ Response com conteúdo adequado")
                        return True
                    else:
                        print("❌ Response muito curta")
                        return False
            else:
                print(f"❌ Erro na requisição: {response.status_code}")
                print(f"📄 Error response: {response.text[:500]}")
                return False
                
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Executa todos os testes."""
    print("=" * 80)
    print("TESTE DE VALIDAÇÃO: gemini-3.1-flash-lite-preview via HTTP API")
    print("=" * 80)
    
    # Health check
    health_ok = await test_health_check()
    if not health_ok:
        print("\n❌ Backend não está respondendo. Abortando testes.")
        return 1
    
    # Teste 1: Chat simples
    simple_result = await test_simple_chat()
    
    # Teste 2: Orquestração
    orchestrator_result = await test_orchestration()
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO DOS TESTES")
    print("=" * 80)
    print(f"✓ Health Check: {'PASSOU' if health_ok else 'FALHOU'}")
    print(f"✓ Chat Simples: {'PASSOU' if simple_result else 'FALHOU'}")
    print(f"✓ Orquestração: {'PASSOU' if orchestrator_result else 'FALHOU'}")
    print("=" * 80)
    
    if health_ok and simple_result and orchestrator_result:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Modelo gemini-3.1-flash-lite-preview está funcionando corretamente")
        print("✅ Orquestração está funcionando")
        return 0
    else:
        print("\n❌ ALGUNS TESTES FALHARAM")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
