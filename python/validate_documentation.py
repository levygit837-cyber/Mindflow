#!/usr/bin/env python3
"""
Validador final da documentação gerada.
Verifica se todos os diretórios e arquivos foram mapeados corretamente.
"""

import argparse
from pathlib import Path


class DocumentationValidator:
    def __init__(self, base_path: str, docs_path: str):
        self.base_path = Path(base_path)
        self.docs_path = Path(docs_path)
        self.expected_directories: set[str] = set()
        self.expected_files: dict[str, list[str]] = {}
        self.generated_files: set[str] = set()
        self.validation_results = {
            'missing_directories': [],
            'missing_files': [],
            'extra_files': [],
            'total_expected_dirs': 0,
            'total_generated_files': 0,
            'total_expected_files': 0
        }

    def scan_source_structure(self) -> None:
        """
        Escaneia a estrutura original para obter o esperado.
        """
        print("🔍 Escaneando estrutura original...")
        
        def scan_recursive(directory: Path, relative_path: str = ""):
            try:
                for item in directory.iterdir():
                    if item.name.startswith('.') or item.name == '__pycache__':
                        continue

                    current_relative = f"{relative_path}/{item.name}" if relative_path else item.name
                    
                    if item.is_dir():
                        self.expected_directories.add(current_relative)
                        scan_recursive(item, current_relative)
                    elif item.suffix == '.py':
                        dir_path = relative_path if relative_path else "root"
                        if dir_path not in self.expected_files:
                            self.expected_files[dir_path] = []
                        self.expected_files[dir_path].append(item.name)
                        
            except Exception as e:
                print(f"⚠️  Erro ao escanear {directory}: {e}")
        
        scan_recursive(self.base_path)
        self.validation_results['total_expected_dirs'] = len(self.expected_directories)
        self.validation_results['total_expected_files'] = sum(len(files) for files in self.expected_files.values())

    def scan_generated_files(self) -> None:
        """
        Escaneia os arquivos de documentação gerados.
        """
        print("📄 Escaneando arquivos gerados...")
        
        if not self.docs_path.exists():
            print(f"❌ Diretório de documentação não encontrado: {self.docs_path}")
            return
        
        for item in self.docs_path.iterdir():
            if item.is_file() and item.suffix == '.md' and item.name != 'INDEX.md' and item.name != 'PYTHON_FILES_COMPLETE.md':
                self.generated_files.add(item.stem)  # Nome sem extensão
        
        self.validation_results['total_generated_files'] = len(self.generated_files)

    def validate_directory_coverage(self) -> None:
        """
        Verifica se todos os diretórios foram documentados.
        """
        print("📁 Validando cobertura de diretórios...")
        
        for directory in self.expected_directories:
            expected_filename = directory.replace('/', '_')
            if expected_filename not in self.generated_files:
                self.validation_results['missing_directories'].append(directory)
        
        # Verificar arquivos extras
        for generated_file in self.generated_files:
            # Converter nome de arquivo para formato de diretório
            directory = generated_file.replace('_', '/')
            if directory not in self.expected_directories:
                self.validation_results['extra_files'].append(generated_file)

    def validate_file_content(self) -> None:
        """
        Valida o conteúdo dos arquivos gerados.
        """
        print("📝 Validando conteúdo dos arquivos...")
        
        for directory in self.expected_directories:
            filename = directory.replace('/', '_') + '.md'
            filepath = self.docs_path / filename
            
            if not filepath.exists():
                continue
            
            with open(filepath, encoding='utf-8') as f:
                content = f.read()
            
            # Verificar se o caminho está correto
            expected_path = f"@python/{directory}"
            if expected_path not in content:
                self.validation_results['missing_files'].append(f"Path incorreto em {filename}")
            
            # Verificar se os arquivos Python estão listados
            if directory in self.expected_files:
                for py_file in self.expected_files[directory]:
                    expected_file_path = f"@python/{directory}/{py_file}"
                    if expected_file_path not in content:
                        self.validation_results['missing_files'].append(f"Arquivo {py_file} não encontrado em {filename}")

    def generate_validation_report(self) -> str:
        """
        Gera um relatório completo de validação.
        """
        report = [
            "# Relatório de Validação da Documentação",
            "=" * 50,
            "",
            "## Estatísticas Gerais",
            f"- **Diretórios Esperados**: {self.validation_results['total_expected_dirs']}",
            f"- **Arquivos Gerados**: {self.validation_results['total_generated_files']}",
            f"- **Arquivos Python Esperados**: {self.validation_results['total_expected_files']}",
            "",
            "## Resultados da Validação"
        ]
        
        # Cobertura de diretórios
        missing_dirs = len(self.validation_results['missing_directories'])
        if missing_dirs == 0:
            report.append("✅ **Todos os diretórios foram documentados!**")
        else:
            report.append(f"❌ **{missing_dirs} diretórios não documentados:**")
            for directory in self.validation_results['missing_directories']:
                report.append(f"   - {directory}")
        
        # Arquivos extras
        extra_files = len(self.validation_results['extra_files'])
        if extra_files > 0:
            report.append(f"\n⚠️  **{extra_files} arquivos extras gerados:**")
            for file in self.validation_results['extra_files']:
                report.append(f"   - {file}")
        
        # Conteúdo dos arquivos
        missing_content = len(self.validation_results['missing_files'])
        if missing_content == 0:
            report.append("\n✅ **Todo o conteúdo está correto!**")
        else:
            report.append(f"\n❌ **{missing_content} problemas de conteúdo encontrados:**")
            for issue in self.validation_results['missing_files']:
                report.append(f"   - {issue}")
        
        # Resumo final
        total_issues = missing_dirs + extra_files + missing_content
        if total_issues == 0:
            report.append("\n🎉 **Validação concluída com sucesso! Documentação perfeita!**")
        else:
            report.append(f"\n⚠️  **Validação concluída com {total_issues} problemas encontrados.**")
        
        return "\n".join(report)

    def save_validation_report(self, output_file: str = "VALIDATION_REPORT.md") -> None:
        """
        Salva o relatório de validação.
        """
        report = self.generate_validation_report()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📊 Relatório de validação salvo em: {output_file}")


def main():
    """
    Função principal para executar a validação.
    """
    parser = argparse.ArgumentParser(description='Validador de documentação gerada')
    parser.add_argument('--base-path', default='mindflow_backend', help='Caminho base do projeto (default: mindflow_backend)')
    parser.add_argument('--docs-path', default='docs_individual', help='Caminho da documentação (default: docs_individual)')
    parser.add_argument('--output', default='VALIDATION_REPORT.md', help='Arquivo de saída do relatório (default: VALIDATION_REPORT.md)')
    
    args = parser.parse_args()
    
    print("🔍 Iniciando validação da documentação...")
    print(f"📂 Projeto: {args.base_path}")
    print(f"📁 Documentação: {args.docs_path}")
    print("-" * 50)
    
    validator = DocumentationValidator(args.base_path, args.docs_path)
    
    # Executar validação
    validator.scan_source_structure()
    validator.scan_generated_files()
    validator.validate_directory_coverage()
    validator.validate_file_content()
    
    # Gerar relatório
    validator.save_validation_report(args.output)
    
    print("\n✅ Validação concluída!")


if __name__ == "__main__":
    main()
