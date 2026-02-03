"""
Shared types for the errors package.

This module contains types shared between context.py and exceptions.py
to break the circular import between them.

Types:
    ErrorSeverity: Error severity classification enum
    RelatedFile: A file related to an error for debugging context
    ErrorDebugPayload: Machine-parseable debug context for AI troubleshooting

"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ErrorSeverity(Enum):
    """
    Error severity classification.

    Determines how errors are handled and whether the build can continue.
    Severity levels affect logging, aggregation, and user presentation.

    Levels (highest to lowest):

    - **FATAL** - Build cannot continue at all. Raises immediately.
    - **ERROR** - This item failed, but build may continue with others.
    - **WARNING** - Something is off but recoverable. Item processed.
    - **HINT** - Suggestion for improvement. No functional impact.

    Example:
            >>> severity = ErrorSeverity.ERROR
            >>> severity.can_continue
        True
            >>> severity.should_aggregate
        True

    """

    FATAL = "fatal"  # Build cannot continue at all
    ERROR = "error"  # This item failed, build may continue
    WARNING = "warning"  # Something off, but recoverable
    HINT = "hint"  # Suggestion for improvement

    @property
    def can_continue(self) -> bool:
        """
        Whether the build can typically continue after this severity.

        Returns:
            True for ERROR, WARNING, HINT. False only for FATAL.
        """
        return self != ErrorSeverity.FATAL

    @property
    def should_aggregate(self) -> bool:
        """
        Whether errors of this severity should be aggregated.

        Aggregation reduces log noise when many similar errors occur.

        Returns:
            True for ERROR and WARNING. False for FATAL and HINT.
        """
        return self in (ErrorSeverity.ERROR, ErrorSeverity.WARNING)


@dataclass
class RelatedFile:
    """
    A file related to an error for debugging context.

    Attributes:
        role: What role this file plays (e.g., "template", "page", "config")
        path: Path to the file
        line_number: Optional line number of interest

    """

    role: str
    path: Path | str
    line_number: int | None = None

    def __str__(self) -> str:
        path_str = str(self.path)
        if self.line_number:
            return f"{self.role}: {path_str}:{self.line_number}"
        return f"{self.role}: {path_str}"


@dataclass
class ErrorDebugPayload:
    """
    Machine-parseable debug context for AI troubleshooting.

    This provides structured data that can be immediately used
    to investigate errors programmatically.

    """

    # What was being processed
    processing_item: str | None = None  # e.g., "page:docs/api/index.md"
    processing_type: str | None = None  # e.g., "page", "asset", "template"

    # Template context (for rendering errors)
    template_name: str | None = None
    template_line: int | None = None
    available_context_vars: list[str] = field(default_factory=list)

    # Relevant config keys being accessed
    config_keys_accessed: list[str] = field(default_factory=list)

    # Relevant config snapshot
    relevant_config: dict[str, Any] = field(default_factory=dict)

    # Error pattern info (from session tracking)
    similar_error_count: int = 0
    first_occurrence_file: str | None = None
    is_recurring: bool = False

    # Suggested investigation paths
    files_to_check: list[str] = field(default_factory=list)
    grep_patterns: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    build_duration_so_far: float | None = None  # seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "processing_item": self.processing_item,
            "processing_type": self.processing_type,
            "template_name": self.template_name,
            "template_line": self.template_line,
            "available_context_vars": self.available_context_vars,
            "config_keys_accessed": self.config_keys_accessed,
            "relevant_config": self.relevant_config,
            "similar_error_count": self.similar_error_count,
            "first_occurrence_file": self.first_occurrence_file,
            "is_recurring": self.is_recurring,
            "files_to_check": self.files_to_check,
            "grep_patterns": self.grep_patterns,
            "test_files": self.test_files,
            "timestamp": self.timestamp.isoformat(),
            "build_duration_so_far": self.build_duration_so_far,
        }
