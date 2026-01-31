"""
Cacheable Protocol and Mixin - Type-safe cache contracts for Bengal.

This module provides:
- Cacheable protocol re-export from bengal.protocols
- CacheableMixin: Provides to_dict/from_dict aliases for test compatibility

For implementation details and documentation, see:
- bengal/protocols/infrastructure.py: Canonical protocol definition

Usage:
    @dataclass
    class MyEntry(CacheableMixin):
        value: str

        def to_cache_dict(self) -> dict[str, Any]:
            return {"value": self.value}

        @classmethod
        def from_cache_dict(cls, data: dict[str, Any]) -> "MyEntry":
            return cls(value=data["value"])

    # Now has to_dict() and from_dict() aliases automatically

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

# Re-export from canonical location for backwards compatibility
from bengal.protocols.infrastructure import Cacheable

if TYPE_CHECKING:
    from typing import Self

T = TypeVar("T", bound="Cacheable")


class CacheableMixin:
    """
    Mixin providing to_dict/from_dict aliases for Cacheable implementations.

    This eliminates duplicate alias methods across cache entry dataclasses.
    Classes using this mixin must implement to_cache_dict() and from_cache_dict().

    Thread Safety:
        Delegates to to_cache_dict/from_cache_dict which must be thread-safe.

    """

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to cache-friendly dictionary (must be implemented by subclass)."""
        raise NotImplementedError

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialize from cache dictionary (must be implemented by subclass)."""
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        """Alias for to_cache_dict (test compatibility)."""
        return self.to_cache_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Alias for from_cache_dict (test compatibility)."""
        return cls.from_cache_dict(data)


__all__ = ["Cacheable", "CacheableMixin", "T"]
