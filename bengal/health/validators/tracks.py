"""Track validator for health checks."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import SiteLike


class TrackValidator(BaseValidator):
    """
    Validates track definitions and track item references.

    Checks:
    - Track data structure validity
    - Track items reference existing pages
    - Track pages have valid track_id

    """

    name = "Tracks"
    description = "Validates learning track definitions and page references"
    enabled_by_default = True

    def validate(
        self, site: SiteLike, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Validate track definitions and references."""
        results = []

        # Check if tracks data exists
        if not hasattr(site.data, "tracks") or not site.data.tracks:
            results.append(
                CheckResult.info(
                    "No tracks defined",
                    "No tracks.yaml file found or tracks data is empty. This is optional.",
                )
            )
            return results

        tracks_data = site.data.tracks
        if not tracks_data:
            return results

        # Cast to dict for iteration (tracks_data is dict at runtime)
        tracks: dict[str, Any] = tracks_data  # type: ignore[assignment]
        if not tracks:
            return results

        # Validate track structure
        for track_id, track in tracks.items():
            if not isinstance(track, dict):
                results.append(
                    CheckResult.error(
                        f"Invalid track structure: {track_id}",
                        code="H801",
                        recommendation=f"Track '{track_id}' is not a dictionary. Expected dict with 'title' and 'items' fields.",
                    )
                )
                continue

            # Check required fields
            if "items" not in track:
                results.append(
                    CheckResult.error(
                        f"Track missing 'items' field: {track_id}",
                        code="H802",
                        recommendation=f"Track '{track_id}' is missing required 'items' field. Add an 'items' list with page paths.",
                    )
                )
                continue

            if not isinstance(track["items"], list):
                results.append(
                    CheckResult.error(
                        f"Track 'items' must be a list: {track_id}",
                        code="H803",
                        recommendation=f"Track '{track_id}' has 'items' field that is not a list. Expected list of page paths.",
                    )
                )
                continue

            # Validate track items reference existing pages
            missing_items = []
            for item_path in track["items"]:
                if not isinstance(item_path, str):
                    results.append(
                        CheckResult.warning(
                            f"Invalid track item type in {track_id}",
                            code="H804",
                            recommendation=f"Track item must be a string (page path), got {type(item_path).__name__}.",
                        )
                    )
                    continue

                # Use get_page logic to check if page exists
                page = self._get_page(site, item_path)
                if page is None:
                    missing_items.append(item_path)

            if missing_items:
                details_text = (
                    f"The following track items reference pages that don't exist: {', '.join(missing_items[:5])}"
                    + (
                        f" (and {len(missing_items) - 5} more)"
                        if len(missing_items) > 5
                        else ""
                    )
                )
                results.append(
                    CheckResult.warning(
                        f"Track '{track_id}' has {len(missing_items)} missing page(s)",
                        code="H805",
                        recommendation="Check that page paths in tracks.yaml match actual content files.",
                        details=[details_text],
                    )
                )
            else:
                results.append(
                    CheckResult.success(
                        f"Track '{track_id}' is valid ({len(track['items'])} items)"
                    )
                )

        # Check for track pages with invalid track_id
        track_ids = set(tracks.keys())
        for page in site.pages:
            page_track_id = page.metadata.get("track_id")
            if page_track_id and page_track_id not in track_ids:
                # Use source_path for display since relative_path may not exist on PageLike
                page_display = str(getattr(page, "source_path", page.title))
                results.append(
                    CheckResult.warning(
                        f"Page '{page_display}' has invalid track_id",
                        code="H806",
                        recommendation=f"Either add '{page_track_id}' to tracks.yaml or remove track_id from page metadata.",
                        details=[
                            f"Page references track_id '{page_track_id}' which doesn't exist in tracks.yaml."
                        ],
                    )
                )

        return results

    def _get_page(self, site: SiteLike, path: str) -> object | None:
        """
        Get page using same logic as get_page template function.

        This mirrors the logic in bengal.rendering.template_functions.get_page
        to ensure validation matches runtime behavior.
        """
        if not path:
            return None

        # Build lookup maps if not already built
        # Use getattr since _page_lookup_maps may not exist on SiteLike protocol
        page_lookup_maps = getattr(site, "_page_lookup_maps", None)
        if page_lookup_maps is None:
            by_full_path: dict[str, object] = {}
            by_content_relative: dict[str, object] = {}

            content_root = site.root_path / "content"

            for p in site.pages:
                by_full_path[str(p.source_path)] = p

                try:
                    rel = p.source_path.relative_to(content_root)
                    rel_str = str(rel).replace("\\", "/")
                    by_content_relative[rel_str] = p
                except ValueError:
                    # Page is not under content root; skip adding to relative map.
                    pass

            page_lookup_maps = {
                "full": by_full_path,
                "relative": by_content_relative,
            }
            # Try to cache on site if possible
            if hasattr(site, "_page_lookup_maps"):
                with contextlib.suppress(AttributeError):
                    site._page_lookup_maps = page_lookup_maps  # type: ignore[attr-defined]

        maps = page_lookup_maps
        normalized_path = path.replace("\\", "/")

        # Strategy 1: Direct lookup
        if normalized_path in maps["relative"]:
            return maps["relative"][normalized_path]

        # Strategy 2: Try adding .md extension
        path_with_ext = (
            f"{normalized_path}.md"
            if not normalized_path.endswith(".md")
            else normalized_path
        )
        if path_with_ext in maps["relative"]:
            return maps["relative"][path_with_ext]

        # Strategy 3: Try full path
        if path in maps["full"]:
            return maps["full"][path]

        return None
