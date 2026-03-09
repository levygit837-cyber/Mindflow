#!/usr/bin/env python3
"""Teste simples para verificar Fase 1 - Memory API Integration."""

def test_memory_api_integration():
    """Testa se a Memory API foi integrada ao router principal."""
    
    print("🔍 Testando Fase 1: Memory API Integration")
    print("=" * 50)
    
    # Ler o router.py diretamente para evitar dependências
    with open('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/router.py', 'r') as f:
        router_content = f.read()
    
    # Verificar se memory_router foi importado
    has_import = 'from mindflow_backend.memory.api.routes import router as memory_router' in router_content
    print(f"✅ Memory router importado: {has_import}")
    
    # Verificar se memory_router foi incluído
    has_include = 'router.include_router(memory_router)' in router_content
    print(f"✅ Memory router incluído: {has_include}")
    
    # Verificar se existe o arquivo de rotas de memória
    import os
    memory_routes_exists = os.path.exists('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/memory/api/routes.py')
    print(f"✅ Arquivo memory/api/routes.py existe: {memory_routes_exists}")
    
    if memory_routes_exists:
        with open('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/memory/api/routes.py', 'r') as f:
            memory_routes_content = f.read()
        
        # Contar endpoints de memória
        endpoint_count = memory_routes_content.count('@router.')
        print(f"✅ Endpoints de memória encontrados: {endpoint_count}")
        
        # Verificar prefixo
        has_prefix = 'prefix="/memory"' in memory_routes_content
        print(f"✅ Prefixo /memory configurado: {has_prefix}")
    
    # Resultado final
    all_checks = has_import and has_include and memory_routes_exists
    print("\n" + "=" * 50)
    if all_checks:
        print("🎉 FASE 1 CONCLUÍDA COM SUCESSO!")
        print("   Memory API foi integrada ao router principal")
        print("   Endpoints disponíveis em: /v1/memory/*")
    else:
        print("❌ FASE 1 INCOMPLETA - Verificar os pontos acima")
    
    return all_checks

if __name__ == "__main__":
    test_memory_api_integration()
