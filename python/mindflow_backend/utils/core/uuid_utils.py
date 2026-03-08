"""UUID utilities for MindFlow backend.

Functions for generating, validating, and manipulating UUIDs.
"""

import uuid
from typing import Optional, Union


def generate_uuid(version: int = 4) -> str:
    """Generate a UUID of specified version."""
    if version == 1:
        return str(uuid.uuid1())
    elif version == 3:
        return str(uuid.uuid3(uuid.NAMESPACE_DNS, 'default'))
    elif version == 4:
        return str(uuid.uuid4())
    elif version == 5:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, 'default'))
    else:
        raise ValueError(f"Unsupported UUID version: {version}")


def generate_uuid1(node: Optional[int] = None, clock_seq: Optional[int] = None) -> str:
    """Generate a UUID1 (timestamp-based)."""
    return str(uuid.uuid1(node, clock_seq))


def generate_uuid3(namespace: uuid.UUID, name: str) -> str:
    """Generate a UUID3 (MD5 hash-based)."""
    return str(uuid.uuid3(namespace, name))


def generate_uuid4() -> str:
    """Generate a UUID4 (random)."""
    return str(uuid.uuid4())


def generate_uuid5(namespace: uuid.UUID, name: str) -> str:
    """Generate a UUID5 (SHA-1 hash-based)."""
    return str(uuid.uuid5(namespace, name))


def generate_uuid_from_string(text: str, version: int = 5) -> str:
    """Generate UUID from string using specified version."""
    if version == 3:
        return str(uuid.uuid3(uuid.NAMESPACE_DNS, text))
    elif version == 5:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, text))
    else:
        raise ValueError(f"Only versions 3 and 5 support string-based generation")


def is_valid_uuid(uuid_str: str) -> bool:
    """Check if string is a valid UUID."""
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False


def normalize_uuid(uuid_str: str) -> str:
    """Normalize UUID to standard format."""
    try:
        return str(uuid.UUID(uuid_str))
    except ValueError:
        return uuid_str


def get_uuid_version(uuid_str: str) -> Optional[int]:
    """Get UUID version."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return uuid_obj.version
    except ValueError:
        return None


def get_uuid_variant(uuid_str: str) -> Optional[str]:
    """Get UUID variant."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return uuid_obj.variant
    except ValueError:
        return None


def get_uuid_fields(uuid_str: str) -> Optional[dict]:
    """Get UUID fields (for UUID1)."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
        
        if uuid_obj.version == 1:
            return {
                'time_low': uuid_obj.time_low,
                'time_mid': uuid_obj.time_mid,
                'time_hi_version': uuid_obj.time_hi_version,
                'clock_seq_hi_variant': uuid_obj.clock_seq_hi_variant,
                'clock_seq_low': uuid_obj.clock_seq_low,
                'node': uuid_obj.node.hex,
                'time': uuid_obj.time,
                'clock_seq': uuid_obj.clock_seq,
            }
        else:
            return None
    except ValueError:
        return None


def get_uuid_time(uuid_str: str) -> Optional[float]:
    """Get timestamp from UUID1."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
        if uuid_obj.version == 1:
            return uuid_obj.time
        return None
    except ValueError:
        return None


def compare_uuids(uuid1: str, uuid2: str) -> int:
    """Compare two UUIDs."""
    try:
        u1 = uuid.UUID(uuid1)
        u2 = uuid.UUID(uuid2)
        
        if u1 < u2:
            return -1
        elif u1 > u2:
            return 1
        else:
            return 0
    except ValueError:
        return 0


def uuid_to_bytes(uuid_str: str) -> Optional[bytes]:
    """Convert UUID to bytes."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return uuid_obj.bytes
    except ValueError:
        return None


def uuid_from_bytes(uuid_bytes: bytes) -> str:
    """Convert bytes to UUID."""
    try:
        uuid_obj = uuid.UUID(bytes=uuid_bytes)
        return str(uuid_obj)
    except ValueError:
        return ""


def uuid_to_int(uuid_str: str) -> Optional[int]:
    """Convert UUID to integer."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return uuid_obj.int
    except ValueError:
        return None


def uuid_from_int(uuid_int: int) -> str:
    """Convert integer to UUID."""
    try:
        uuid_obj = uuid.UUID(int=uuid_int)
        return str(uuid_obj)
    except ValueError:
        return ""


def get_short_uuid(uuid_str: Optional[str] = None, length: int = 8) -> str:
    """Get short UUID."""
    if uuid_str is None:
        uuid_str = generate_uuid4()
    
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return uuid_obj.hex[:length]
    except ValueError:
        return uuid_str[:length]


