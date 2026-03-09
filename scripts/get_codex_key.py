#!/usr/bin/env python3
"""
Script para extrair CodeX API key do arquivo de autenticação do VS Code.
Uso: python scripts/get_codex_key.py
"""

import json
import os
import sys
from pathlib import Path

def get_codex_api_key():
    """Extrai a API key do CodeX do arquivo de autenticação."""
    
    # Path para o arquivo de autenticação do CodeX
    codex_auth_path = Path.home() / ".codex" / "auth.json"
    
    if not codex_auth_path.exists():
        print("❌ Arquivo de autenticação CodeX não encontrado!")
        print(f"   Expected: {codex_auth_path}")
        print("   Execute o VS Code com CodeX para gerar este arquivo.")
        return None
    
    try:
        with open(codex_auth_path, 'r', encoding='utf-8') as f:
            auth_data = json.load(f)
        
        # Extrair a API key do OpenAI (usada pelo CodeX)
        openai_key = auth_data.get("tokens", {}).get("access_token")
        
        if openai_key:
            print("✅ API key do CodeX encontrada!")
            print(f"   Key: {openai_key[:20]}...{openai_key[-10:]}")
            return openai_key
        else:
            print("❌ API key não encontrada no arquivo de autenticação!")
            print("   Verifique se o CodeX está configurado no VS Code.")
            return None
            
    except json.JSONDecodeError:
        print("❌ Erro ao ler arquivo de autenticação do CodeX!")
        print("   O arquivo pode estar corrompido.")
        return None
    except Exception as e:
        print(f"❌ Erro ao processar arquivo de autenticação: {e}")
        return None

def main():
    """Função principal."""
    api_key = get_codex_api_key()
    
    if api_key:
        # Exportar para uso imediato
        print(f"\n🔧 Para configurar no .env:")
        print(f"CODEX_API_KEY={api_key}")
        
        # Opcional: escrever no .env automaticamente
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Atualizar ou adicionar a CODEX_API_KEY
                lines = content.split('\n')
                updated_lines = []
                key_found = False
                
                for line in lines:
                    if line.strip().startswith('CODEX_API_KEY='):
                        updated_lines.append(f'CODEX_API_KEY={api_key}')
                        key_found = True
                    else:
                        updated_lines.append(line)
                
                if not key_found:
                    # Adicionar no final do arquivo
                    updated_lines.append(f'CODEX_API_KEY={api_key}')
                
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(updated_lines))
                
                print(f"\n✅ .env atualizado automaticamente!")
                
            except Exception as e:
                print(f"\n⚠️  Erro ao atualizar .env: {e}")
                print("   Adicione manualmente:")
                print(f"   CODEX_API_KEY={api_key}")

if __name__ == "__main__":
    main()
