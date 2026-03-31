"""Base64 utilities for MindFlow backend.

Functions for Base64 encoding/decoding and related operations.
"""

import base64
import os


def encode_base64(data: str | bytes, encoding: str = 'utf-8') -> str:
    """Encode data to Base64 string."""
    if isinstance(data, str):
        data = data.encode(encoding)
    
    return base64.b64encode(data).decode('ascii')


def decode_base64(base64_str: str, encoding: str = 'utf-8') -> bytes:
    """Decode Base64 string to bytes."""
    return base64.b64decode(base64_str)


def decode_base64_to_string(base64_str: str, encoding: str = 'utf-8') -> str:
    """Decode Base64 string to string."""
    bytes_data = decode_base64(base64_str)
    return bytes_data.decode(encoding)


def encode_base64_url_safe(data: str | bytes, encoding: str = 'utf-8') -> str:
    """Encode data to URL-safe Base64 string."""
    if isinstance(data, str):
        data = data.encode(encoding)
    
    return base64.urlsafe_b64encode(data).decode('ascii')


def decode_base64_url_safe(base64_str: str, encoding: str = 'utf-8') -> bytes:
    """Decode URL-safe Base64 string to bytes."""
    return base64.urlsafe_b64decode(base64_str)


def decode_base64_url_safe_to_string(base64_str: str, encoding: str = 'utf-8') -> str:
    """Decode URL-safe Base64 string to string."""
    bytes_data = decode_base64_url_safe(base64_str)
    return bytes_data.decode(encoding)


def is_valid_base64(base64_str: str) -> bool:
    """Check if string is valid Base64."""
    try:
        base64.b64decode(base64_str, validate=True)
        return True
    except (base64.binascii.Error, ValueError):
        return False


def is_valid_base64_url_safe(base64_str: str) -> bool:
    """Check if string is valid URL-safe Base64."""
    try:
        base64.urlsafe_b64decode(base64_str, validate=True)
        return True
    except (base64.binascii.Error, ValueError):
        return False


def encode_file_base64(file_path: str, chunk_size: int = 8192) -> str:
    """Encode file to Base64 string."""
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        return encode_base64(file_data)
    except (FileNotFoundError, OSError):
        return ""


def decode_file_base64(base64_str: str, output_path: str) -> bool:
    """Decode Base64 string to file."""
    try:
        file_data = decode_base64(base64_str)
        with open(output_path, 'wb') as f:
            f.write(file_data)
        return True
    except (OSError, ValueError):
        return False


def encode_base64_with_padding(data: str | bytes, encoding: str = 'utf-8') -> str:
    """Encode data to Base64 with proper padding."""
    if isinstance(data, str):
        data = data.encode(encoding)
    
    encoded = base64.b64encode(data).decode('ascii')
    
    # Add padding if needed
    padding_needed = (4 - len(encoded) % 4) % 4
    if padding_needed:
        encoded += '=' * padding_needed
    
    return encoded


def remove_base64_padding(base64_str: str) -> str:
    """Remove padding from Base64 string."""
    return base64_str.rstrip('=')


def add_base64_padding(base64_str: str) -> str:
    """Add padding to Base64 string."""
    padding_needed = (4 - len(base64_str) % 4) % 4
    return base64_str + ('=' * padding_needed)


def encode_base64_chunked(data: str | bytes, chunk_size: int = 76, encoding: str = 'utf-8') -> list[str]:
    """Encode data to Base64 in chunks."""
    if isinstance(data, str):
        data = data.encode(encoding)
    
    encoded = base64.b64encode(data).decode('ascii')
    
    # Split into chunks
    chunks = [encoded[i:i + chunk_size] for i in range(0, len(encoded), chunk_size)]
    return chunks


def decode_base64_chunked(chunks: list[str]) -> str:
    """Decode Base64 chunks back to original string."""
    combined = ''.join(chunks)
    return decode_base64_to_string(combined)


def generate_base64_token(length: int = 32, url_safe: bool = False) -> str:
    """Generate random Base64 token."""
    random_bytes = os.urandom(length)
    
    if url_safe:
        return base64.urlsafe_b64encode(random_bytes).decode('ascii').rstrip('=')
    else:
        return base64.b64encode(random_bytes).decode('ascii').rstrip('=')


def base64_to_hex(base64_str: str) -> str:
    """Convert Base64 string to hex string."""
    try:
        bytes_data = decode_base64(base64_str)
        return bytes_data.hex()
    except ValueError:
        return ""


def hex_to_base64(hex_str: str) -> str:
    """Convert hex string to Base64 string."""
    try:
        bytes_data = bytes.fromhex(hex_str)
        return encode_base64(bytes_data)
    except ValueError:
        return ""


