"""Unit tests for seo_agent.core.utils."""

import hashlib
import os
import tempfile
from pathlib import Path

import pytest

from seo_agent.core.utils import (
    clamp,
    compute_file_hash,
    merge_dicts,
    normalize_path,
    remove_prefix,
    remove_suffix,
    safe_get,
    sanitize_filename,
    to_camel_case,
    to_snake_case,
    truncate_string,
)


# =============================================================================
# TestSanitizeFilename
# =============================================================================


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_sanitize_filename_removes_invalid_chars(self):
        """sanitize_filename removes characters like < > : " / \\ | ? *."""
        result = sanitize_filename('file<name>with:invalid"chars')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "/" not in result
        assert "\\" not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result

    def test_sanitize_filename_replaces_with_underscore(self):
        """Invalid characters are replaced with underscore."""
        result = sanitize_filename("file?name")
        assert result == "file_name"

    def test_sanitize_filename_strips_whitespace(self):
        """sanitize_filename strips leading/trailing whitespace."""
        result = sanitize_filename("  filename  ")
        assert result == "filename"

    def test_sanitize_filename_strips_dots(self):
        """sanitize_filename strips leading/trailing dots."""
        result = sanitize_filename("..filename..")
        assert result == "filename"

    def test_sanitize_filename_limits_to_255_chars(self):
        """sanitize_filename limits output to 255 characters."""
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) == 255

    def test_sanitize_filename_empty_returns_unnamed(self):
        """sanitize_filename returns 'unnamed' for empty string."""
        result = sanitize_filename("")
        assert result == "unnamed"

    def test_sanitize_filename_whitespace_only_returns_unnamed(self):
        """sanitize_filename returns 'unnamed' for whitespace-only."""
        result = sanitize_filename("   ")
        assert result == "unnamed"

    def test_sanitize_filename_dots_only_returns_unnamed(self):
        """sanitize_filename returns 'unnamed' for dots-only."""
        result = sanitize_filename("...")
        assert result == "unnamed"

    def test_sanitize_filename_preserves_valid_chars(self):
        """sanitize_filename preserves valid filename characters."""
        result = sanitize_filename("valid_filename-123.txt")
        assert result == "valid_filename-123.txt"

    def test_sanitize_filename_normal_string(self):
        """sanitize_filename works with normal strings."""
        result = sanitize_filename("normal_file.txt")
        assert result == "normal_file.txt"


# =============================================================================
# TestTruncateString
# =============================================================================


class TestTruncateString:
    """Tests for truncate_string function."""

    def test_truncate_string_short_enough_returns_original(self):
        """truncate_string returns original if within max_length."""
        text = "short"
        result = truncate_string(text, 10)
        assert result == "short"

    def test_truncate_string_exactly_max_length_returns_original(self):
        """truncate_string returns original if exactly max_length."""
        text = "exactly"
        result = truncate_string(text, 7)
        assert result == "exactly"

    def test_truncate_string_adds_suffix(self):
        """truncate_string adds suffix when truncating."""
        text = "this is a long string"
        result = truncate_string(text, 10)
        assert result == "this is..."

    def test_truncate_string_custom_suffix(self):
        """truncate_string uses custom suffix."""
        text = "this is a long string"
        result = truncate_string(text, 10, suffix="...")
        assert result == "this is..."

    def test_truncate_string_empty_suffix(self):
        """truncate_string works with empty suffix."""
        text = "this is a long string"
        result = truncate_string(text, 10, suffix="")
        assert len(result) == 10

    def test_truncate_string_suffix_longer_than_max(self):
        """truncate_string handles suffix longer than max_length."""
        text = "some text"
        result = truncate_string(text, 3, suffix="...")
        # Should not crash, returns truncated content
        assert len(result) <= 3

    def test_truncate_string_empty_string(self):
        """truncate_string handles empty string."""
        result = truncate_string("", 10)
        assert result == ""

    def test_truncate_string_single_char(self):
        """truncate_string handles single character."""
        result = truncate_string("a", 10)
        assert result == "a"


# =============================================================================
# TestComputeFileHash
# =============================================================================


