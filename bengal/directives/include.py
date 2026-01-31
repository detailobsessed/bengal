"""
Include directive for Mistune.

Allows including markdown files directly in content.
Syntax:

    ```{include} path/to/file.md
    ```

Or with options:

    ```{include} path/to/file.md
    :start-line: 5
    :end-line: 20
    ```

Paths are resolved relative to the site root or the current page's directory.

Robustness:
- Maximum include depth of 10 to prevent stack overflow
- Cycle detection to prevent infinite loops (a.md → b.md → a.md)
- File size limits to prevent memory exhaustion (10MB default)
- Symlink rejection to prevent path traversal attacks

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from mistune.directives import DirectivePlugin

from bengal.directives.base import BengalDirective
from bengal.directives.include_utils import (
    load_file_content,
    parse_line_numbers,
    resolve_include_path_with_fallback,
)
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from re import Match

    from mistune.block_parser import BlockParser
    from mistune.core import BlockState

__all__ = ["IncludeDirective", "render_include"]

logger = get_logger(__name__)

# Robustness limits
MAX_INCLUDE_DEPTH = 10  # Prevent stack overflow from deeply nested includes


class IncludeDirective(DirectivePlugin):
    """
    Include directive for including markdown files.

    Syntax:
            ```{include} path/to/file.md
            ```

    Or with line range:
            ```{include} path/to/file.md
            :start-line: 5
            :end-line: 20
            ```

    Paths are resolved relative to:
    1. Current page's directory (if source_path available in state)
    2. Site root (if root_path available in state)
    3. Current working directory (fallback)

    Security: Only allows paths within the site root to prevent path traversal.

    """

    PRIORITY = BengalDirective.PRIORITY_FIRST

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["include"]

    def parse(
        self, block: BlockParser, m: Match[str], state: BlockState
    ) -> dict[str, Any]:
        """
        Parse include directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state (may contain root_path, source_path)

        Returns:
            Token dict with type 'include'
        """
        # Get file path from title
        path = self.parse_title(m)
        if not path or not path.strip():
            logger.warning(
                "include_no_path",
                reason="include directive missing file path",
            )
            return {
                "type": "include",
                "attrs": {"error": "No file path specified"},
                "children": [],
            }

        # Parse options
        options = dict(self.parse_options(m))
        start_line, end_line = parse_line_numbers(options)

        # Resolve file path
        file_path = resolve_include_path_with_fallback(path, state, "include")

        if not file_path:
            return {
                "type": "include",
                "attrs": {"error": f"File not found: {path}"},
                "children": [],
            }

        # --- Robustness: Check depth limit ---
        # Use state.env dict for type-safe state tracking
        # Note: Must check for None explicitly since empty dict {} is falsy
        env_attr = getattr(state, "env", None)
        if env_attr is None:
            env: dict[str, object] = {}
            state.env = env
        else:
            env = env_attr
        depth_value = env.get("_include_depth", 0)
        current_depth: int = depth_value if isinstance(depth_value, int) else 0
        if current_depth >= MAX_INCLUDE_DEPTH:
            logger.warning(
                "include_max_depth_exceeded",
                path=path,
                depth=current_depth,
                max_depth=MAX_INCLUDE_DEPTH,
            )
            return {
                "type": "include",
                "attrs": {
                    "error": f"Maximum include depth ({MAX_INCLUDE_DEPTH}) exceeded. "
                    f"Check for deeply nested includes."
                },
                "children": [],
            }

        # --- Robustness: Check for include cycles ---
        files_value = env.get("_included_files")
        if isinstance(files_value, set):
            included_files: set[str] = files_value  # type: ignore[assignment]
        else:
            included_files = set()
        canonical_path = str(file_path.resolve())
        if canonical_path in included_files:
            logger.warning(
                "include_cycle_detected",
                path=path,
                canonical_path=canonical_path,
            )
            return {
                "type": "include",
                "attrs": {
                    "error": f"Include cycle detected: {path} was already included. "
                    f"Check for circular includes (a.md → b.md → a.md)."
                },
                "children": [],
            }

        # Load file content
        content = load_file_content(file_path, start_line, end_line, "include")

        if content is None:
            return {
                "type": "include",
                "attrs": {"error": f"Failed to read file: {path}"},
                "children": [],
            }

        # --- Update state for nested includes ---
        # Track this file to detect cycles using state.env dict
        new_included_files = included_files | {canonical_path}
        env["_included_files"] = new_included_files
        env["_include_depth"] = current_depth + 1

        # Parse included content as markdown
        # Use parse_tokens to allow nested directives in included content
        children = self.parse_tokens(block, content, state)

        # Restore depth after parsing (allows sibling includes at same depth)
        env["_include_depth"] = current_depth

        return {
            "type": "include",
            "attrs": {
                "path": str(file_path),
                "start_line": int(start_line) if start_line else None,
                "end_line": int(end_line) if end_line else None,
            },
            "children": children,
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register include directive."""
        directive.register("include", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("include", render_include)


def render_include(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render include directive.

    Args:
        renderer: Mistune renderer
        text: Rendered children (included markdown content)
        **attrs: Directive attributes

    Returns:
        HTML string

    """
    error = attrs.get("error")

    if error:
        return f'<div class="include-error"><p><strong>Include error:</strong> {error}</p></div>\n'

    # text contains the rendered included markdown content
    return text
