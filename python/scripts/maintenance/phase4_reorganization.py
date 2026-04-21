#!/usr/bin/env python3
"""Phase 4: Reorganize structure and cleanup."""

import re
from pathlib import Path


def fix_corrupted_files(directory: Path) -> int:
    """Fix corrupted files (add line breaks)."""
    fixed_count = 0
    
    for file_path in directory.rglob("*.py"):
        if file_path.name == "__init__.py":
            continue
            
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()
            
            # Check if file is corrupted (all in one line)
            if '\n' not in content and len(content) > 500:
                # Fix by adding line breaks at appropriate places
                fixed_content = fix_single_line_file(content)
                
                if fixed_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    print(f"✅ Fixed {file_path.relative_to(directory)}")
                    fixed_count += 1
                    
        except Exception as e:
            print(f"❌ Error fixing {file_path}: {e}")
    
    return fixed_count

def fix_single_line_file(content: str) -> str:
    """Fix a single-line Python file by adding appropriate line breaks."""
    # Basic fixes for common patterns
    content = re.sub(r'"""', '"""\n', content)
    content = re.sub(r"'''", "'''\n", content)
    content = re.sub(r'from ', '\nfrom ', content)
    content = re.sub(r'import ', '\nimport ', content)
    content = re.sub(r'class ', '\nclass ', content)
    content = re.sub(r'def ', '\ndef ', content)
    content = re.sub(r'    def ', '\n    def ', content)
    content = re.sub(r'        def ', '\n        def ', content)
    content = re.sub(r'# ', '\n# ', content)
    content = re.sub(r'"""', '\n"""', content)
    content = re.sub(r"'''", "\n'''", content)
    content = re.sub(r'if ', '\nif ', content)
    content = re.sub(r'elif ', '\nelif ', content)
    content = re.sub(r'else:', '\nelse:', content)
    content = re.sub(r'except ', '\nexcept ', content)
    content = re.sub(r'finally:', '\nfinally:', content)
    content = re.sub(r'with ', '\nwith ', content)
    content = re.sub(r'for ', '\nfor ', content)
    content = re.sub(r'while ', '\nwhile ', content)
    content = re.sub(r'return ', '\nreturn ', content)
    content = re.sub(r'raise ', '\nraise ', content)
    content = re.sub(r'yield ', '\nyield ', content)
    
    # Clean up multiple empty lines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    return content.strip()

def reorganize_structure():
    """Phase 4: Reorganize structure and cleanup."""
    print("🗂️ Phase 4: Reorganizing Structure")
    
    base_path = Path("mindflow_backend/agents/tools")
    
    # Fix corrupted files
    print("🔧 Fixing corrupted files...")
    fixed_count = fix_corrupted_files(base_path)
    print(f"   Fixed {fixed_count} files")
    
    # Replace unified files with original names
    replacements = [
        ("filesystem/file_operations_unified.py", "filesystem/file_operations.py"),
        ("filesystem/search_tools_unified.py", "filesystem/search_tools.py"),
    ]
    
    replaced_count = 0
    for old_file, new_file in replacements:
        old_path = base_path / old_file
        new_path = base_path / new_file
        
        if old_path.exists():
            if new_path.exists():
                new_path.unlink()
            old_path.rename(new_path)
            print(f"✅ Renamed {old_file} -> {new_file}")
            replaced_count += 1
    
    print("\n📊 Phase 4 Reorganization Summary:")
    print(f"   - Files fixed: {fixed_count}")
    print(f"   - Files renamed: {replaced_count}")
    print("   - Status: Ready for Phase 5")
    
    return fixed_count > 0 or replaced_count > 0

def main():
    """Run Phase 4 reorganization."""
    print("🧪 Starting Phase 4 Reorganization\n")
    
    success = reorganize_structure()
    
    if success:
        print("\n🎉 Phase 4 Reorganization Successful!")
        print("\n📋 Next Steps:")
        print("   - Phase 5: Final cleanup")
        print("   - Remove old /tools directory")
        print("   - Update all imports")
        print("   - Final testing and validation")
    else:
        print("\n⚠️ Phase 4 Reorganization Issues Found")
        print("   - Check file permissions")
        print("   - Verify directory structure")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
