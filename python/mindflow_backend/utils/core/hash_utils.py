"""Hash utilities for MindFlow backend.

Functions for hashing, checksums, and integrity verification.
"""

import hashlib
import hmac
import os
from typing import Optional, Union


def hash_string(
    data: str,
    algorithm: str = 'sha256',
    encoding: str = 'utf-8',
    salt: Optional[str] = None,
) -> str:
    """Hash string using specified algorithm."""
    if salt:
        data = salt + data
    
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data.encode(encoding))
    return hash_obj.hexdigest()


def hash_bytes(data: bytes, algorithm: str = 'sha256') -> str:
    """Hash bytes using specified algorithm."""
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()


def hash_file(
    file_path: str,
    algorithm: str = 'sha256',
    chunk_size: int = 8192,
    encoding: str = 'utf-8',
) -> str:
    """Hash file contents using specified algorithm."""
    hash_obj = hashlib.new(algorithm)
    
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except (FileNotFoundError, IOError, OSError) as exc:
        return ""


def hash_file_stream(
    file_obj,
    algorithm: str = 'sha256',
    chunk_size: int = 8192,
) -> str:
    """Hash file stream using specified algorithm."""
    hash_obj = hashlib.new(algorithm)
    
    # Reset file pointer to beginning
    file_obj.seek(0)
    
    while chunk := file_obj.read(chunk_size):
        hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def generate_salt(length: int = 32) -> str:
    """Generate random salt for hashing."""
    return os.urandom(length).hex()


def hash_with_salt(
    data: str,
    salt: Optional[str] = None,
    algorithm: str = 'sha256',
    encoding: str = 'utf-8',
) -> tuple[str, str]:
    """Hash data with salt, returning hash and salt."""
    if salt is None:
        salt = generate_salt()
    
    hash_value = hash_string(data, algorithm, encoding, salt)
    return hash_value, salt


def verify_hash_with_salt(
    data: str,
    hash_value: str,
    salt: str,
    algorithm: str = 'sha256',
    encoding: str = 'utf-8',
) -> bool:
    """Verify data hash against stored hash and salt."""
    computed_hash = hash_string(data, algorithm, encoding, salt)
    return hmac.compare_digest(computed_hash, hash_value)


def hmac_hash(
    data: str,
    key: str,
    algorithm: str = 'sha256',
    encoding: str = 'utf-8',
) -> str:
    """Generate HMAC hash."""
    hmac_obj = hmac.new(
        key.encode(encoding),
        data.encode(encoding),
        algorithm
    )
    return hmac_obj.hexdigest()


def verify_hmac(
    data: str,
    signature: str,
    key: str,
    algorithm: str = 'sha256',
    encoding: str = 'utf-8',
) -> bool:
    """Verify HMAC signature."""
    computed_signature = hmac_hash(data, key, algorithm, encoding)
    return hmac.compare_digest(computed_signature, signature)


def hash_password(
    password: str,
    salt: Optional[str] = None,
    iterations: int = 100000,
    algorithm: str = 'sha256',
) -> tuple[str, str]:
    """Hash password using PBKDF2."""
    if salt is None:
        salt = generate_salt()
    
    password_bytes = password.encode('utf-8')
    salt_bytes = bytes.fromhex(salt)
    
    hash_bytes = hashlib.pbkdf2_hmac(
        algorithm,
        password_bytes,
        salt_bytes,
        iterations,
        dklen=32
    )
    
    return hash_bytes.hex(), salt


def verify_password(
    password: str,
    hash_value: str,
    salt: str,
    iterations: int = 100000,
    algorithm: str = 'sha256',
) -> bool:
    """Verify password hash."""
    try:
        computed_hash, _ = hash_password(password, salt, iterations, algorithm)
        return hmac.compare_digest(computed_hash, hash_value)
    except Exception:
        return False


def generate_checksum(data: Union[str, bytes], algorithm: str = 'md5') -> str:
    """Generate checksum for data."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    return hash_bytes(data, algorithm)


def verify_checksum(
    data: Union[str, bytes],
    expected_checksum: str,
    algorithm: str = 'md5',
) -> bool:
    """Verify data checksum."""
    actual_checksum = generate_checksum(data, algorithm)
    return hmac.compare_digest(actual_checksum, expected_checksum)


def compute_file_checksums(file_path: str) -> dict[str, str]:
    """Compute multiple checksums for file."""
    algorithms = ['md5', 'sha1', 'sha256', 'sha512']
    checksums = {}
    
    for algorithm in algorithms:
        checksums[algorithm] = hash_file(file_path, algorithm)
    
    return checksums


def hash_dict(data: dict, algorithm: str = 'sha256', sort_keys: bool = True) -> str:
    """Hash dictionary representation."""
    import json
    
    # Convert to JSON string
    json_str = json.dumps(data, sort_keys=sort_keys, default=str)
    
    return hash_string(json_str, algorithm)


def hash_list(data: list, algorithm: str = 'sha256') -> str:
    """Hash list representation."""
    import json
    
    # Convert to JSON string
    json_str = json.dumps(data, default=str)
    
    return hash_string(json_str, algorithm)


def murmurhash3(data: Union[str, bytes], seed: int = 0) -> int:
    """Generate MurmurHash3 hash (32-bit)."""
    try:
        import mmh3
        if isinstance(data, str):
            data = data.encode('utf-8')
        return mmh3.hash(data, seed)
    except ImportError:
        # Fallback to regular hash if mmh3 not available
        return hash(data)


def xxhash(data: Union[str, bytes], seed: int = 0) -> int:
    """Generate xxHash hash."""
    try:
        import xxhash
        if isinstance(data, str):
            data = data.encode('utf-8')
        return xxhash.xxh32(data, seed).intdigest()
    except ImportError:
        # Fallback to regular hash if xxhash not available
        return hash(data)


def blake2b_hash(
    data: Union[str, bytes],
    digest_size: int = 32,
    key: Optional[bytes] = None,
    salt: Optional[bytes] = None,
) -> str:
    """Generate BLAKE2b hash."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    hash_obj = hashlib.blake2b(
        digest_size=digest_size,
        key=key,
        salt=salt
    )
    hash_obj.update(data)
    return hash_obj.hexdigest()


