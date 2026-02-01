"""
Template engine system for Bengal SSG.

This package provides the Kida template engine, Bengal's native templating
solution optimized for free-threaded Python.

Architecture:
All template engine access MUST go through create_engine(). Direct
imports of engine classes are for type hints and testing only.

Kida Template Engine:
    Bengal's native template engine. Jinja2-compatible syntax with unified
    block endings, pattern matching, pipeline operators, and automatic
    block caching. Designed for Python 3.14+ free-threading.

Public API:
- create_engine(): Factory function (required for engine creation)
- register_engine(): Register custom/third-party engines
- TemplateEngineProtocol: Interface for custom implementations
- TemplateError: Base exception for template errors
- TemplateNotFoundError: Template file not found
- TemplateRenderError: Template rendering failed

Usage:
    >>> from bengal.rendering.engines import create_engine
    >>>
    >>> engine = create_engine(site)
    >>> html = engine.render("page.html", {"page": page, "site": site})

Custom Engines:
To add a third-party engine, implement TemplateEngineProtocol and register:

    >>> from bengal.rendering.engines import register_engine
    >>> register_engine("myengine", MyTemplateEngine)

Related Modules:
- bengal.rendering.template_functions: Functions available in templates
- bengal.rendering.template_context: Context wrappers for URL handling
- bengal.rendering.errors: Rich error objects for debugging

See Also:
- bengal.protocols: Canonical protocol definitions (TemplateEngine, TemplateRenderer, etc.)
- bengal.rendering.engines.kida: Kida implementation details

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.errors import BengalConfigError, ErrorCode

# Import from canonical location (bengal.protocols)
from bengal.protocols import TemplateEngine as TemplateEngineProtocol
from bengal.rendering.engines.errors import (
    TemplateError,
    TemplateNotFoundError,
)
from bengal.rendering.errors import TemplateRenderError

if TYPE_CHECKING:
    from bengal.core import Site

# Third-party engine registry (for plugins)
_ENGINES: dict[str, type[TemplateEngineProtocol]] = {}


def register_engine(name: str, engine_class: type[TemplateEngineProtocol]) -> None:
    """
    Register a third-party template engine.

    Args:
        name: Engine identifier (used in bengal.yaml)
        engine_class: Class implementing TemplateEngineProtocol

    """
    _ENGINES[name] = engine_class


def create_engine(
    site: Site,
    *,
    profile: bool = False,
) -> TemplateEngineProtocol:
    """
    Create a template engine based on site configuration.

    This is the ONLY way to get a template engine instance.

    Args:
        site: Site instance
        profile: Enable template profiling

    Returns:
        Engine implementing TemplateEngineProtocol

    Raises:
        BengalConfigError: If engine is unknown

    """
    engine_name = site.config.get("template_engine", "kida")

    if engine_name == "kida":
        from bengal.rendering.engines.kida import KidaTemplateEngine

        return KidaTemplateEngine(site, profile=profile)

    if engine_name in _ENGINES:
        return _ENGINES[engine_name](site)

    available = ["kida", *_ENGINES.keys()]
    raise BengalConfigError(
        f"Unknown template engine: '{engine_name}'. Available: {', '.join(sorted(available))}",
        code=ErrorCode.C003,
        suggestion="Set template_engine to 'kida' (default) or register a custom engine",
    )


# Public API
__all__ = [
    # Protocol
    "TemplateEngineProtocol",
    # Errors
    "TemplateError",
    "TemplateNotFoundError",
    "TemplateRenderError",
    # Factory
    "create_engine",
    "register_engine",
]
