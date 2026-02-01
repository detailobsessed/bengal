#!/usr/bin/env python3
"""
Pre-commit hook to detect unregistered global state in Bengal modules.

Finds module-level globals that could cause test pollution:
- `_foo = None` patterns (singletons, cached state)
- `global _foo` statements (state mutation)

Then checks if they're registered with the cache registry for cleanup.

Usage:
    uv run scripts/check_global_state.py [files...]
    uv run scripts/check_global_state.py --all  # Check all bengal/ files

Exit codes:
    0: All global state is registered
    1: Unregistered global state found
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns that indicate global state needing cleanup
GLOBAL_STATE_PATTERNS = [
    # Module-level None assignments (singletons, cached refs)
    re.compile(r"^_[a-z_]+\s*(?::\s*\S+\s*)?=\s*None\s*$"),
    # Module-level empty collections
    re.compile(r"^_[a-z_]+\s*(?::\s*\S+\s*)?=\s*(?:\{\}|\[\]|set\(\))\s*$"),
]

# Files/patterns to exclude from checking
EXCLUDE_PATTERNS = [
    "*/test_*.py",
    "*/__pycache__/*",
    "*/conftest.py",
]

# Known safe patterns (constants, type aliases, etc.)
SAFE_PATTERNS = [
    re.compile(r"^_[A-Z_]+\s*="),  # Constants like _DEFAULT_SIZE = 24
    re.compile(r"^_T\s*="),  # Type variables
    re.compile(r"^_logger\s*="),  # Loggers (stateless)
    re.compile(r"^_lock\s*="),  # Locks (needed for thread safety)
    re.compile(r"^_[a-z_]+_lock\s*="),  # Named locks
    re.compile(r"^__all__\s*="),  # Module exports
    re.compile(r"^_cached_fields.*ClassVar"),  # Class-level caches (not module state)
    re.compile(r"^_uvloop"),  # uvloop lazy loading (stateless detection)
    re.compile(r"^_console\s*="),  # Rich console (has reset_console)
    re.compile(r"^_invalidation_log\s*="),  # Cache registry internal state
]


def is_excluded(path: Path) -> bool:
    """Check if path matches exclusion patterns."""
    from fnmatch import fnmatch

    path_str = str(path)
    return any(fnmatch(path_str, pattern) for pattern in EXCLUDE_PATTERNS)


def is_safe_pattern(line: str) -> bool:
    """Check if line matches a known safe pattern."""
    return any(pattern.match(line) for pattern in SAFE_PATTERNS)


def find_global_state(filepath: Path) -> list[tuple[int, str, str]]:
    """
    Find potential global state in a Python file.

    Returns:
        List of (line_number, variable_name, line_content) tuples
    """
    issues = []

    try:
        content = filepath.read_text()
        lines = content.splitlines()
    except Exception:
        return []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            continue

        # Skip safe patterns
        if is_safe_pattern(stripped):
            continue

        # Check for global state patterns
        for pattern in GLOBAL_STATE_PATTERNS:
            if pattern.match(stripped):
                # Extract variable name
                match = re.match(r"^(_[a-z_]+)", stripped)
                if match:
                    var_name = match.group(1)
                    issues.append((i, var_name, stripped))
                break

    return issues


def check_registration(filepath: Path, var_names: list[str]) -> list[str]:
    """
    Check if global state variables are registered with cache registry.

    Returns:
        List of unregistered variable names
    """
    try:
        content = filepath.read_text()
    except Exception:
        return var_names

    # Check for reset functions that clear the variables
    unregistered = []
    for var_name in var_names:
        # Look for patterns like:
        # - global _var_name followed by _var_name = None
        # - def reset_*() or def clear_*() that clears the variable
        # - .clear() calls on the variable
        reset_pattern = re.compile(
            rf"def\s+(?:reset|clear)_\w+\([^)]*\).*?(?:global\s+{re.escape(var_name)}.*?{re.escape(var_name)}\s*=|{re.escape(var_name)}\.clear\(\))",
            re.DOTALL,
        )
        clear_pattern = re.compile(
            rf"global\s+{re.escape(var_name)}.*?{re.escape(var_name)}\s*=\s*(?:None|\[\]|set\(\)|\{{\}})",
            re.DOTALL,
        )
        method_clear_pattern = re.compile(rf"{re.escape(var_name)}\.clear\(\)")

        has_reset = (
            reset_pattern.search(content)
            or clear_pattern.search(content)
            or method_clear_pattern.search(content)
        )
        is_context_var = f"{var_name}: ContextVar" in content
        if not has_reset and not is_context_var:
            unregistered.append(var_name)

    return unregistered


def check_file(filepath: Path) -> list[str]:
    """
    Check a single file for unregistered global state.

    Returns:
        List of error messages
    """
    if is_excluded(filepath):
        return []

    issues = find_global_state(filepath)
    if not issues:
        return []

    var_names = [var_name for _, var_name, _ in issues]
    unregistered = check_registration(filepath, var_names)

    if not unregistered:
        return []

    errors = []
    for line_num, var_name, line_content in issues:
        if var_name in unregistered:
            errors.append(
                f"{filepath}:{line_num}: Unregistered global state '{var_name}'\n"
                f"  {line_content}\n"
                f"  Fix: Add reset function and register with cache_registry"
            )

    return errors


def main() -> int:
    """Main entry point."""
    args = sys.argv[1:]

    if not args or "--help" in args:
        print(__doc__)
        return 0

    if "--all" in args:
        # Check all bengal/ Python files
        bengal_dir = Path(__file__).parent.parent / "bengal"
        files = list(bengal_dir.rglob("*.py"))
    else:
        files = [Path(f) for f in args if f.endswith(".py")]

    all_errors = []
    for filepath in files:
        if filepath.exists():
            errors = check_file(filepath)
            all_errors.extend(errors)

    if all_errors:
        print("Unregistered global state detected (potential test pollution):\n")
        for error in all_errors:
            print(error)
            print()
        print(
            "To fix: Add a reset function and register it with bengal.utils.cache_registry.\n"
            "See bengal/rendering/template_functions/authors.py for an example."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