def calculate_base64_size(original_size: int) -> int:
    """Calculate Base64 encoded size from original size."""
    return ((original_size + 2) // 3) * 4


def calculate_original_size(base64_size: int) -> int:
    """Calculate original size from Base64 size."""
    return (base64_size * 3) // 4


def compress_and_encode_base64(data: str | bytes, encoding: str = 'utf-8') -> str:
    """Compress data and encode to Base64."""
    try:
        import gzip
        
        if isinstance(data, str):
            data = data.encode(encoding)
        
        compressed = gzip.compress(data)
        return encode_base64(compressed)
    except ImportError:
        # Fallback to regular Base64 if gzip not available
        return encode_base64(data, encoding)


def decode_and_decompress_base64(base64_str: str, encoding: str = 'utf-8') -> str:
    """Decode Base64 and decompress data."""
    try:
        import gzip
        
        compressed = decode_base64(base64_str)
        decompressed = gzip.decompress(compressed)
        return decompressed.decode(encoding)
    except ImportError:
        # Fallback to regular Base64 decode if gzip not available
        return decode_base64_to_string(base64_str, encoding)


def encode_base64_mime(data: str | bytes, encoding: str = 'utf-8', line_length: int = 76) -> str:
    """Encode data to MIME Base64 format with line breaks."""
    if isinstance(data, str):
        data = data.encode(encoding)
    
    encoded = base64.b64encode(data).decode('ascii')
    
    # Add line breaks
    lines = [encoded[i:i + line_length] for i in range(0, len(encoded), line_length)]
    return '\n'.join(lines)


def decode_base64_mime(mime_str: str, encoding: str = 'utf-8') -> str:
    """Decode MIME Base64 format."""
    # Remove line breaks and whitespace
    clean_str = ''.join(mime_str.split())
    return decode_base64_to_string(clean_str, encoding)


def base64_encode_json(data: dict, indent: int | None = None) -> str:
    """Encode JSON object to Base64 string."""
    import json
    
    json_str = json.dumps(data, indent=indent, default=str)
    return encode_base64(json_str)


def base64_decode_json(base64_str: str) -> dict:
    """Decode Base64 string to JSON object."""
    import json
    
    json_str = decode_base64_to_string(base64_str)
    return json.loads(json_str)


def create_base64_header(data: dict) -> str:
    """Create Base64 header (common in JWT)."""
    return base64_encode_json(data)


def parse_base64_header(base64_str: str) -> dict:
    """Parse Base64 header."""
    return base64_decode_json(base64_str)


def base64_encode_binary(data: bytes) -> str:
    """Encode binary data to Base64."""
    return base64.b64encode(data).decode('ascii')


def base64_decode_binary(base64_str: str) -> bytes:
    """Decode Base64 to binary data."""
    return base64.b64decode(base64_str)


def mask_base64(base64_str: str, visible_chars: int = 4, mask_char: str = "*") -> str:
    """Mask Base64 string for display."""
    if len(base64_str) <= visible_chars:
        return base64_str
    
    visible_start = visible_chars // 2
    visible_end = visible_chars - visible_start
    
    masked_middle = mask_char * (len(base64_str) - visible_start - visible_end)
    
    return base64_str[:visible_start] + masked_middle + base64_str[-visible_end:]


def get_base64_info(base64_str: str) -> dict:
    """Get information about Base64 string."""
    try:
        decoded_bytes = decode_base64(base64_str)
        
        return {
            'original_size': len(decoded_bytes),
            'encoded_size': len(base64_str),
            'is_valid': is_valid_base64(base64_str),
            'has_padding': base64_str.endswith('='),
            'padding_count': base64_str.count('='),
            'encoding_ratio': len(base64_str) / len(decoded_bytes) if decoded_bytes else 0,
        }
    except ValueError:
        return {
            'original_size': 0,
            'encoded_size': len(base64_str),
            'is_valid': False,
            'has_padding': False,
            'padding_count': 0,
            'encoding_ratio': 0,
        }


def base64_url_encode_dict(data: dict, encoding: str = 'utf-8') -> str:
    """URL-safe encode dictionary to Base64."""
    import json
    
    json_str = json.dumps(data, separators=(',', ':'), default=str)
    return encode_base64_url_safe(json_str, encoding)


def base64_url_decode_dict(base64_str: str, encoding: str = 'utf-8') -> dict:
    """URL-safe decode Base64 to dictionary."""
    import json
    
    # Add padding if needed
    padded_str = add_base64_padding(base64_str)
    json_str = decode_base64_url_safe_to_string(padded_str, encoding)
    return json.loads(json_str)


# Common Base64 constants
BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
BASE64_URL_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
BASE64_PADDING = "="
