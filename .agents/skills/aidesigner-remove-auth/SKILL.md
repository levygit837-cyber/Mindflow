---
name: aidesigner-remove-auth
description: Remove a autenticacao OAuth do MCP AIDesigner no Codex, verificar se o servidor ficou deslogado e opcionalmente remover a configuracao do servidor MCP. Use quando o usuario quiser desconectar o AIDesigner, limpar credenciais OAuth travadas ou resetar o login do MCP aidesigner.
---

# AIDesigner MCP Logout

Use esta skill para remover a autenticacao OAuth do MCP `aidesigner` no Codex com verificacao segura.

## O Que Esta Skill Sabe

- O servidor MCP do AIDesigner fica configurado em `~/.codex/config.toml`.
- Esse arquivo guarda a definicao do servidor, nao o token OAuth.
- No Linux, o Codex prefere armazenar credenciais OAuth de MCP no keyring do sistema via Secret Service.
- Se o keyring nao estiver disponivel, o binario do Codex indica fallback para um store em `credentials.json`.
- O comando oficial para desautenticar um MCP OAuth e `codex mcp logout <nome>`.

## Fluxo

1. Inspecione o servidor:

```bash
codex mcp get aidesigner
codex mcp list
```

2. Remova somente a autenticacao OAuth:

```bash
codex mcp logout aidesigner
```

3. Verifique o resultado:

```bash
codex mcp list
```

Resultado esperado:

- `aidesigner` continua cadastrado, mas com `Auth: Not logged in`

4. Se o usuario quiser limpeza completa, remova tambem a configuracao do servidor:

```bash
codex mcp remove aidesigner
```

## Script Recomendado

Para executar o fluxo de forma idempotente, use:

```bash
bash .agents/skills/aidesigner-remove-auth/scripts/remove_aidesigner_auth.sh
```

Para remover tambem a entrada do servidor:

```bash
bash .agents/skills/aidesigner-remove-auth/scripts/remove_aidesigner_auth.sh --remove-server
```

## Quando Usar

- Login OAuth do AIDesigner expirou ou ficou inconsistente
- O usuario quer desconectar a conta do AIDesigner do Codex
- E preciso resetar o login antes de rodar `codex mcp login aidesigner`
- O usuario quer limpar credenciais MCP sem apagar outras configuracoes do Codex

## Reautenticacao

Depois da limpeza, para conectar novamente:

```bash
codex mcp login aidesigner
```
