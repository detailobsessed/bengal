"""
Unit tests for ICON_MAP in bengal.directives._icons.

Ensures that all mapped icons actually exist in the default theme.
"""

import pytest

from bengal.directives._icons import ICON_MAP, render_icon
from bengal.icons import resolver as icon_resolver


class TestIconMapValidity:
    """Test that all ICON_MAP entries resolve to existing icons."""

    def test_all_mapped_icons_exist(self) -> None:
        """Every icon in ICON_MAP should resolve to an actual SVG file."""
        # Reset resolver to use default theme
        icon_resolver._initialized = False
        icon_resolver._search_paths = []
        icon_resolver.clear_cache()

        missing = []
        for semantic_name, actual_name in ICON_MAP.items():
            svg = icon_resolver.load_icon(actual_name)
            if svg is None:
                missing.append(f"{semantic_name} -> {actual_name}")

        assert not missing, (
            "ICON_MAP contains mappings to non-existent icons:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )

    def test_external_icon_renders(self) -> None:
        """Regression test: external icon should render correctly.

        Previously mapped to 'arrow-square-out' which didn't exist.
        Now correctly maps to 'external' which exists in default theme.
        """
        # Reset resolver to use default theme
        icon_resolver._initialized = False
        icon_resolver._search_paths = []
        icon_resolver.clear_cache()

        result = render_icon("external", size=16)
        assert result, "external icon should render"
        assert "<svg" in result, "should return valid SVG"
        assert 'class="bengal-icon icon-external"' in result

    @pytest.mark.parametrize(
        "icon_name",
        [
            "external",
            "link",
            "search",
            "info",
            "warning",
            "error",
            "success",
            "tip",
            "note",
        ],
    )
    def test_common_semantic_icons_render(self, icon_name: str) -> None:
        """Common semantic icons used in templates should all render."""
        # Reset resolver to use default theme
        icon_resolver._initialized = False
        icon_resolver._search_paths = []
        icon_resolver.clear_cache()

        result = render_icon(icon_name, size=16)
        assert result, f"{icon_name} icon should render"
        assert "<svg" in result, f"{icon_name} should return valid SVG"
