"""
CSS transformation utilities for asset processing.

Provides functions for transforming CSS syntax for browser compatibility:
- Nesting syntax transformation (&:hover, &.class → .parent:hover, .parent.class)
- Duplicate rule removal
- Lossless minification (whitespace/comment removal only)

These are internal utilities used by the Asset class during CSS processing.
"""

from __future__ import annotations

import re
from re import Match


def _find_balanced_braces(css: str, start: int) -> int | None:
    """
    Find the position of the closing brace that balances the opening brace at start.

    Args:
        css: CSS content string
        start: Position of the opening brace '{'

    Returns:
        Position of the matching closing brace, or None if not found

    """
    if start >= len(css) or css[start] != "{":
        return None

    depth = 1
    pos = start + 1
    while pos < len(css) and depth > 0:
        if css[pos] == "{":
            depth += 1
        elif css[pos] == "}":
            depth -= 1
        pos += 1

    return pos - 1 if depth == 0 else None


def _extract_css_rules(css: str) -> list[tuple[str, str, int, int]]:
    """
    Extract CSS rules as (selector, block_content, start, end) tuples.

    Uses iterative brace matching to avoid regex catastrophic backtracking.

    Args:
        css: CSS content string

    Returns:
        List of (selector, block_content, rule_start, rule_end) tuples

    """
    rules: list[tuple[str, str, int, int]] = []
    pos = 0

    while pos < len(css):
        # Find next opening brace
        brace_pos = css.find("{", pos)
        if brace_pos == -1:
            break

        # Extract selector (text before the brace)
        selector = css[pos:brace_pos].strip()

        # Find matching closing brace
        close_pos = _find_balanced_braces(css, brace_pos)
        if close_pos is None:
            # Unbalanced braces, skip this brace and continue
            pos = brace_pos + 1
            continue

        # Extract block content (between braces)
        block_content = css[brace_pos + 1 : close_pos]

        if selector:  # Only add if there's a selector
            rules.append((selector, block_content, pos, close_pos + 1))

        pos = close_pos + 1

    return rules


def transform_css_nesting(css: str) -> str:
    """
    Transform CSS nesting syntax (&:hover, &.class, etc.) to traditional selectors.

    Transforms patterns like:
        .parent {
          color: red;
          &:hover { color: blue; }
        }
    Into:
        .parent { color: red; }
        .parent:hover { color: blue; }

    This ensures browser compatibility for CSS nesting syntax.

    NOTE: We should NOT write nested CSS in source files. Use traditional selectors instead.
    This is a safety net for any nested CSS that slips through.

    Args:
        css: CSS content string

    Returns:
        Transformed CSS with nesting syntax expanded

    """
    # Pattern to find nested & selectors within a block
    # This is safe because it only matches within already-extracted block content
    nested_pattern = re.compile(r"&\s*([:.#\[\w\s-]+)\s*\{")

    def transform_block(selector: str, block_content: str) -> tuple[str, list[str]]:
        """
        Transform a single CSS block, extracting nested rules.

        Returns (remaining_content, list_of_extracted_rules).
        """
        # For @layer blocks, recursively transform the content inside
        if selector.strip().startswith("@layer"):
            # Recursively transform the content inside the @layer block
            transformed_content = transform_css_nesting(block_content)
            return transformed_content, []

        # Skip other @rules (like @media, @keyframes, etc.)
        if selector.strip().startswith("@"):
            return block_content, []

        # Clean @layer prefixes
        selector_clean = re.sub(r"^@layer\s+\w+\s*", "", selector).strip()
        has_layer = selector.strip().startswith("@layer")
        layer_decl = ""
        if has_layer:
            layer_match = re.match(r"(@layer\s+\w+)\s*", selector)
            if layer_match:
                layer_decl = layer_match.group(1) + " "

        if not selector_clean or selector_clean.startswith("@"):
            return block_content, []

        nested_rules: list[str] = []
        remaining = block_content
        search_start = 0

        while True:
            match = nested_pattern.search(remaining, search_start)
            if not match:
                break

            # Find the opening brace position in remaining
            brace_pos = match.end() - 1
            close_pos = _find_balanced_braces(remaining, brace_pos)

            if close_pos is None:
                # Unbalanced, skip this match
                search_start = match.end()
                continue

            nested_selector_part = match.group(1).strip()
            nested_block = remaining[brace_pos + 1 : close_pos]

            # Build full selector
            if nested_selector_part.startswith((":", ".", "[", " ")):
                full_selector = selector_clean + nested_selector_part
            else:
                full_selector = selector_clean + nested_selector_part

            if has_layer:
                nested_rules.append(f"{layer_decl}{full_selector} {{{nested_block}}}")
            else:
                nested_rules.append(f"{full_selector} {{{nested_block}}}")

            # Remove the nested rule from remaining content
            remaining = remaining[: match.start()] + remaining[close_pos + 1 :]
            # Don't advance search_start since we removed content

        # Clean up extra newlines
        remaining = re.sub(r"\n\s*\n\s*\n", "\n\n", remaining)

        return remaining, nested_rules

    # Process iteratively to handle deeply nested cases
    result = css
    for _ in range(10):
        rules = _extract_css_rules(result)
        if not rules:
            break

        # Process rules in reverse order to preserve positions
        new_parts: list[str] = []
        last_end = 0
        any_changes = False

        for selector, block_content, rule_start, rule_end in rules:
            remaining, nested_rules = transform_block(selector, block_content)

            # Check if content was transformed (either nested rules extracted or content changed)
            content_changed = remaining != block_content
            if nested_rules or content_changed:
                any_changes = True
                # Add content before this rule
                new_parts.append(result[last_end:rule_start])
                # Add transformed rule
                new_parts.append(f"{selector}{{{remaining}}}")
                if nested_rules:
                    new_parts.append("\n")
                    new_parts.append("\n".join(nested_rules))
                last_end = rule_end
            # If no changes, we'll include it unchanged via last_end tracking

        if not any_changes:
            break

        # Add remaining content after last processed rule
        new_parts.append(result[last_end:])
        result = "".join(new_parts)

    return result


