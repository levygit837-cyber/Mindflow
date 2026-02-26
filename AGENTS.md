# AGENTS.md

## Escopo
Este repositório está migrando o sistema de agentes para Python. Alterações de agentes devem priorizar `python/omnimind_agents`.

## Regras de manutenção
- Não adicionar nova lógica de orquestração de agentes em TypeScript.
- Qualquer mudança em normalização de stream deve ser acompanhada de testes em `python/tests/test_chat_stream_normalizer.py`.
- Mudanças em segurança de execução shell devem atualizar `python/omnimind_agents/safe_backend.py` e `python/tests/test_safe_backend.py`.
- Mudanças de prompts devem manter módulos separados em `python/omnimind_agents/prompts/tools`.

## Testes obrigatórios para alterações de agentes
- `PYTHONPATH=python python -m unittest discover -s python/tests -p 'test_*.py'`

## Integração
- Frontend/Next.js pode continuar consumindo eventos SSE, mas a lógica de agente deve viver no pacote Python.
