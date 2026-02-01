import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine


@pytest.fixture
def temp_site_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        site_dir = Path(tmp_dir) / "site"
        site_dir.mkdir()
        (site_dir / "bengal.toml").write_text(
            """
[site]
title = "Test Site"
baseurl = ""
            """
        )
        yield site_dir


@pytest.fixture
def temp_site_dir_with_favicon():
    """Site directory with custom favicon configured."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        site_dir = Path(tmp_dir) / "site"
        site_dir.mkdir()
        (site_dir / "bengal.toml").write_text(
            """
[site]
title = "Test Site"
baseurl = ""
favicon = "/assets/custom-favicon.png"
            """
        )
        yield site_dir


@pytest.fixture
def site_from_config(temp_site_dir):
    """Create a properly initialized Site using from_config()."""
    return Site.from_config(temp_site_dir)


@pytest.fixture
def site_with_favicon(temp_site_dir_with_favicon):
    """Create a Site with custom favicon configured."""
    return Site.from_config(temp_site_dir_with_favicon)


def _create_mock_page(**kwargs: object) -> Mock:
    """Create a Mock page with proper defaults for template rendering."""
    defaults: dict[str, object] = {
        "title": "Test Page",
        "url": "/",
        "href": "/",
        "_path": "/",
        "kind": "page",
        "keywords": [],
        "tags": [],
        "lang": None,  # Prevent Mock from being stringified in lang=""
        "content": None,
        "date": None,
        "output_path": None,
        "metadata": {},
    }
    defaults.update(kwargs)
    return Mock(**defaults)  # type: ignore[arg-type]


def test_default_favicon_inclusion(site_from_config):
    # Arrange: No favicon in config, use default theme
    engine = TemplateEngine(site_from_config)

    # Mock a simple page context with proper defaults
    context = {
        "site": site_from_config,
        "page": _create_mock_page(),
        "meta_desc": "Test description",
    }

    # Act: Render base.html
    html_output = engine.render("base.html", context)

    # Assert: Default favicon links are present
    assert '<link rel="icon" type="image/x-icon" href="' in html_output
    assert "favicon.ico" in html_output
    assert "favicon-16x16.png" in html_output
    assert "favicon-32x32.png" in html_output


def test_custom_favicon_override(site_with_favicon):
    # Arrange: Site with custom favicon configured in bengal.toml
    engine = TemplateEngine(site_with_favicon)

    context = {
        "site": site_with_favicon,
        "page": _create_mock_page(),
        "meta_desc": "Test description",
    }

    # Act
    html_output = engine.render("base.html", context)

    # Assert: Custom favicon link is present
    assert "/assets/custom-favicon.png" in html_output
