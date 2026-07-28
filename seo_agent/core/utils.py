"""Utility functions for the SEO Agent.

This module provides common utility functions used across the project.
All functions are pure utilities with no business logic.
"""

import hashlib
import re
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


def sanitize_filename(name: str) -> str:
    """Convert a string to a safe filename.

    Args:
        name: The string to sanitize.

    Returns:
        A safe filename string with invalid characters removed.
    """
    # Remove invalid filename characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(". ")
    # Limit length
    return sanitized[:255] if sanitized else "unnamed"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate a string to a maximum length.

    Args:
        text: The string to truncate.
        max_length: Maximum length including suffix.
        suffix: String to append when truncated.

    Returns:
        Truncated string with suffix if needed.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Compute the hash of a file.

    Args:
        file_path: Path to the file.
        algorithm: Hash algorithm to use (md5, sha1, sha256).

    Returns:
        Hexadecimal hash string.
    """
    hash_func = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def normalize_path(path: str | Path) -> Path:
    """Normalize a path to an absolute Path object.

    Args:
        path: The path to normalize.

    Returns:
        Absolute Path object.
    """
    return Path(path).expanduser().resolve()


def merge_dicts(
    base: dict[str, Any],
    override: dict[str, Any],
    deep: bool = False,
) -> dict[str, Any]:
    """Merge two dictionaries.

    Args:
        base: Base dictionary.
        override: Dictionary with values to override.
        deep: If True, perform deep merge for nested dicts.

    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in override.items():
        if deep and key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value, deep=True)
        else:
            result[key] = value
    return result


def safe_get(dictionary: dict[str, Any], *keys: str, default: T = None) -> T:
    """Safely get a nested value from a dictionary.

    Args:
        dictionary: The dictionary to search.
        *keys: Sequence of keys to traverse.
        default: Default value if key not found.

    Returns:
        The value at the path or default.
    """
    current: Any = dictionary
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current if current is not None else default


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a value between min and max.

    Args:
        value: The value to clamp.
        min_value: Minimum allowed value.
        max_value: Maximum allowed value.

    Returns:
        Clamped value.
    """
    return max(min_value, min(value, max_value))


def to_snake_case(text: str) -> str:
    """Convert a string to snake_case.

    Args:
        text: The string to convert.

    Returns:
        Snake_case version of the string.
    """
    # Insert underscore before uppercase letters
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", text)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def to_camel_case(text: str) -> str:
    """Convert a string to camelCase.

    Args:
        text: The string to convert.

    Returns:
        camelCase version of the string.
    """
    components = text.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def remove_prefix(text: str, prefix: str) -> str:
    """Remove a prefix from a string.

    Args:
        text: The string to process.
        prefix: The prefix to remove.

    Returns:
        String without the prefix.
    """
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text


def remove_suffix(text: str, suffix: str) -> str:
    """Remove a suffix from a string.

    Args:
        text: The string to process.
        suffix: The suffix to remove.

    Returns:
        String without the suffix.
    """
    if text.endswith(suffix):
        return text[: -len(suffix)]
    return text