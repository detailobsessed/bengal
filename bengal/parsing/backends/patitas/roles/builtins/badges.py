"""Badge role handlers.

Provides inline badge/pill elements via role syntax:
- {bdg}`text` - Default secondary badge
- {bdg-primary}`text` - Primary colored badge
- {bdg-success}`text` - Success colored badge
- {bdg-warning}`text` - Warning colored badge
- {bdg-danger}`text` - Danger colored badge
- {bdg-info}`text` - Info colored badge
- {bdg-secondary}`text` - Secondary colored badge
- {bdg-light}`text` - Light colored badge
- {bdg-dark}`text` - Dark colored badge

Example:
    This feature is {bdg-success}`stable` and {bdg-info}`documented`.

Output:
    <span class="badge badge-success">stable</span>
    <span class="badge badge-info">documented</span>

"""

from __future__ import annotations

from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from patitas.nodes import Role

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.stringbuilder import StringBuilder


class BadgeRole:
    """Handler for {bdg-*}`text` roles.

    Renders inline badge/pill elements with Bootstrap-style colors.

    Syntax:
        {bdg}`text` - Default (secondary) badge
        {bdg-primary}`text` - Primary colored badge
        {bdg-success}`text` - Success colored badge
        etc.

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    # Known badge color variants
    KNOWN_COLORS: ClassVar[frozenset[str]] = frozenset(
        {
            "primary",
            "secondary",
            "success",
            "warning",
            "danger",
            "info",
            "light",
            "dark",
        }
    )

    # Register all known variants plus catch-all pattern
    # Note: We register specific names so they're found in the registry
    # Unknown bdg-* patterns will fall through to default role renderer
    names: ClassVar[tuple[str, ...]] = (
        "bdg",
        "bdg-primary",
        "bdg-secondary",
        "bdg-success",
        "bdg-warning",
        "bdg-danger",
        "bdg-info",
        "bdg-light",
        "bdg-dark",
    )
    token_type: ClassVar[str] = "badge"

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Parse badge role content."""
        return Role(location=location, name=name, content=content.strip())

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render badge to HTML.

        Converts role name to badge class:
        - bdg -> badge badge-secondary
        - bdg-primary -> badge badge-primary
        - bdg-success -> badge badge-success
        etc.

        Empty content renders nothing (graceful handling).
        """
        content = node.content
        if not content:
            # Empty badges render nothing
            return

        # Extract color from role name (bdg-primary -> primary)
        # Only registered names reach this handler (see `names` tuple)
        name = node.name
        color = "secondary" if name == "bdg" else name[4:]  # Remove "bdg-" prefix

        sb.append(f'<span class="badge badge-{html_escape(color)}">')
        sb.append(html_escape(content))
        sb.append("</span>")
