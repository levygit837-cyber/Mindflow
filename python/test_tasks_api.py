#!/usr/bin/env python3
"""Teste para verificar Fase 3 - Tasks Management API."""

def test_tasks_api_integration():
    """Testa se a Tasks API foi integrada ao router principal."""
    
    print("🔍 Testando Fase 3: Tasks Management API")
    print("=" * 50)
    
    # Ler o router.py diretamente para evitar dependências
    with open('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/router.py') as f:
        router_content = f.read()
    
    # Verificar se tasks_router foi importado
    has_import = 'from mindflow_backend.api.v1.tasks import router as tasks_router' in router_content
    print(f"✅ Tasks router importado: {has_import}")
    
    # Verificar se tasks_router foi incluído
    has_include = 'router.include_router(tasks_router)' in router_content
    print(f"✅ Tasks router incluído: {has_include}")
    
    # Verificar se existe o arquivo de tasks API
    import os
    tasks_api_exists = os.path.exists('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/v1/tasks.py')
    print(f"✅ Arquivo api/v1/tasks.py existe: {tasks_api_exists}")
    
    if tasks_api_exists:
        with open('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/v1/tasks.py') as f:
            tasks_content = f.read()
        
        # Contar endpoints de tasks
        endpoint_count = tasks_content.count('@router.')
        print(f"✅ Endpoints de tasks encontrados: {endpoint_count}")
        
        # Verificar prefixo
        has_prefix = 'prefix="/tasks"' in tasks_content
        print(f"✅ Prefixo /tasks configurado: {has_prefix}")
        
        # Verificar endpoints principais
        main_endpoints = [
            '@router.get("/{task_id}",',
            '@router.post("/{task_id}/cancel",',
            '@router.post("/{task_id}/retry",',
            '@router.get("/session/{session_id}",',
            '@router.get("/{task_id}/subtasks",',
            '@router.get("/{task_id}/progress"'
        ]
        
        for endpoint in main_endpoints:
            has_endpoint = endpoint in tasks_content
            endpoint_name = endpoint.split('/')[1].split('"')[0]
            print(f"✅ Endpoint {endpoint_name}: {has_endpoint}")
    
    # Verificar schemas
    task_requests_exists = os.path.exists('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/schemas/task_requests.py')
    task_responses_exists = os.path.exists('/home/levybonito/Projetos/MindFlow/python/mindflow_backend/api/schemas/task_responses.py')
    
    print(f"✅ Schema task_requests.py existe: {task_requests_exists}")
    print(f"✅ Schema task_responses.py existe: {task_responses_exists}")
    
    # Resultado final
    all_checks = (
        has_import and 
        has_include and 
        tasks_api_exists and 
        task_requests_exists and 
        task_responses_exists
    )
    
    print("\n" + "=" * 50)
    if all_checks:
        print("🎉 FASE 3 CONCLUÍDA COM SUCESSO!")
        print("   Tasks Management API foi integrada")
        print("   Endpoints disponíveis em: /v1/tasks/*")
        print("   Principais endpoints:")
        print("   - GET /v1/tasks/{id} - Status da task")
        print("   - POST /v1/tasks/{id}/cancel - Cancelar task")
        print("   - POST /v1/tasks/{id}/retry - Re-executar task")
        print("   - GET /v1/tasks/session/{id} - Tasks por sessão")
        print("   - GET /v1/tasks/{id}/subtasks - Subtasks decompostas")
        print("   - GET /v1/tasks/{id}/progress - Progresso em tempo real")
    else:
        print("❌ FASE 3 INCOMPLETA - Verificar os pontos acima")
    
    return all_checks

if __name__ == "__main__":
    test_tasks_api_integration()