class TestComputeFileHash:
    """Tests for compute_file_hash function."""

    def test_compute_file_hash_sha256(self, tmp_path):
        """compute_file_hash computes SHA256 hash correctly."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"hello world")
        result = compute_file_hash(file_path, "sha256")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert result == expected

    def test_compute_file_hash_md5(self, tmp_path):
        """compute_file_hash computes MD5 hash correctly."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"hello world")
        result = compute_file_hash(file_path, "md5")
        expected = hashlib.md5(b"hello world").hexdigest()
        assert result == expected

    def test_compute_file_hash_sha1(self, tmp_path):
        """compute_file_hash computes SHA1 hash correctly."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"hello world")
        result = compute_file_hash(file_path, "sha1")
        expected = hashlib.sha1(b"hello world").hexdigest()
        assert result == expected

    def test_compute_file_hash_default_algorithm(self, tmp_path):
        """compute_file_hash uses SHA256 by default."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"hello world")
        result = compute_file_hash(file_path)
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert result == expected

    def test_compute_file_hash_large_file(self, tmp_path):
        """compute_file_hash handles large files."""
        file_path = tmp_path / "large.txt"
        # Write 1MB of data
        file_path.write_bytes(b"x" * (1024 * 1024))
        result = compute_file_hash(file_path)
        expected = hashlib.sha256(b"x" * (1024 * 1024)).hexdigest()
        assert result == expected

    def test_compute_file_hash_empty_file(self, tmp_path):
        """compute_file_hash handles empty files."""
        file_path = tmp_path / "empty.txt"
        file_path.write_bytes(b"")
        result = compute_file_hash(file_path)
        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_compute_file_hash_binary_content(self, tmp_path):
        """compute_file_hash handles binary content."""
        file_path = tmp_path / "binary.bin"
        file_path.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")
        result = compute_file_hash(file_path)
        expected = hashlib.sha256(b"\x00\x01\x02\xff\xfe\xfd").hexdigest()
        assert result == expected


# =============================================================================
# TestNormalizePath
# =============================================================================


class TestNormalizePath:
    """Tests for normalize_path function."""

    def test_normalize_path_string(self):
        """normalize_path converts string to Path."""
        result = normalize_path("/some/path")
        assert isinstance(result, Path)

    def test_normalize_path_expands_user(self):
        """normalize_path expands ~ to home directory."""
        result = normalize_path("~/some/path")
        assert "~" not in str(result)
        assert result.is_absolute()

    def test_normalize_path_resolves_relative(self):
        """normalize_path resolves relative paths to absolute."""
        result = normalize_path("./relative/path")
        assert result.is_absolute()

    def test_normalize_path_path_object(self):
        """normalize_path accepts Path objects."""
        path = Path("/some/path")
        result = normalize_path(path)
        assert result == path.resolve()


# =============================================================================
# TestMergeDicts
# =============================================================================


