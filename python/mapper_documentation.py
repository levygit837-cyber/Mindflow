#!/usr/bin/env python3
"""
Gerador de documentação para estrutura de diretórios e arquivos Python.
Mapeia todos os diretórios e arquivos .py no formato solicitado.
"""

import os
from pathlib import Path
from typing import Dict, List, Set
import argparse


class DocumentationMapper:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.directories: Set[str] = set()
        self.python_files: Dict[str, List[str]] = {}
        self.stats = {
            'total_directories': 0,
            'total_python_files': 0,
            'total_files': 0
        }

    def scan_directory(self, directory: Path, relative_path: str = "") -> None:
        """
        Escaneia recursivamente um diretório para encontrar subdiretórios e arquivos Python.
        """
        try:
            for item in directory.iterdir():
                # Ignorar diretórios que começam com . e __pycache__
                if item.name.startswith('.') or item.name == '__pycache__':
                    continue

                current_relative = f"{relative_path}/{item.name}" if relative_path else item.name
                
                if item.is_dir():
                    self.directories.add(current_relative)
                    self.stats['total_directories'] += 1
                    print(f"📁 Mapeando diretório: {current_relative}")
                    
                    # Escanear subdiretório
                    self.scan_directory(item, current_relative)
                    
                elif item.suffix == '.py':
                    # Adicionar arquivo Python ao diretório correspondente
                    dir_path = relative_path if relative_path else "root"
                    if dir_path not in self.python_files:
                        self.python_files[dir_path] = []
                    self.python_files[dir_path].append(item.name)
                    self.stats['total_python_files'] += 1
                    print(f"📄 Arquivo Python encontrado: {current_relative}")
                
                self.stats['total_files'] += 1
                
        except PermissionError:
            print(f"⚠️  Sem permissão para acessar: {directory}")
        except Exception as e:
            print(f"❌ Erro ao escanear {directory}: {e}")

    def generate_directory_docs(self) -> str:
        """
        Gera documentação para diretórios no formato @python/path.
        """
        docs = ["# Estrutura de Diretórios\n"]
        docs.append("## Diretórios Mapeados\n")
        
        for directory in sorted(self.directories):
            docs.append(f"@python/{directory}")
        
        return "\n".join(docs)

    def generate_file_docs(self) -> str:
        """
        Gera documentação para arquivos Python organizados por diretório.
        """
        docs = ["\n# Arquivos Python\n"]
        docs.append("## Arquivos Mapeados por Diretório\n")
        
        for directory in sorted(self.python_files.keys()):
            docs.append(f"\n### {directory}\n")
            for file in sorted(self.python_files[directory]):
                if directory == "root":
                    docs.append(f"@python/{file}")
                else:
                    docs.append(f"@python/{directory}/{file}")
        
        return "\n".join(docs)

    def generate_stats(self) -> str:
        """
        Gera estatísticas do mapeamento.
        """
        stats = [
            "\n# Estatísticas do Mapeamento\n",
            f"- **Total de Diretórios**: {self.stats['total_directories']}",
            f"- **Total de Arquivos Python**: {self.stats['total_python_files']}",
            f"- **Total de Arquivos**: {self.stats['total_files']}",
            f"- **Diretórios com Arquivos Python**: {len(self.python_files)}"
        ]
        
        return "\n".join(stats)

    def validate_structure(self) -> List[str]:
        """
        Valida a estrutura encontrada e retorna possíveis problemas.
        """
        validations = []
        issues = []
        
        # Verificar se há diretórios vazios
        for directory in sorted(self.directories):
            if directory not in self.python_files:
                issues.append(f"Diretório sem arquivos Python: {directory}")
        
        # Verificar arquivos órfãos (fora de diretórios conhecidos)
        python_files_flat = []
        for files in self.python_files.values():
            python_files_flat.extend(files)
        
        if issues:
            validations.append("## ⚠️ Problemas Encontrados:\n")
            validations.extend(f"- {issue}" for issue in issues)
        else:
            validations.append("## ✅ Validação: Estrutura consistente!\n")
        
        return "\n".join(validations)

    def generate_complete_documentation(self) -> str:
        """
        Gera a documentação completa.
        """
        docs = [
            "# Documentação da Estrutura do Projeto MindFlow Backend",
            "=" * 50,
            self.generate_directory_docs(),
            self.generate_file_docs(),
            self.generate_stats(),
            self.validate_structure()
        ]
        
        return "\n".join(docs)

    def save_documentation(self, output_file: str = "STRUCTURE_DOCUMENTATION.md") -> None:
        """
        Salva a documentação em um arquivo.
        """
        documentation = self.generate_complete_documentation()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(documentation)
        
        print(f"\n📝 Documentação salva em: {output_file}")
        print(f"📊 Resumo:")
        print(f"   - Diretórios: {self.stats['total_directories']}")
        print(f"   - Arquivos Python: {self.stats['total_python_files']}")
        print(f"   - Total de Arquivos: {self.stats['total_files']}")


def main():
    """
    Função principal para executar o mapeamento.
    """
    parser = argparse.ArgumentParser(description='Gerador de documentação para estrutura Python')
    parser.add_argument('--base-path', default='.', help='Caminho base para escanear (default: .)')
    parser.add_argument('--output', default='STRUCTURE_DOCUMENTATION.md', help='Arquivo de saída (default: STRUCTURE_DOCUMENTATION.md)')
    
    args = parser.parse_args()
    
    print("🚀 Iniciando mapeamento da estrutura Python...")
    print(f"📂 Diretório base: {args.base_path}")
    print(f"📄 Arquivo de saída: {args.output}")
    print("-" * 50)
    
    mapper = DocumentationMapper(args.base_path)
    
    # Escanear o diretório base
    base_dir = Path(args.base_path)
    if base_dir.is_dir():
        mapper.scan_directory(base_dir)
    else:
        print(f"❌ Erro: Diretório {args.base_path} não encontrado!")
        return
    
    # Gerar e salvar documentação
    mapper.save_documentation(args.output)
    
    print("\n✅ Mapeamento concluído com sucesso!")


if __name__ == "__main__":
    main()
