"""
Literal include directive for Mistune.

Allows including code files directly in content as code blocks.
Syntax:

    ```{literalinclude} path/to/file.py
    ```

Or with options:

    ```{literalinclude} path/to/file.py
    :language: python
    :start-line: 5
    :end-line: 20
    :emphasize-lines: 7,8,9
    :linenos: true
    ```

Robustness:
- File size limits to prevent memory exhaustion (10MB default)
- Symlink rejection to prevent path traversal attacks

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from mistune.directives import DirectivePlugin

from bengal.directives.include_utils import (
    load_file_content,
    parse_line_numbers,
    resolve_include_path,
)
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from re import Match

    from mistune.block_parser import BlockParser
    from mistune.core import BlockState

__all__ = ["LiteralIncludeDirective", "render_literalinclude"]

logger = get_logger(__name__)


class LiteralIncludeDirective(DirectivePlugin):
    """
    Literal include directive for including code files as code blocks.

    Syntax:
            ```{literalinclude} path/to/file.py
            ```

    Or with options:
            ```{literalinclude} path/to/file.py
            :language: python
            :start-line: 5
            :end-line: 20
            :emphasize-lines: 7,8,9
            :linenos: true
            ```

    Paths are resolved relative to:
    1. Current page's directory (if source_path available in state)
    2. Site root (if root_path available in state)
    3. Current working directory (fallback)

    Security: Only allows paths within the site root to prevent path traversal.

    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["literalinclude"]

    def parse(
        self, block: BlockParser, m: Match[str], state: BlockState
    ) -> dict[str, Any]:
        """
        Parse literalinclude directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state (may contain root_path, source_path)

        Returns:
            Token dict with type 'literalinclude'
        """
        # Get file path from title
        path = self.parse_title(m)
        if not path or not path.strip():
            logger.warning(
                "literalinclude_no_path",
                reason="literalinclude directive missing file path",
            )
            return {
                "type": "literalinclude",
                "attrs": {"error": "No file path specified"},
                "children": [],
            }

        # Parse options
        options = dict(self.parse_options(m))
        language = options.get("language")
        emphasize_lines = options.get("emphasize-lines")
        linenos = options.get("linenos", "false").lower() in ("true", "1", "yes")
        start_line, end_line = parse_line_numbers(options)

        # Auto-detect language from file extension if not specified
        if not language:
            language = self._detect_language(path)

        # Resolve file path
        file_path = resolve_include_path(path, state, "literalinclude")

        if not file_path:
            return {
                "type": "literalinclude",
                "attrs": {"error": f"File not found: {path}"},
                "children": [],
            }

        # Load file content
        content = load_file_content(file_path, start_line, end_line, "literalinclude")

        if content is None:
            return {
                "type": "literalinclude",
                "attrs": {"error": f"Failed to read file: {path}"},
                "children": [],
            }

        return {
            "type": "literalinclude",
            "attrs": {
                "path": str(file_path),
                "language": language,
                "code": content,
                "start_line": int(start_line) if start_line else None,
                "end_line": int(end_line) if end_line else None,
                "emphasize_lines": emphasize_lines,
                "linenos": linenos,
            },
            "children": [],
        }

    def _detect_language(self, path: str) -> str | None:
        """
        Detect language from file extension.

        Args:
            path: File path

        Returns:
            Language name or None
        """
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".html": "html",
            ".css": "css",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".toml": "toml",
            ".md": "markdown",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "bash",
            ".fish": "bash",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".rb": "ruby",
            ".php": "php",
            ".sql": "sql",
            ".xml": "xml",
            ".r": "r",
            ".R": "r",
            ".m": "matlab",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".clj": "clojure",
            ".hs": "haskell",
            ".ml": "ocaml",
            ".fs": "fsharp",
            ".vb": "vbnet",
            ".cs": "csharp",
            ".dart": "dart",
            ".lua": "lua",
            ".pl": "perl",
            ".pm": "perl",
            ".vim": "vim",
            ".vimrc": "vim",
            ".dockerfile": "dockerfile",
            ".makefile": "makefile",
            ".mk": "makefile",
        }

        ext = Path(path).suffix.lower()
        return ext_map.get(ext)

    def __call__(self, directive: Any, md: Any) -> None:
        """Register literalinclude directive."""
        directive.register("literalinclude", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("literalinclude", render_literalinclude)


def render_literalinclude(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render literalinclude directive as code block.

    Args:
        renderer: Mistune renderer
        text: Not used (content is in attrs['code'])
        **attrs: Directive attributes

    Returns:
        HTML string

    """
    error = attrs.get("error")
    if error:
        return f'<div class="literalinclude-error"><p><strong>Literal include error:</strong> {error}</p></div>\n'

    code = attrs.get("code", "")
    language = attrs.get("language")
    linenos = attrs.get("linenos", False)
    emphasize_lines = attrs.get("emphasize_lines")

    # Use mistune's block_code renderer if available
    if hasattr(renderer, "block_code"):
        # Render as code block with syntax highlighting
        html: str = renderer.block_code(code, language)
    else:
        # Fallback: simple code block
        lang_attr = f' class="language-{language}"' if language else ""
        html = f"<pre><code{lang_attr}>{code}</code></pre>\n"

    # Add line numbers wrapper if requested
    if linenos:
        html = f'<div class="highlight-wrapper linenos">\n{html}</div>\n'

    # Add emphasis classes if specified
    if emphasize_lines:
        # Note: Full emphasis support would require client-side JS or server-side processing
        # For now, we just add a data attribute that themes can use
        emphasize_str = (
            emphasize_lines
            if isinstance(emphasize_lines, str)
            else str(emphasize_lines)
        )
        html = f'<div class="highlight-wrapper emphasize-lines" data-emphasize="{emphasize_str}">\n{html}</div>\n'

    return html