class TestMergeDicts:
    """Tests for merge_dicts function."""

    def test_merge_dicts_shallow_override(self):
        """merge_dicts overrides base values."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = merge_dicts(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_dicts_shallow_preserves_base(self):
        """merge_dicts preserves base keys not in override."""
        base = {"a": 1, "b": 2}
        override = {"c": 3}
        result = merge_dicts(base, override)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_merge_dicts_deep_merge(self):
        """merge_dicts performs deep merge when deep=True."""
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        result = merge_dicts(base, override, deep=True)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_merge_dicts_deep_nested(self):
        """merge_dicts handles deeply nested structures."""
        base = {"a": {"b": {"c": 1}}}
        override = {"a": {"b": {"d": 2}}}
        result = merge_dicts(base, override, deep=True)
        assert result == {"a": {"b": {"c": 1, "d": 2}}}

    def test_merge_dicts_shallow_does_not_deep_merge(self):
        """merge_dicts with deep=False replaces nested dicts."""
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        result = merge_dicts(base, override, deep=False)
        assert result == {"a": {"y": 3, "z": 4}}

    def test_merge_dicts_empty_base(self):
        """merge_dicts handles empty base."""
        base = {}
        override = {"a": 1}
        result = merge_dicts(base, override)
        assert result == {"a": 1}

    def test_merge_dicts_empty_override(self):
        """merge_dicts handles empty override."""
        base = {"a": 1}
        override = {}
        result = merge_dicts(base, override)
        assert result == {"a": 1}

    def test_merge_dicts_both_empty(self):
        """merge_dicts handles both empty."""
        result = merge_dicts({}, {})
        assert result == {}

    def test_merge_dicts_does_not_modify_original(self):
        """merge_dicts does not modify input dictionaries."""
        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}
        merge_dicts(base, override, deep=True)
        assert base == {"a": {"x": 1}}
        assert override == {"a": {"y": 2}}


# =============================================================================
# TestSafeGet
# =============================================================================


class TestSafeGet:
    """Tests for safe_get function."""

    def test_safe_get_single_key(self):
        """safe_get retrieves single key."""
        d = {"a": 1}
        result = safe_get(d, "a")
        assert result == 1

    def test_safe_get_nested_keys(self):
        """safe_get traverses nested keys."""
        d = {"a": {"b": {"c": 42}}}
        result = safe_get(d, "a", "b", "c")
        assert result == 42

    def test_safe_get_missing_key_returns_default(self):
        """safe_get returns default for missing key."""
        d = {"a": 1}
        result = safe_get(d, "b", default="missing")
        assert result == "missing"

    def test_safe_get_nested_missing_key_returns_default(self):
        """safe_get returns default when nested key missing."""
        d = {"a": {"b": 1}}
        result = safe_get(d, "a", "c", default="default")
        assert result == "default"

    def test_safe_get_default_none(self):
        """safe_get defaults to None."""
        d = {"a": 1}
        result = safe_get(d, "b")
        assert result is None

    def test_safe_get_empty_keys(self):
        """safe_get with no keys returns dict."""
        d = {"a": 1}
        result = safe_get(d)
        assert result == d

    def test_safe_get_none_value_in_path(self):
        """safe_get returns default when None encountered in path."""
        d = {"a": None}
        result = safe_get(d, "a", "b", default="default")
        assert result == "default"

    def test_safe_get_non_dict_in_path(self):
        """safe_get returns default when non-dict in path."""
        d = {"a": "string"}
        result = safe_get(d, "a", "b", default="default")
        assert result == "default"

    def test_safe_get_custom_default(self):
        """safe_get uses custom default value."""
        d = {"a": 1}
        result = safe_get(d, "missing", default=[])
        assert result == []

    def test_safe_get_explicit_none_value(self):
        """safe_get returns None when value is explicitly None."""
        d = {"a": None}
        result = safe_get(d, "a", default="default")
        assert result == "default"


# =============================================================================
# TestClamp
# =============================================================================


class TestClamp:
    """Tests for clamp function."""

    def test_clamp_value_within_range(self):
        """clamp returns value when within range."""
        result = clamp(5, 0, 10)
        assert result == 5

    def test_clamp_value_at_min(self):
        """clamp returns min when value is below."""
        result = clamp(-5, 0, 10)
        assert result == 0

    def test_clamp_value_at_max(self):
        """clamp returns max when value is above."""
        result = clamp(15, 0, 10)
        assert result == 10

    def test_clamp_value_below_min(self):
        """clamp returns min for value far below range."""
        result = clamp(-100, 0, 10)
        assert result == 0

    def test_clamp_value_above_max(self):
        """clamp returns max for value far above range."""
        result = clamp(100, 0, 10)
        assert result == 10

    def test_clamp_negative_range(self):
        """clamp works with negative ranges."""
        result = clamp(0, -10, -5)
        assert result == -5

    def test_clamp_float_values(self):
        """clamp works with float values."""
        result = clamp(3.5, 0.0, 10.0)
        assert result == 3.5

    def test_clamp_equal_min_max(self):
        """clamp returns min (which equals max) when range is zero."""
        result = clamp(5, 10, 10)
        assert result == 10


# =============================================================================
# TestToSnakeCase
# =============================================================================


class TestToSnakeCase:
    """Tests for to_snake_case function."""

    def test_to_snake_case_simple(self):
        """to_snake_case converts simple strings."""
        result = to_snake_case("hello")
        assert result == "hello"

    def test_to_snake_case_camel_case(self):
        """to_snake_case converts camelCase."""
        result = to_snake_case("helloWorld")
        assert result == "hello_world"

    def test_to_snake_case_pascal_case(self):
        """to_snake_case converts PascalCase."""
        result = to_snake_case("HelloWorld")
        assert result == "hello_world"

    def test_to_snake_case_multiple_uppercase(self):
        """to_snake_case handles multiple uppercase letters."""
        result = to_snake_case("XMLParser")
        assert result == "xml_parser"

    def test_to_snake_case_already_snake_case(self):
        """to_snake_case preserves snake_case."""
        result = to_snake_case("hello_world_test")
        assert result == "hello_world_test"

    def test_to_snake_case_with_numbers(self):
        """to_snake_case handles numbers."""
        result = to_snake_case("user123Name")
        assert result == "user123_name"

    def test_to_snake_case_empty_string(self):
        """to_snake_case handles empty string."""
        result = to_snake_case("")
        assert result == ""

    def test_to_snake_case_single_char(self):
        """to_snake_case handles single character."""
        result = to_snake_case("A")
        assert result == "a"


# =============================================================================
# TestToCamelCase
# =============================================================================


class TestToCamelCase:
    """Tests for to_camel_case function."""

    def test_to_camel_case_simple(self):
        """to_camel_case converts simple strings."""
        result = to_camel_case("hello")
        assert result == "hello"

    def test_to_camel_case_snake_case(self):
        """to_camel_case converts snake_case."""
        result = to_camel_case("hello_world")
        assert result == "helloWorld"

    def test_to_camel_case_multiple_underscores(self):
        """to_camel_case handles multiple underscores."""
        result = to_camel_case("hello_world_test")
        assert result == "helloWorldTest"

    def test_to_camel_case_already_camel_case(self):
        """to_camel_case preserves camelCase."""
        result = to_camel_case("helloWorld")
        assert result == "helloWorld"

    def test_to_camel_case_single_word(self):
        """to_camel_case handles single word."""
        result = to_camel_case("hello")
        assert result == "hello"

    def test_to_camel_case_empty_string(self):
        """to_camel_case handles empty string."""
        result = to_camel_case("")
        assert result == ""

    def test_to_camel_case_leading_underscore(self):
        """to_camel_case handles leading underscore."""
        result = to_camel_case("_hello")
        assert result == "Hello"

    def test_to_camel_case_trailing_underscore(self):
        """to_camel_case handles trailing underscore."""
        result = to_camel_case("hello_")
        assert result == "hello"


# =============================================================================
# TestRemovePrefix
# =============================================================================


class TestRemovePrefix:
    """Tests for remove_prefix function."""

    def test_remove_prefix_existing(self):
        """remove_prefix removes matching prefix."""
        result = remove_prefix("hello_world", "hello_")
        assert result == "world"

    def test_remove_prefix_not_present(self):
        """remove_prefix returns original when prefix not present."""
        result = remove_prefix("hello_world", "foo_")
        assert result == "hello_world"

    def test_remove_prefix_full_string(self):
        """remove_prefix removes entire string if it matches prefix."""
        result = remove_prefix("hello", "hello")
        assert result == ""

    def test_remove_prefix_empty_prefix(self):
        """remove_prefix returns original for empty prefix."""
        result = remove_prefix("hello", "")
        assert result == "hello"

    def test_remove_prefix_empty_string(self):
        """remove_prefix handles empty string."""
        result = remove_prefix("", "prefix")
        assert result == ""

    def test_remove_prefix_case_sensitive(self):
        """remove_prefix is case sensitive."""
        result = remove_prefix("HelloWorld", "hello")
        assert result == "HelloWorld"


# =============================================================================
# TestRemoveSuffix
# =============================================================================


class TestRemoveSuffix:
    """Tests for remove_suffix function."""

    def test_remove_suffix_existing(self):
        """remove_suffix removes matching suffix."""
        result = remove_suffix("hello_world", "_world")
        assert result == "hello"

    def test_remove_suffix_not_present(self):
        """remove_suffix returns original when suffix not present."""
        result = remove_suffix("hello_world", "_foo")
        assert result == "hello_world"

    def test_remove_suffix_full_string(self):
        """remove_suffix removes entire string if it matches suffix."""
        result = remove_suffix("world", "world")
        assert result == ""

    def test_remove_suffix_empty_suffix(self):
        """remove_suffix returns original for empty suffix."""
        result = remove_suffix("hello", "")
        assert result == "hello"

    def test_remove_suffix_empty_string(self):
        """remove_suffix handles empty string."""
        result = remove_suffix("", "suffix")
        assert result == ""

    def test_remove_suffix_case_sensitive(self):
        """remove_suffix is case sensitive."""
        result = remove_suffix("HelloWorld", "world")
        assert result == "HelloWorld"