def encode_uuid(uuid_str: str, encoding: str = 'base64') -> Optional[str]:
    """Encode UUID using specified encoding."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
        uuid_bytes = uuid_obj.bytes
        
        if encoding == 'base64':
            import base64
            return base64.b64encode(uuid_bytes).decode('ascii')
        elif encoding == 'hex':
            return uuid_obj.hex
        elif encoding == 'base32':
            import base64
            return base64.b32encode(uuid_bytes).decode('ascii')
        else:
            return None
    except ValueError:
        return None


def decode_uuid(encoded_uuid: str, encoding: str = 'base64') -> Optional[str]:
    """Decode encoded UUID."""
    try:
        if encoding == 'base64':
            import base64
            uuid_bytes = base64.b64decode(encoded_uuid)
        elif encoding == 'hex':
            uuid_bytes = bytes.fromhex(encoded_uuid)
        elif encoding == 'base32':
            import base64
            uuid_bytes = base64.b32decode(encoded_uuid)
        else:
            return None
        
        uuid_obj = uuid.UUID(bytes=uuid_bytes)
        return str(uuid_obj)
    except (ValueError, TypeError):
        return None


def generate_uuid_namespace(name: str) -> uuid.UUID:
    """Generate a namespace UUID from name."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, name)


def generate_time_based_uuid(name: Optional[str] = None) -> str:
    """Generate time-based UUID with optional name."""
    if name:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{name}:{uuid.uuid1().time}"))
    else:
        return str(uuid.uuid1())


def is_nil_uuid(uuid_str: str) -> bool:
    """Check if UUID is nil (all zeros)."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return uuid_obj == uuid.NIL
    except ValueError:
        return False


def is_max_uuid(uuid_str: str) -> bool:
    """Check if UUID is max (all ones)."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return uuid_obj.int == 0xffffffffffffffffffffffffffffffff
    except ValueError:
        return False


def get_uuid_info(uuid_str: str) -> dict:
    """Get comprehensive UUID information."""
    try:
        uuid_obj = uuid.UUID(uuid_str)
        
        info = {
            'uuid': str(uuid_obj),
            'version': uuid_obj.version,
            'variant': uuid_obj.variant,
            'hex': uuid_obj.hex,
            'int': uuid_obj.int,
            'urn': uuid_obj.urn,
            'is_nil': uuid_obj == uuid.NIL,
            'is_max': uuid_obj.int == 0xffffffffffffffffffffffffffffffff,
        }
        
        if uuid_obj.version == 1:
            info.update({
                'time': uuid_obj.time,
                'clock_seq': uuid_obj.clock_seq,
                'node': uuid_obj.node.hex,
            })
        
        return info
    except ValueError:
        return {
            'uuid': uuid_str,
            'valid': False,
            'error': 'Invalid UUID format',
        }


def batch_generate_uuids(count: int, version: int = 4) -> list[str]:
    """Generate multiple UUIDs."""
    return [generate_uuid(version) for _ in range(count)]


def deduplicate_uuids(uuid_list: list[str]) -> list[str]:
    """Remove duplicate UUIDs from list."""
    seen = set()
    unique_uuids = []
    
    for uuid_str in uuid_list:
        try:
            uuid_obj = uuid.UUID(uuid_str)
            if uuid_obj not in seen:
                seen.add(uuid_obj)
                unique_uuids.append(uuid_str)
        except ValueError:
            if uuid_str not in seen:
                seen.add(uuid_str)
                unique_uuids.append(uuid_str)
    
    return unique_uuids


def sort_uuids(uuid_list: list[str], reverse: bool = False) -> list[str]:
    """Sort UUIDs."""
    try:
        uuid_objects = [(uuid.UUID(u), u) for u in uuid_list]
        uuid_objects.sort(key=lambda x: x[0], reverse=reverse)
        return [u for _, u in uuid_objects]
    except ValueError:
        # Fallback to string sorting if invalid UUIDs
        return sorted(uuid_list, reverse=reverse)


def create_uuid_from_components(
    time_low: int,
    time_mid: int,
    time_hi_version: int,
    clock_seq_hi_variant: int,
    clock_seq_low: int,
    node: str,
) -> str:
    """Create UUID from individual components."""
    try:
        node_bytes = bytes.fromhex(node)
        uuid_obj = uuid.UUID(
            fields=(
                time_low,
                time_mid,
                time_hi_version,
                clock_seq_hi_variant,
                clock_seq_low,
                node_bytes,
            )
        )
        return str(uuid_obj)
    except ValueError:
        return ""


# Common namespace constants
NAMESPACE_DNS = uuid.NAMESPACE_DNS
NAMESPACE_URL = uuid.NAMESPACE_URL
NAMESPACE_OID = uuid.NAMESPACE_OID
NAMESPACE_X500 = uuid.NAMESPACE_X500