def remove_duplicate_bare_h1_rules(css: str) -> str:
    """
    Remove duplicate bare h1 rules that appear right after scoped h1 rules.

    CSS processing sometimes creates duplicate rules like:
        .browser-header h1 { font-size: var(--text-5xl); }
        h1 { font-size: var(--text-5xl); }  # Duplicate!

    The bare h1 rule overrides the base typography rule, breaking text sizing.
    This function removes the duplicate bare h1 rules.

    Args:
        css: CSS content string

    Returns:
        CSS with duplicate bare h1 rules removed

    """
    # Pattern to match: scoped selector h1 { ... } followed by bare h1 { ... }
    # We need to match the scoped rule, then check if there's a duplicate bare h1
    pattern = r"(\.[\w-]+\s+h1\s*\{[^}]+\})\s*(h1\s*\{[^}]+\})"

    def remove_duplicate(match: Match[str]) -> str:
        scoped_rule = match.group(1)
        bare_rule = match.group(2)

        # Extract content from both rules
        scoped_content_match = re.search(r"\{([^}]+)\}", scoped_rule, re.DOTALL)
        bare_content_match = re.search(r"\{([^}]+)\}", bare_rule, re.DOTALL)

        if scoped_content_match and bare_content_match:
            scoped_content = (
                scoped_content_match.group(1).strip().replace(" ", "").replace("\n", "")
            )
            bare_content = (
                bare_content_match.group(1).strip().replace(" ", "").replace("\n", "")
            )

            # If content is identical, remove the bare rule
            if scoped_content == bare_content:
                return scoped_rule  # Return only the scoped rule

        # Not a duplicate, keep both
        return match.group(0)

    # Process iteratively to catch all duplicates
    result = css
    for _ in range(5):  # Max 5 iterations
        new_result = re.sub(pattern, remove_duplicate, result, flags=re.DOTALL)
        if new_result == result:
            break
        result = new_result

    return result


def lossless_minify_css(css: str) -> str:
    """
    Remove comments and redundant whitespace without touching selectors/properties.

    This intentionally avoids aggressive rewrites so modern CSS (nesting, @layer, etc.)
    remains intact.

    Args:
        css: CSS content string

    Returns:
        Minified CSS with comments and extra whitespace removed

    Note:
        Delegates to bengal.assets.css_minifier.minify_css which provides
        a more sophisticated implementation with proper context tracking.

    """
    from bengal.assets.css_minifier import minify_css

    return minify_css(css)
