"""File utilities for MindFlow backend.

Safe file operations and file system utilities.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import hashlib


def ensure_directory(directory: Union[str, Path]) -> bool:
    """Ensure directory exists, create if necessary."""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except (OSError, PermissionError):
        return False


def safe_filename(filename: str) -> str:
    """Generate safe filename by removing dangerous characters."""
    import re
    
    # Remove path traversal characters
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    # Ensure not empty
    return filename or "unnamed"


def get_file_size(file_path: Union[str, Path]) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(file_path)
    except (FileNotFoundError, OSError):
        return 0


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Get comprehensive file information."""
    try:
        path = Path(file_path)
        stat = path.stat()
        
        return {
            'name': path.name,
            'stem': path.stem,
            'suffix': path.suffix,
            'size': stat.st_size,
            'created': stat.st_ctime,
            'modified': stat.st_mtime,
            'accessed': stat.st_atime,
            'is_file': path.is_file(),
            'is_dir': path.is_dir(),
            'exists': path.exists(),
            'absolute_path': str(path.absolute()),
            'parent': str(path.parent),
        }
    except (FileNotFoundError, OSError):
        return {
            'name': str(file_path),
            'exists': False,
        }


def read_file_safe(
    file_path: Union[str, Path],
    encoding: str = 'utf-8',
    default: str = "",
) -> str:
    """Safely read file content."""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except (FileNotFoundError, IOError, OSError, UnicodeDecodeError):
        return default


def write_file_safe(
    file_path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8',
    create_dirs: bool = True,
) -> bool:
    """Safely write file content."""
    try:
        path = Path(file_path)
        
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return True
    except (IOError, OSError, PermissionError):
        return False


def read_file_bytes_safe(file_path: Union[str, Path], default: bytes = b"") -> bytes:
    """Safely read file as bytes."""
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except (FileNotFoundError, IOError, OSError):
        return default


def write_file_bytes_safe(
    file_path: Union[str, Path],
    content: bytes,
    create_dirs: bool = True,
) -> bool:
    """Safely write file as bytes."""
    try:
        path = Path(file_path)
        
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'wb') as f:
            f.write(content)
        
        return True
    except (IOError, OSError, PermissionError):
        return False


def append_file_safe(
    file_path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8',
    create_dirs: bool = True,
) -> bool:
    """Safely append content to file."""
    try:
        path = Path(file_path)
        
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'a', encoding=encoding) as f:
            f.write(content)
        
        return True
    except (IOError, OSError, PermissionError):
        return False


def copy_file_safe(src: Union[str, Path], dst: Union[str, Path]) -> bool:
    """Safely copy file."""
    try:
        shutil.copy2(src, dst)
        return True
    except (FileNotFoundError, IOError, OSError, PermissionError):
        return False


def move_file_safe(src: Union[str, Path], dst: Union[str, Path]) -> bool:
    """Safely move file."""
    try:
        shutil.move(src, dst)
        return True
    except (FileNotFoundError, IOError, OSError, PermissionError):
        return False


def delete_file_safe(file_path: Union[str, Path]) -> bool:
    """Safely delete file."""
    try:
        os.remove(file_path)
        return True
    except (FileNotFoundError, IOError, OSError, PermissionError):
        return False


def delete_directory_safe(directory: Union[str, Path], recursive: bool = False) -> bool:
    """Safely delete directory."""
    try:
        if recursive:
            shutil.rmtree(directory)
        else:
            os.rmdir(directory)
        return True
    except (FileNotFoundError, IOError, OSError, PermissionError):
        return False


def list_files(
    directory: Union[str, Path],
    pattern: str = "*",
    recursive: bool = False,
    include_dirs: bool = True,
) -> List[Path]:
    """List files in directory matching pattern."""
    try:
        path = Path(directory)
        
        if recursive:
            if include_dirs:
                return list(path.rglob(pattern))
            else:
                return [p for p in path.rglob(pattern) if p.is_file()]
        else:
            if include_dirs:
                return list(path.glob(pattern))
            else:
                return [p for p in path.glob(pattern) if p.is_file()]
    
    except (FileNotFoundError, OSError):
        return []