def blake2s_hash(
    data: Union[str, bytes],
    digest_size: int = 32,
    key: Optional[bytes] = None,
    salt: Optional[bytes] = None,
) -> str:
    """Generate BLAKE2s hash."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    hash_obj = hashlib.blake2s(
        digest_size=digest_size,
        key=key,
        salt=salt
    )
    hash_obj.update(data)
    return hash_obj.hexdigest()


def sha3_hash(data: Union[str, bytes], variant: int = 256) -> str:
    """Generate SHA-3 hash."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    algorithm_map = {
        224: 'sha3_224',
        256: 'sha3_256',
        384: 'sha3_384',
        512: 'sha3_512',
    }
    
    algorithm = algorithm_map.get(variant, 'sha3_256')
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()


def shake_hash(
    data: Union[str, bytes],
    digest_size: int = 32,
    variant: int = 128,
) -> str:
    """Generate SHAKE hash."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    algorithm_map = {
        128: 'shake_128',
        256: 'shake_256',
    }
    
    algorithm = algorithm_map.get(variant, 'shake_128')
    hash_obj = hashlib.new(algorithm, digest_size=digest_size)
    hash_obj.update(data)
    return hash_obj.hexdigest()


def create_hash_chain(
    data: str,
    length: int = 10,
    algorithm: str = 'sha256',
) -> list[str]:
    """Create hash chain (hash of hash)."""
    chain = [hash_string(data, algorithm)]
    
    for i in range(1, length):
        next_hash = hash_string(chain[-1], algorithm)
        chain.append(next_hash)
    
    return chain


def verify_hash_chain(
    chain: list[str],
    algorithm: str = 'sha256',
) -> bool:
    """Verify hash chain integrity."""
    for i in range(1, len(chain)):
        expected = hash_string(chain[i-1], algorithm)
        if not hmac.compare_digest(chain[i], expected):
            return False
    
    return True


def merkle_root(hashes: list[str], algorithm: str = 'sha256') -> str:
    """Calculate Merkle root from list of hashes."""
    if not hashes:
        return ""
    
    if len(hashes) == 1:
        return hashes[0]
    
    # Convert to list if not already
    current_level = hashes.copy()
    
    while len(current_level) > 1:
        next_level = []
        
        # Pair up hashes
        for i in range(0, len(current_level), 2):
            if i + 1 < len(current_level):
                # Hash the concatenation of two hashes
                combined = current_level[i] + current_level[i + 1]
                next_hash = hash_string(combined, algorithm)
                next_level.append(next_hash)
            else:
                # Odd number of hashes, duplicate the last one
                combined = current_level[i] + current_level[i]
                next_hash = hash_string(combined, algorithm)
                next_level.append(next_hash)
        
        current_level = next_level
    
    return current_level[0]


def generate_hash_id(
    data: Union[str, bytes],
    algorithm: str = 'sha256',
    length: int = 8,
) -> str:
    """Generate short hash ID."""
    hash_value = hash_bytes(data, algorithm) if isinstance(data, bytes) else hash_string(data, algorithm)
    return hash_value[:length]


def consistent_hash(
    data: str,
    buckets: int,
    algorithm: str = 'md5',
) -> int:
    """Consistent hash to bucket number."""
    hash_value = hash_string(data, algorithm)
    hash_int = int(hash_value, 16)
    return hash_int % buckets


def get_available_algorithms() -> list[str]:
    """Get list of available hash algorithms."""
    return hashlib.algorithms_available


def is_algorithm_available(algorithm: str) -> bool:
    """Check if hash algorithm is available."""
    return algorithm in hashlib.algorithms_available


def benchmark_hash_performance(
    data: Union[str, bytes],
    iterations: int = 1000,
    algorithms: Optional[list[str]] = None,
) -> dict[str, float]:
    """Benchmark hash algorithm performance."""
    import time
    
    if algorithms is None:
        algorithms = ['md5', 'sha1', 'sha256', 'sha512']
    
    results = {}
    
    for algorithm in algorithms:
        if not is_algorithm_available(algorithm):
            continue
        
        start_time = time.time()
        
        for _ in range(iterations):
            if isinstance(data, str):
                hash_string(data, algorithm)
            else:
                hash_bytes(data, algorithm)
        
        end_time = time.time()
        avg_time = (end_time - start_time) / iterations
        results[algorithm] = avg_time
    
    return results


# Common hash constants
EMPTY_MD5 = hashlib.md5(b'').hexdigest()
EMPTY_SHA1 = hashlib.sha1(b'').hexdigest()
EMPTY_SHA256 = hashlib.sha256(b'').hexdigest()
EMPTY_SHA512 = hashlib.sha512(b'').hexdigest()
