#!/usr/bin/env python3
"""
Gerador de documentação individual para cada diretório.
Cria arquivos separados para cada diretório no formato solicitado.
"""

import os
from pathlib import Path
from typing import Dict, List, Set
import argparse


class IndividualDocumentationGenerator:
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

    def create_individual_directory_docs(self, output_dir: str = "docs_individual") -> None:
        """
        Cria arquivos individuais para cada diretório.
        """
        # Criar diretório de saída
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print(f"\n📝 Criando arquivos individuais em: {output_dir}")
        
        # Criar arquivo para cada diretório
        for directory in sorted(self.directories):
            filename = f"{directory.replace('/', '_')}.md"
            filepath = output_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Documentação do Diretório: {directory}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"## Caminho\n")
                f.write(f"@python/{directory}\n\n")
                
                # Adicionar arquivos Python deste diretório se houver
                if directory in self.python_files:
                    f.write(f"## Arquivos Python ({len(self.python_files[directory])})\n\n")
                    for file in sorted(self.python_files[directory]):
                        f.write(f"@python/{directory}/{file}\n")
                else:
                    f.write(f"## Arquivos Python\n\n")
                    f.write("*Nenhum arquivo Python encontrado neste diretório*\n")
                
                # Adicionar subdiretórios
                subdirs = [d for d in self.directories if d.startswith(directory + "/") and d.count('/') == directory.count('/') + 1]
                if subdirs:
                    f.write(f"\n## Subdiretórios ({len(subdirs)})\n\n")
                    for subdir in sorted(subdirs):
                        f.write(f"@python/{subdir}\n")
            
            print(f"✅ Criado: {filename}")

    def create_main_index(self, output_dir: str = "docs_individual") -> None:
        """
        Cria um arquivo de índice principal.
        """
        output_path = Path(output_dir)
        index_file = output_path / "INDEX.md"
        
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write("# Índice de Documentação Individual\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"## Resumo\n\n")
            f.write(f"- **Total de Diretórios**: {self.stats['total_directories']}\n")
            f.write(f"- **Total de Arquivos Python**: {self.stats['total_python_files']}\n")
            f.write(f"- **Total de Arquivos**: {self.stats['total_files']}\n\n")
            
            f.write("## Diretórios Documentados\n\n")
            
            # Agrupar por nível
            level_1 = [d for d in self.directories if '/' not in d]
            level_2 = {}
            level_3 = {}
            
            for directory in sorted(self.directories):
                parts = directory.split('/')
                if len(parts) == 1:
                    continue  # Já tratado em level_1
                elif len(parts) == 2:
                    parent = parts[0]
                    if parent not in level_2:
                        level_2[parent] = []
                    level_2[parent].append(directory)
                elif len(parts) == 3:
                    parent = parts[0] + '/' + parts[1]
                    if parent not in level_3:
                        level_3[parent] = []
                    level_3[parent].append(directory)
            
            # Nível 1
            for directory in sorted(level_1):
                filename = f"{directory.replace('/', '_')}.md"
                f.write(f"- [{directory}]({filename})\n")
                
                # Nível 2
                if directory in level_2:
                    for subdir in sorted(level_2[directory]):
                        subfilename = f"{subdir.replace('/', '_')}.md"
                        f.write(f"  - [{subdir}]({subfilename})\n")
                        
                        # Nível 3
                        if subdir in level_3:
                            for subsubdir in sorted(level_3[subdir]):
                                subsubfilename = f"{subsubdir.replace('/', '_')}.md"
                                f.write(f"    - [{subsubdir}]({subsubfilename})\n")
        
        print(f"✅ Criado índice: INDEX.md")

    def create_python_files_list(self, output_dir: str = "docs_individual") -> None:
        """
        Cria uma lista completa de todos os arquivos Python.
        """
        output_path = Path(output_dir)
        python_list_file = output_path / "PYTHON_FILES_COMPLETE.md"
        
        with open(python_list_file, 'w', encoding='utf-8') as f:
            f.write("# Lista Completa de Arquivos Python\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Total: {self.stats['total_python_files']} arquivos Python\n\n")
            
            for directory in sorted(self.python_files.keys()):
                f.write(f"## {directory}\n\n")
                for file in sorted(self.python_files[directory]):
                    if directory == "root":
                        f.write(f"@python/{file}\n")
                    else:
                        f.write(f"@python/{directory}/{file}\n")
                f.write("\n")
        
        print(f"✅ Criada lista completa: PYTHON_FILES_COMPLETE.md")


def main():
    """
    Função principal para executar a geração de documentação individual.
    """
    parser = argparse.ArgumentParser(description='Gerador de documentação individual')
    parser.add_argument('--base-path', default='mindflow_backend', help='Caminho base para escanear (default: mindflow_backend)')
    parser.add_argument('--output-dir', default='docs_individual', help='Diretório de saída (default: docs_individual)')
    
    args = parser.parse_args()
    
    print("🚀 Iniciando geração de documentação individual...")
    print(f"📂 Diretório base: {args.base_path}")
    print(f"📁 Diretório de saída: {args.output_dir}")
    print("-" * 50)
    
    generator = IndividualDocumentationGenerator(args.base_path)
    
    # Escanear o diretório base
    base_dir = Path(args.base_path)
    if base_dir.is_dir():
        generator.scan_directory(base_dir)
    else:
        print(f"❌ Erro: Diretório {args.base_path} não encontrado!")
        return
    
    # Gerar documentação individual
    generator.create_individual_directory_docs(args.output_dir)
    generator.create_main_index(args.output_dir)
    generator.create_python_files_list(args.output_dir)
    
    print("\n✅ Documentação individual gerada com sucesso!")
    print(f"📊 Resumo:")
    print(f"   - Diretórios: {generator.stats['total_directories']}")
    print(f"   - Arquivos Python: {generator.stats['total_python_files']}")
    print(f"   - Total de Arquivos: {generator.stats['total_files']}")
    print(f"   - Arquivos gerados: {len(generator.directories) + 2}")


if __name__ == "__main__":
    main()