def find_files(
    directory: Union[str, Path],
    name_pattern: Optional[str] = None,
    content_pattern: Optional[str] = None,
    case_sensitive: bool = True,
    max_depth: Optional[int] = None,
) -> List[Path]:
    """Find files by name or content pattern."""
    import re
    
    results = []
    directory_path = Path(directory)
    
    if not directory_path.exists():
        return results
    
    # Prepare regex patterns
    name_regex = None
    content_regex = None
    
    if name_pattern:
        flags = 0 if case_sensitive else re.IGNORECASE
        name_regex = re.compile(name_pattern, flags)
    
    if content_pattern:
        flags = 0 if case_sensitive else re.IGNORECASE
        content_regex = re.compile(content_pattern, flags)
    
    # Search files
    def search_dir(path: Path, depth: int = 0):
        if max_depth is not None and depth >= max_depth:
            return
        
        try:
            for item in path.iterdir():
                if item.is_file():
                    # Check name pattern
                    if name_regex and not name_regex.search(item.name):
                        continue
                    
                    # Check content pattern
                    if content_regex:
                        try:
                            content = item.read_text(encoding='utf-8', errors='ignore')
                            if not content_regex.search(content):
                                continue
                        except (UnicodeDecodeError, IOError):
                            continue
                    
                    results.append(item)
                
                elif item.is_dir():
                    search_dir(item, depth + 1)
        
        except (PermissionError, OSError):
            pass
    
    search_dir(directory_path)
    return results


def get_file_hash(
    file_path: Union[str, Path],
    algorithm: str = 'sha256',
    chunk_size: int = 8192,
) -> str:
    """Calculate file hash."""
    try:
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    except (FileNotFoundError, IOError, OSError):
        return ""


def compare_files(file1: Union[str, Path], file2: Union[str, Path]) -> bool:
    """Compare two files for equality."""
    try:
        # Quick size check
        if get_file_size(file1) != get_file_size(file2):
            return False
        
        # Content comparison
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            while True:
                chunk1 = f1.read(8192)
                chunk2 = f2.read(8192)
                
                if chunk1 != chunk2:
                    return False
                
                if not chunk1:  # EOF
                    break
        
        return True
    except (FileNotFoundError, IOError, OSError):
        return False


def backup_file(
    file_path: Union[str, Path],
    backup_suffix: Optional[str] = None,
    backup_dir: Optional[Union[str, Path]] = None,
) -> Optional[Path]:
    """Create backup of file."""
    try:
        source = Path(file_path)
        
        if not source.exists():
            return None
        
        if backup_suffix is None:
            import datetime
            backup_suffix = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if backup_dir:
            backup_dir_path = Path(backup_dir)
            backup_dir_path.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir_path / f"{source.stem}_{backup_suffix}{source.suffix}"
        else:
            backup_path = source.parent / f"{source.stem}_{backup_suffix}{source.suffix}"
        
        shutil.copy2(source, backup_path)
        return backup_path
    
    except (IOError, OSError, PermissionError):
        return None


def create_temp_file(
    suffix: str = "",
    prefix: str = "tmp",
    directory: Optional[Union[str, Path]] = None,
    text: bool = True,
) -> Path:
    """Create temporary file."""
    fd, path = tempfile.mkstemp(suffix, prefix, directory, text)
    os.close(fd)
    return Path(path)


def create_temp_directory(
    suffix: str = "",
    prefix: str = "tmp",
    directory: Optional[Union[str, Path]] = None,
) -> Path:
    """Create temporary directory."""
    return Path(tempfile.mkdtemp(suffix, prefix, directory))


