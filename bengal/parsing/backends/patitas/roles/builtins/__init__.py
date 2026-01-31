"""Built-in role handlers.

Provides commonly-used roles out of the box:
- ref: Cross-references
- doc: Document links
- kbd: Keyboard shortcuts
- abbr: Abbreviations with expansion
- math: Inline math
- sub: Subscript
- sup: Superscript
- icon: Inline SVG icons
- bdg: Inline badges/pills

"""

from __future__ import annotations

from bengal.parsing.backends.patitas.roles.builtins.badges import BadgeRole
from bengal.parsing.backends.patitas.roles.builtins.formatting import (
    AbbrRole,
    KbdRole,
    SubRole,
    SupRole,
)
from bengal.parsing.backends.patitas.roles.builtins.icons import IconRole
from bengal.parsing.backends.patitas.roles.builtins.math import MathRole
from bengal.parsing.backends.patitas.roles.builtins.reference import DocRole, RefRole

__all__ = [
    "AbbrRole",
    "BadgeRole",
    "DocRole",
    "IconRole",
    "KbdRole",
    "MathRole",
    "RefRole",
    "SubRole",
    "SupRole",
]
