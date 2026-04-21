#!/usr/bin/env python3
"""Teste para verificar Fase 2 - Chains Management API."""

def test_chains_api_integration():
    """Testa se a Chains API foi integrada ao router principal."""
    
    print("🔍 Testando Fase 2: Chains Management API")
    print("=" * 50)
    
    # Ler o router.py diretamente para evitar dependências
    with open('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/router.py') as f:
        router_content = f.read()
    
    # Verificar se chains_router foi importado
    has_import = 'from mindflow_backend.api.v1.chains import router as chains_router' in router_content
    print(f"✅ Chains router importado: {has_import}")
    
    # Verificar se chains_router foi incluído
    has_include = 'router.include_router(chains_router)' in router_content
    print(f"✅ Chains router incluído: {has_include}")
    
    # Verificar se existe o arquivo de chains API
    import os
    chains_api_exists = os.path.exists('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/v1/chains.py')
    print(f"✅ Arquivo api/v1/chains.py existe: {chains_api_exists}")
    
    if chains_api_exists:
        with open('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/v1/chains.py') as f:
            chains_content = f.read()
        
        # Contar endpoints de chains
        endpoint_count = chains_content.count('@router.')
        print(f"✅ Endpoints de chains encontrados: {endpoint_count}")
        
        # Verificar prefixo
        has_prefix = 'prefix="/chains"' in chains_content
        print(f"✅ Prefixo /chains configurado: {has_prefix}")
        
        # Verificar endpoints principais
        main_endpoints = [
            '@router.get("/",',
            '@router.get("/{chain_id}",',
            '@router.post("/{chain_id}/execute",',
            '@router.get("/{chain_id}/stats",',
            '@router.post("/find",',
            '@router.get("/registry/info",'
        ]
        
        for endpoint in main_endpoints:
            has_endpoint = endpoint in chains_content
            print(f"✅ Endpoint {endpoint.split('/')[1]}: {has_endpoint}")
    
    # Verificar schemas
    chain_requests_exists = os.path.exists('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/schemas/chain_requests.py')
    chain_responses_exists = os.path.exists('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/schemas/chain_responses.py')
    
    print(f"✅ Schema chain_requests.py existe: {chain_requests_exists}")
    print(f"✅ Schema chain_responses.py existe: {chain_responses_exists}")
    
    # Resultado final
    all_checks = (
        has_import and 
        has_include and 
        chains_api_exists and 
        chain_requests_exists and 
        chain_responses_exists
    )
    
    print("\n" + "=" * 50)
    if all_checks:
        print("🎉 FASE 2 CONCLUÍDA COM SUCESSO!")
        print("   Chains Management API foi integrada")
        print("   Endpoints disponíveis em: /v1/chains/*")
        print("   Principais endpoints:")
        print("   - GET /v1/chains/ - Listar chains")
        print("   - GET /v1/chains/{id} - Info da chain")
        print("   - POST /v1/chains/{id}/execute - Executar chain")
        print("   - GET /v1/chains/{id}/stats - Estatísticas")
        print("   - POST /v1/chains/find - Encontrar chains")
        print("   - GET /v1/chains/registry/info - Info do registry")
    else:
        print("❌ FASE 2 INCOMPLETA - Verificar os pontos acima")
    
    return all_checks

if __name__ == "__main__":
    test_chains_api_integration()