def clean_temp_files(max_age_hours: int = 24, pattern: str = "tmp*") -> int:
    """Clean old temporary files."""
    import time
    
    cleaned_count = 0
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    try:
        temp_dir = Path(tempfile.gettempdir())
        
        for item in temp_dir.glob(pattern):
            try:
                if item.is_file() and (current_time - item.stat().st_mtime) > max_age_seconds:
                    item.unlink()
                    cleaned_count += 1
                elif item.is_dir() and (current_time - item.stat().st_mtime) > max_age_seconds:
                    shutil.rmtree(item)
                    cleaned_count += 1
            except (PermissionError, OSError):
                continue
    
    except (OSError, PermissionError):
        pass
    
    return cleaned_count


def get_directory_size(directory: Union[str, Path]) -> int:
    """Get total size of directory in bytes."""
    total_size = 0
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except (FileNotFoundError, OSError):
                    continue
    except (OSError, PermissionError):
        pass
    
    return total_size


def get_directory_info(directory: Union[str, Path]) -> Dict[str, Any]:
    """Get comprehensive directory information."""
    try:
        path = Path(directory)
        
        if not path.exists():
            return {'exists': False}
        
        file_count = 0
        dir_count = 0
        total_size = 0
        
        for root, dirs, files in os.walk(directory):
            dir_count += len(dirs)
            file_count += len(files)
            
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except (FileNotFoundError, OSError):
                    continue
        
        return {
            'name': path.name,
            'path': str(path.absolute()),
            'exists': True,
            'file_count': file_count,
            'directory_count': dir_count,
            'total_size': total_size,
            'is_empty': file_count == 0 and dir_count == 0,
        }
    
    except (OSError, PermissionError):
        return {'exists': False}


def compress_file(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    compression: str = 'gzip',
) -> bool:
    """Compress file."""
    try:
        input_file = Path(input_path)
        
        if output_path is None:
            output_path = input_file.with_suffix(f"{input_file.suffix}.{compression}")
        
        if compression == 'gzip':
            import gzip
            with open(input_file, 'rb') as f_in:
                with gzip.open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        elif compression == 'bz2':
            import bz2
            with open(input_file, 'rb') as f_in:
                with bz2.open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        elif compression == 'lzma':
            import lzma
            with open(input_file, 'rb') as f_in:
                with lzma.open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            return False
        
        return True
    
    except (ImportError, IOError, OSError):
        return False


def decompress_file(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
) -> bool:
    """Decompress file."""
    try:
        input_file = Path(input_path)
        
        # Determine compression type from extension
        compression = None
        if input_file.suffix == '.gz':
            compression = 'gzip'
        elif input_file.suffix == '.bz2':
            compression = 'bz2'
        elif input_file.suffix in ['.xz', '.lzma']:
            compression = 'lzma'
        
        if compression is None:
            return False
        
        if output_path is None:
            # Remove compression extension
            if compression == 'gzip':
                output_path = input_file.with_suffix(input_file.suffix.replace('.gz', ''))
            else:
                output_path = input_file.with_suffix('')
        
        if compression == 'gzip':
            import gzip
            with gzip.open(input_file, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        elif compression == 'bz2':
            import bz2
            with bz2.open(input_file, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        elif compression == 'lzma':
            import lzma
            with lzma.open(input_file, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        
        return True
    
    except (ImportError, IOError, OSError):
        return False


def watch_file(
    file_path: Union[str, Path],
    callback: callable,
    interval: float = 1.0,
) -> None:
    """Simple file watcher (polling-based)."""
    import time
    
    path = Path(file_path)
    last_mtime = path.stat().st_mtime if path.exists() else 0
    
    try:
        while True:
            if path.exists():
                current_mtime = path.stat().st_mtime
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    callback(str(path))
            else:
                if last_mtime != 0:
                    callback(str(path))  # File deleted
                    last_mtime = 0
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        pass


# File size constants
SIZE_BYTES = 1
SIZE_KB = 1024
SIZE_MB = 1024 * 1024
SIZE_GB = 1024 * 1024 * 1024
SIZE_TB = 1024 * 1024 * 1024 * 1024
