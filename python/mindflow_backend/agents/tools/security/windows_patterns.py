"""Windows Pattern Detection — Detect path traversal bypass attempts on Windows/NTFS.

Detects suspicious Windows path patterns that could bypass security checks.
These patterns work on all platforms because NTFS filesystems can be mounted
on Linux and macOS (e.g., via ntfs-3g, WSL).

Adapted from Claude Code's hasSuspiciousWindowsPathPattern() in filesystem.ts.

Detected patterns:
1. NTFS Alternate Data Streams (ADS): file.txt:stream, file.txt::$DATA
2. 8.3 Short Names: GIT~1, CLAUDE~1, SETTIN~1
3. Long path prefixes: \\?\, \\.\, //?/, //.
4. Trailing dots and spaces: .git., .claude , .bashrc...
5. DOS Device Names: .git.CON, settings.json.PRN, .bashrc.AUX
6. Three+ consecutive dots: .../file, file...
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# DOS device names (reserved names that should NOT be used as filenames)
DOS_DEVICE_NAMES: set[str] = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# ADS suffixes that are meaningful for security
ADS_SUFFIXES: list[str] = [
    "::$DATA",
    "::$INDEX_ALLOCATION",
    "::$ATTRIBUTE_LIST",
    "::$SECURITY_DESCRIPTOR",
]


# ---------------------------------------------------------------------------
# Pattern detection functions
# ---------------------------------------------------------------------------


def has_suspicious_windows_pattern(path_str: str) -> bool:
    """Check if a path contains any suspicious Windows patterns.
    
    This should always result in manual approval — these patterns are
    commonly used to bypass security checks via path canonicalization.
    
    Args:
        path_str: The path string to check.
        
    Returns:
        True if suspicious pattern detected.
    """
    if not path_str:
        return False

    return (
        has_ntfs_alternate_data_stream(path_str)
        or has_83_short_name(path_str)
        or has_long_path_prefix(path_str)
        or has_trailing_spaces_dots(path_str)
        or has_dos_device_name(path_str)
        or has_consecutive_dots(path_str)
        or has_unc_path(path_str)
    )


def has_ntfs_alternate_data_stream(path_str: str) -> bool:
    """Check for NTFS Alternate Data Streams.
    
    ADS allows multiple data streams per file: filename:streamname
    Examples: file.txt:secret, file.txt::$DATA, config.json:hidden:$INDEX_ALLOCATION
    
    Note: Colon syntax is Windows/WSL-specific, but we check everywhere
    for defense-in-depth since NTFS can be mounted on Linux.
    """
    # Basic ADS pattern: something:somethingelse
    # But NOT Windows drive letters (C:, D:)
    ads_pattern = re.compile(
        r"(?<!^[A-Za-z])"  # NOT preceded by a letter (catches C:, D:, etc.)
        r":"
        r"[^:\s/\\]",  # Colon followed by non-special char
    )
    if ads_pattern.search(path_str):
        return True

    # Explicit ADS suffixes
    path_lower = path_str.lower()
    for suffix in ADS_SUFFIXES:
        if suffix.lower() in path_lower:
            return True

    return False


def has_83_short_name(path_str: str) -> bool:
    """Check for 8.3 short filename (SFN) patterns.
    
    8.3 names are legacy Windows short filenames: MAXIMUM~1.TXT
    These can be used to bypass allowlist-based security checks.
    
    Examples: GIT~1, CLAUDE~1, SETTIN~1.JSON, DOCUME~1
    """
    # Pattern: 1-6 chars + tilde + digit + optional extension
    short_name_pattern = re.compile(
        r"(?:^|["
        r"/\\"  # Path separators
        r"])"
        r"([A-Za-z0-9_-]{1,6})"  # Base name (1-6 chars)
        r"~"  # Tilde
        r"(\d)"  # Digit (1-9 typically)
        r"(?:\.([A-Za-z0-9_-]{1,3}))?"  # Optional 3-char extension
        r"(?:$|["
        r"/\\"  # Path separators
        r"])",
    )
    return bool(short_name_pattern.search(path_str))


def has_long_path_prefix(path_str: str) -> bool:
    """Check for Windows long path prefixes.
    
    These prefixes bypass path length limits and can confuse parsers:
    - \\?\C:\...  (Win32 namespace)
    - \\.\C:\...  (NT namespace)
    - //?/C:/...  (POSIX-style on Windows)
    """
    prefixes = [
        "\\\\?\\",
        "\\\\.\\",
        "//?/",
        "//./",
        "\\\\?\\UNC\\",
        "\\\\?\\GLOBALROOT",
    ]
    path_lower = path_str.lower()
    return any(prefix.lower() in path_lower for prefix in prefixes)


def has_trailing_spaces_dots(path_str: str) -> bool:
    """Check for trailing spaces or dots.
    
    Windows strips trailing dots and spaces from filenames, which can
    bypass security checks:
    - .git. -> .git (bypasses hidden file check)
    - .bashrc  -> .bashrc (bypasses dotfile check)
    """
    if not path_str:
        return False

    # Get the last component (filename)
    parts = path_str.replace("\\", "/").split("/")
    last_part = parts[-1] if parts else ""

    if not last_part:
        return False

    # Check trailing dots
    if last_part.endswith("."):
        return True

    # Check trailing spaces
    if last_part.endswith(" "):
        return True

    # Check for dots before extension
    if "." in last_part:
        name_part = last_part.rsplit(".", 1)[0]
        if name_part and name_part.endswith("."):
            return True

    return False


def has_dos_device_name(path_str: str) -> bool:
    """Check for DOS device names in filename.
    
    DOS device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9) are reserved
    on Windows. An attacker can try to access them via:
    - .git.CON
    - settings.json.PRN
    - C:\path\NUL
    
    These work regardless of filesystem (even on ext4 via WSL).
    """
    # Extract filename components
    parts = path_str.replace("\\", "/").split("/")
    
    for part in parts:
        if not part:
            continue
        
        # Remove extension for checking
        name_no_ext = part.rsplit(".", 1)[0] if "." in part else part
        
        # Get the last component of the name
        name_parts = name_no_ext.split(".")
        last_name_part = name_parts[-1].upper() if name_parts else ""
        
        if last_name_part in DOS_DEVICE_NAMES:
            return True
        
        # Also check if any part matches
        for component in name_parts:
            if component.upper() in DOS_DEVICE_NAMES:
                return True

    # Also check the full path for device names after dots
    for device in DOS_DEVICE_NAMES:
        # Pattern: .DEVICE or /DEVICE\ or endswith .DEVICE
        patterns = [
            rf"\.{device}(?:$|[\\/])",  # .CON, .CON\
            rf"(?:^|[\\/]){device}(?:$|[\\/])",  # CON, CON/, \CON\
        ]
        for pattern in patterns:
            if re.search(pattern, path_str, re.IGNORECASE):
                return True

    return False


def has_consecutive_dots(path_str: str) -> bool:
    """Check for three or more consecutive dots.
    
    While ../ is normal path traversal, ... or .... can be used to
    bypass naive normalization:
    - .../ -> resolves to current dir, not parent
    - path/.../file -> confusing for parsers
    - file...txt -> unusual extension
    """
    return "..." in path_str


def has_unc_path(path_str: str) -> bool:
    """Check for UNC paths.

    UNC paths can access network resources and should
    always require manual approval.

    Examples: \\\\evil-server\\share, //192.168.1.100/c$
    """
    return path_str.startswith("\\\\") or path_str.startswith("//")


# ---------------------------------------------------------------------------
# Detailed analysis
# ---------------------------------------------------------------------------


@dataclass
class WindowsPatternAnalysis:
    """Detailed analysis of Windows patterns found in path."""

    path: str
    has_ads: bool = False
    has_83_name: bool = False
    has_long_prefix: bool = False
    has_trailing: bool = False
    has_dos_device: bool = False
    has_consecutive_dots: bool = False
    has_unc: bool = False

    @property
    def is_suspicious(self) -> bool:
        """True if any suspicious pattern was found."""
        return any([
            self.has_ads,
            self.has_83_name,
            self.has_long_prefix,
            self.has_trailing,
            self.has_dos_device,
            self.has_consecutive_dots,
            self.has_unc,
        ])

    @property
    def reasons(self) -> list[str]:
        """List of reasons why the path is suspicious."""
        reasons: list[str] = []
        if self.has_ads:
            reasons.append("NTFS Alternate Data Stream detected")
        if self.has_83_name:
            reasons.append("8.3 short filename detected")
        if self.has_long_prefix:
            reasons.append("Windows long path prefix detected")
        if self.has_trailing:
            reasons.append("Trailing spaces or dots detected")
        if self.has_dos_device:
            reasons.append("DOS device name detected")
        if self.has_consecutive_dots:
            reasons.append("Three or more consecutive dots")
        if self.has_unc:
            reasons.append("UNC network path detected")
        return reasons

    def to_risk_string(self) -> str:
        """Human-readable risk assessment."""
        if not self.is_suspicious:
            return "No suspicious Windows patterns detected"
        return "Suspicious patterns: " + "; ".join(self.reasons)


def analyze_windows_patterns(path_str: str) -> WindowsPatternAnalysis:
    """Perform detailed analysis of Windows patterns in a path.
    
    Returns WindowsPatternAnalysis with per-pattern findings
    and a combined risk assessment.
    
    Args:
        path_str: Path to analyze.
        
    Returns:
        WindowsPatternAnalysis with detailed findings.
    """
    return WindowsPatternAnalysis(
        path=path_str,
        has_ads=has_ntfs_alternate_data_stream(path_str),
        has_83_name=has_83_short_name(path_str),
        has_long_prefix=has_long_path_prefix(path_str),
        has_trailing=has_trailing_spaces_dots(path_str),
        has_dos_device=has_dos_device_name(path_str),
        has_consecutive_dots=has_consecutive_dots(path_str),
        has_unc=has_unc_path(path_str),
    )