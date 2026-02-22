"""File permissions module for PRISM - Controls automatic file reading permissions."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from prism.config import load_global_config


@dataclass
class FilePermissions:
    """File permission settings for PRISM agents."""

    auto_read_enabled: bool = True
    auto_read_paths: list[str] = field(default_factory=list)
    protected_paths: list[str] = field(default_factory=list)
    max_auto_read_size: int = 1048576  # 1MB
    role_overrides: dict = field(default_factory=dict)


def _matches_pattern(path: str, pattern: str) -> bool:
    """Check if a path matches a glob pattern."""
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern)


def _is_path_allowed(path: str, allowed_patterns: list[str]) -> bool:
    """Check if path matches any allowed pattern."""
    for pattern in allowed_patterns:
        if _matches_pattern(path, pattern):
            return True
    return False


def _is_path_protected(path: str, protected_patterns: list[str]) -> bool:
    """Check if path matches any protected pattern."""
    for pattern in protected_patterns:
        if _matches_pattern(path, pattern):
            return True
    return False


def can_read_file(
    file_path: str | Path, role: Optional[str] = None, explicit_permission: bool = False
) -> tuple[bool, str]:
    """Check if an agent can read a file automatically.

    Args:
        file_path: Path to the file to check
        role: Agent role (architect, developer, reviewer, memory, optimizer)
        explicit_permission: Whether user has explicitly granted permission

    Returns:
        Tuple of (can_read, reason)
        - can_read: True if file can be read automatically
        - reason: Explanation of the decision
    """
    path = Path(file_path)
    path_str = str(path)

    # If explicit permission granted, always allow
    if explicit_permission:
        return True, "Explicit permission granted"

    # Load configuration
    config = load_global_config()
    perm_config = getattr(config, "permissions", None)

    if not perm_config:
        # No permissions config, default to allowing reads
        return True, "No permissions configured (default allow)"

    # Check role-specific permissions
    auto_read_enabled = perm_config.get("auto_read_enabled", True)
    auto_read_paths = perm_config.get("auto_read_paths", ["*"])
    protected_paths = perm_config.get("protected_paths", [])
    max_size = perm_config.get("max_auto_read_size", 1048576)

    # Apply role overrides if specified
    if role and "roles" in perm_config:
        role_config = perm_config["roles"].get(role, {})
        if "auto_read_enabled" in role_config:
            auto_read_enabled = role_config["auto_read_enabled"]
        if "additional_paths" in role_config:
            auto_read_paths = auto_read_paths + role_config["additional_paths"]

    # Check if auto-read is enabled for this role
    if not auto_read_enabled:
        return False, f"Auto-read disabled for role: {role}"

    # Check file size
    try:
        if path.exists() and path.stat().st_size > max_size:
            return False, f"File exceeds max auto-read size ({max_size} bytes)"
    except (OSError, IOError):
        pass  # Can't check size, continue with other checks

    # Check if path is protected (protected paths always require explicit permission)
    if _is_path_protected(path_str, protected_paths):
        return False, "Path is protected - explicit permission required"

    # Check if path is in allowed list
    if _is_path_allowed(path_str, auto_read_paths):
        return True, "Path in auto-read allow list"

    # Default: require explicit permission
    return False, "Path not in auto-read allow list"


def get_permissions_summary(role: Optional[str] = None) -> dict:
    """Get a summary of current permissions configuration.

    Args:
        role: Optional role to get specific permissions for

    Returns:
        Dictionary with permission settings
    """
    config = load_global_config()
    perm_config = getattr(config, "permissions", {})

    summary = {
        "auto_read_enabled": perm_config.get("auto_read_enabled", True),
        "auto_read_paths_count": len(perm_config.get("auto_read_paths", [])),
        "protected_paths_count": len(perm_config.get("protected_paths", [])),
        "max_auto_read_size": perm_config.get("max_auto_read_size", 1048576),
    }

    if role and "roles" in perm_config:
        role_config = perm_config["roles"].get(role)
        if role_config:
            summary["role"] = role
            summary["role_auto_read"] = role_config.get(
                "auto_read_enabled", summary["auto_read_enabled"]
            )
            summary["role_additional_paths"] = role_config.get("additional_paths", [])

    return summary


def validate_path_for_auto_read(path: str) -> dict:
    """Validate a specific path and return detailed info.

    Args:
        path: File path to validate

    Returns:
        Dictionary with validation results
    """
    config = load_global_config()
    perm_config = getattr(config, "permissions", {})

    auto_read_paths = perm_config.get("auto_read_paths", [])
    protected_paths = perm_config.get("protected_paths", [])

    return {
        "path": path,
        "is_allowed": _is_path_allowed(path, auto_read_paths),
        "is_protected": _is_path_protected(path, protected_paths),
        "can_auto_read": _is_path_allowed(path, auto_read_paths)
        and not _is_path_protected(path, protected_paths),
        "matching_allow_patterns": [
            p for p in auto_read_paths if _matches_pattern(path, p)
        ],
        "matching_protect_patterns": [
            p for p in protected_paths if _matches_pattern(path, p)
        ],
    }


def can_write_file(
    file_path: str | Path, role: Optional[str] = None, explicit_permission: bool = False
) -> tuple[bool, str]:
    """Check if an agent can write (create/edit) a file automatically.

    Args:
        file_path: Path to the file to check
        role: Agent role (architect, developer, reviewer, memory, optimizer)
        explicit_permission: Whether user has explicitly granted permission

    Returns:
        Tuple of (can_write, reason)
        - can_write: True if file can be written automatically
        - reason: Explanation of the decision
    """
    path = Path(file_path)
    path_str = str(path)

    # If explicit permission granted, always allow
    if explicit_permission:
        return True, "Explicit permission granted"

    # Load configuration
    config = load_global_config()
    perm_config = getattr(config, "permissions", None)

    if not perm_config:
        # No permissions config, default to allowing writes
        return True, "No permissions configured (default allow)"

    write_config = perm_config.get("write_permissions", {})

    # Check role-specific permissions
    auto_write_enabled = write_config.get("auto_write_enabled", True)
    auto_write_paths = write_config.get("auto_write_paths", ["*"])
    protected_write_paths = write_config.get("protected_write_paths", [])
    max_size = write_config.get("max_auto_write_size", 5242880)

    # Apply role overrides if specified
    if role and "roles" in write_config:
        role_config = write_config["roles"].get(role, {})
        if "auto_write_enabled" in role_config:
            auto_write_enabled = role_config["auto_write_enabled"]

    # Check if auto-write is enabled for this role
    if not auto_write_enabled:
        return False, f"Auto-write disabled for role: {role}"

    # Check file size for existing files
    try:
        if path.exists() and path.stat().st_size > max_size:
            return False, f"File exceeds max auto-write size ({max_size} bytes)"
    except (OSError, IOError):
        pass  # Can't check size, continue with other checks

    # Check if path is protected (protected paths always require explicit permission)
    if _is_path_protected(path_str, protected_write_paths):
        return False, "Path is protected - explicit permission required"

    # Check if path is in allowed list
    if _is_path_allowed(path_str, auto_write_paths):
        return True, "Path in auto-write allow list"

    # Default: require explicit permission
    return False, "Path not in auto-write allow list"


def get_write_permissions_summary(role: Optional[str] = None) -> dict:
    """Get a summary of current write permissions configuration.

    Args:
        role: Optional role to get specific permissions for

    Returns:
        Dictionary with write permission settings
    """
    config = load_global_config()
    perm_config = getattr(config, "permissions", {})
    write_config = perm_config.get("write_permissions", {})

    summary = {
        "auto_write_enabled": write_config.get("auto_write_enabled", True),
        "auto_write_paths_count": len(write_config.get("auto_write_paths", [])),
        "protected_write_paths_count": len(
            write_config.get("protected_write_paths", [])
        ),
        "max_auto_write_size": write_config.get("max_auto_write_size", 5242880),
    }

    if role and "roles" in write_config:
        role_config = write_config["roles"].get(role)
        if role_config:
            summary["role"] = role
            summary["role_auto_write"] = role_config.get(
                "auto_write_enabled", summary["auto_write_enabled"]
            )

    return summary


def validate_path_for_auto_write(path: str) -> dict:
    """Validate a specific path for writing and return detailed info.

    Args:
        path: File path to validate

    Returns:
        Dictionary with validation results
    """
    config = load_global_config()
    perm_config = getattr(config, "permissions", {})
    write_config = perm_config.get("write_permissions", {})

    auto_write_paths = write_config.get("auto_write_paths", [])
    protected_write_paths = write_config.get("protected_write_paths", [])

    return {
        "path": path,
        "is_allowed": _is_path_allowed(path, auto_write_paths),
        "is_protected": _is_path_protected(path, protected_write_paths),
        "can_auto_write": _is_path_allowed(path, auto_write_paths)
        and not _is_path_protected(path, protected_write_paths),
        "matching_allow_patterns": [
            p for p in auto_write_paths if _matches_pattern(path, p)
        ],
        "matching_protect_patterns": [
            p for p in protected_write_paths if _matches_pattern(path, p)
        ],
    }


def get_full_permissions_summary(role: Optional[str] = None) -> dict:
    """Get a complete summary of all permissions (read and write).

    Args:
        role: Optional role to get specific permissions for

    Returns:
        Dictionary with complete permission settings
    """
    return {
        "read": get_permissions_summary(role),
        "write": get_write_permissions_summary(role),
    }
