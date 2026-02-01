"""
Shared utilities for include and literalinclude directives.

Provides common functionality for:
- Path resolution with security checks
- File loading with size limits and line range extraction
- Line number parsing from directive options
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from mistune.core import BlockState

__all__ = [
    "MAX_INCLUDE_SIZE",
    "extract_lines",
    "load_file_content",
    "parse_line_numbers",
    "resolve_include_path",
]

logger = get_logger(__name__)

# Robustness limits
MAX_INCLUDE_SIZE = 10 * 1024 * 1024  # 10 MB - prevent memory exhaustion


def parse_line_numbers(
    options: dict[str, str],
) -> tuple[int | None, int | None]:
    """
    Parse start-line and end-line from directive options.

    Args:
        options: Directive options dict

    Returns:
        Tuple of (start_line, end_line), either may be None
    """
    start_line_str = options.get("start-line")
    end_line_str = options.get("end-line")

    start_line: int | None = None
    end_line: int | None = None

    if start_line_str is not None:
        with contextlib.suppress(ValueError, TypeError):
            start_line = int(start_line_str)
    if end_line_str is not None:
        with contextlib.suppress(ValueError, TypeError):
            end_line = int(end_line_str)

    return start_line, end_line


def resolve_include_path(
    path: str,
    state: BlockState,
    directive_name: str = "include",
) -> Path | None:
    """
    Resolve file path relative to current page or site root.

    Security:
        - Rejects absolute paths
        - Rejects paths outside site root
        - Rejects symlinks (could escape containment)

    Path Resolution:
        - root_path MUST be provided via state (set by rendering pipeline)
        - No fallback to Path.cwd() - eliminates CWD-dependent behavior

    Args:
        path: Relative path to file
        state: Parser state (must contain root_path, may contain source_path)
        directive_name: Name of directive for log messages

    Returns:
        Resolved Path object, or None if not found or security check fails
    """
    # Get root_path from state (MUST be set by rendering pipeline)
    root_path = getattr(state, "root_path", None)
    if not root_path:
        logger.warning(
            f"{directive_name}_missing_root_path",
            path=path,
            action="skipping",
            hint="Ensure rendering pipeline passes root_path in state",
        )
        return None
    root_path = Path(root_path)

    # Try to get source_path from state (current page being parsed)
    source_path = getattr(state, "source_path", None)
    if source_path:
        source_path = Path(source_path)
        base_dir = source_path.parent
    else:
        content_dir = root_path / "content"
        base_dir = content_dir if content_dir.exists() else root_path

    # Reject absolute paths (security)
    if Path(path).is_absolute():
        logger.warning(f"{directive_name}_absolute_path_rejected", path=path)
        return None

    # Check for path traversal attempts
    normalized_path = path.replace("\\", "/")
    if "../" in normalized_path or normalized_path.startswith("../"):
        resolved = (base_dir / path).resolve()
        try:
            resolved.relative_to(root_path.resolve())
        except ValueError:
            logger.warning(f"{directive_name}_path_traversal_rejected", path=path)
            return None
        file_path: Path | None = resolved
    else:
        file_path = base_dir / path

    # Check if file exists
    if file_path is None or not file_path.exists():
        file_path = None

    # Security: Reject symlinks
    if file_path is not None and file_path.is_symlink():
        logger.warning(
            f"{directive_name}_symlink_rejected",
            path=str(file_path),
            reason="symlinks_not_allowed_for_security",
        )
        return None

    # Ensure file is within site root
    if file_path is not None:
        try:
            file_path.resolve().relative_to(root_path.resolve())
        except ValueError:
            logger.warning(f"{directive_name}_outside_site_root", path=str(file_path))
            return None

    return file_path


def resolve_include_path_with_fallback(
    path: str,
    state: BlockState,
    directive_name: str = "include",
) -> Path | None:
    """
    Resolve file path with fallback to content directory and .md extension.

    This is the full resolution logic used by the include directive.
    For literalinclude, use resolve_include_path directly.

    Args:
        path: Relative path to file
        state: Parser state
        directive_name: Name of directive for log messages

    Returns:
        Resolved Path object, or None if not found
    """
    file_path = resolve_include_path(path, state, directive_name)

    if file_path is not None:
        return file_path

    # Get root_path and source_path for fallback logic
    root_path = getattr(state, "root_path", None)
    if not root_path:
        return None
    root_path = Path(root_path)

    source_path = getattr(state, "source_path", None)
    if source_path:
        source_path = Path(source_path)
        base_dir = source_path.parent
    else:
        content_dir = root_path / "content"
        base_dir = content_dir if content_dir.exists() else root_path

    # Try with .md extension
    if not path.endswith(".md"):
        md_path = base_dir / f"{path}.md"
        if md_path.exists() and not md_path.is_symlink():
            try:
                md_path.resolve().relative_to(root_path.resolve())
                return md_path
            except ValueError:
                pass

    # Fallback: try content directory if file not found relative to page
    if source_path:
        content_dir = root_path / "content"
        if content_dir.exists():
            fallback_path = content_dir / path
            if fallback_path.exists() and not fallback_path.is_symlink():
                try:
                    fallback_path.resolve().relative_to(root_path.resolve())
                    return fallback_path
                except ValueError:
                    pass

            # Try with .md extension in content dir
            if not path.endswith(".md"):
                fallback_md = content_dir / f"{path}.md"
                if fallback_md.exists() and not fallback_md.is_symlink():
                    try:
                        fallback_md.resolve().relative_to(root_path.resolve())
                        return fallback_md
                    except ValueError:
                        pass

    return None


def extract_lines(
    lines: list[str],
    start_line: int | None,
    end_line: int | None,
) -> list[str]:
    """
    Extract a range of lines from a list.

    Args:
        lines: List of lines
        start_line: 1-indexed start line (None = from beginning)
        end_line: 1-indexed end line (None = to end)

    Returns:
        Extracted lines
    """
    if start_line is not None or end_line is not None:
        start = int(start_line) - 1 if start_line else 0
        end = int(end_line) if end_line else len(lines)
        # Clamp to valid range
        start = max(0, min(start, len(lines)))
        end = max(start, min(end, len(lines)))
        return lines[start:end]
    return lines


def load_file_content(
    file_path: Path,
    start_line: int | None = None,
    end_line: int | None = None,
    directive_name: str = "include",
    max_size: int = MAX_INCLUDE_SIZE,
) -> str | None:
    """
    Load file content with optional line range.

    Security: Enforces file size limit to prevent memory exhaustion.

    Args:
        file_path: Path to file
        start_line: Optional start line (1-indexed)
        end_line: Optional end line (1-indexed)
        directive_name: Name of directive for log messages
        max_size: Maximum file size in bytes

    Returns:
        File content as string, or None on error
    """
    try:
        # Check file size before reading (security)
        file_size = file_path.stat().st_size
        if file_size > max_size:
            logger.warning(
                f"{directive_name}_file_too_large",
                path=str(file_path),
                size_bytes=file_size,
                limit_bytes=max_size,
                size_mb=f"{file_size / (1024 * 1024):.2f}",
                limit_mb=f"{max_size / (1024 * 1024):.0f}",
            )
            return None

        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        lines = extract_lines(lines, start_line, end_line)
        return "".join(lines).rstrip()

    except Exception as e:
        logger.warning(
            f"{directive_name}_load_error", path=str(file_path), error=str(e)
        )
        return None
