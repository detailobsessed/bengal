"""Protocol definitions for analysis modules.

Provides protocol definitions for analysis components to break circular
imports between knowledge_graph and analysis modules.

Protocols:
    KnowledgeGraphProtocol: Protocol for knowledge graph access

Note:
    This module was created to fix circular import cycles between:
    - knowledge_graph ↔ graph_analysis
    - knowledge_graph ↔ graph_reporting
    - graph_reporting ↔ path_analysis

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.analysis.graph.metrics import GraphMetrics
    from bengal.analysis.graph.page_rank import PageRankResults
    from bengal.analysis.links.types import LinkMetrics, LinkType
    from bengal.analysis.performance.path_analysis import PathAnalysisResults
    from bengal.protocols.core import PageLike, SiteLike


@runtime_checkable
class KnowledgeGraphProtocol(Protocol):
    """Protocol for knowledge graph access.

    Defines the interface that analysis modules can depend on without
    importing the concrete KnowledgeGraph class. This breaks circular
    imports while maintaining type safety.

    Example:
        def analyze(graph: KnowledgeGraphProtocol) -> dict:
            hubs = graph.get_hubs()
            orphans = graph.get_orphans()
            return {"hubs": len(hubs), "orphans": len(orphans)}

    """

    # Core data structures
    site: SiteLike
    incoming_refs: dict[Any, float]  # PageLike -> float
    outgoing_refs: dict[Any, set[Any]]  # PageLike -> set[PageLike]
    link_metrics: dict[Any, LinkMetrics]  # PageLike -> LinkMetrics
    link_types: dict[tuple[Any, Any], LinkType]  # (PageLike|None, PageLike) -> LinkType
    incoming_edges: dict[Any, list[Any]]  # PageLike -> list[PageLike]

    # Configuration
    hub_threshold: int
    leaf_threshold: int
    exclude_autodoc: bool

    # State
    _built: bool

    # Metrics (set after build)
    metrics: GraphMetrics | None

    # Cached analysis results (optional, may be None)
    _pagerank_results: PageRankResults | None
    _path_results: PathAnalysisResults | None

    # Core methods
    def build(self) -> None:
        """Build the knowledge graph from site data."""
        ...

    def get_analysis_pages(self) -> list[PageLike]:
        """Get list of pages to analyze.

        Returns:
            List of pages included in analysis
        """
        ...

    def get_hubs(self, threshold: int | None = None) -> list[PageLike]:
        """Get pages with high incoming references (hubs).

        Args:
            threshold: Minimum incoming refs (defaults to hub_threshold)

        Returns:
            List of hub pages
        """
        ...

    def get_orphans(self) -> list[PageLike]:
        """Get pages with no incoming references.

        Returns:
            List of orphaned pages
        """
        ...

    def get_leaves(self, threshold: int | None = None) -> list[PageLike]:
        """Get pages with low connectivity (leaf nodes).

        Args:
            threshold: Maximum connectivity (defaults to leaf_threshold)

        Returns:
            List of leaf pages
        """
        ...

    # Analysis methods
    def compute_pagerank(
        self,
        damping: float = 0.85,
        max_iterations: int = 100,
        force_recompute: bool = False,
    ) -> PageRankResults:
        """Compute PageRank scores for all pages.

        Args:
            damping: Probability of following links vs random jump
            max_iterations: Maximum iterations before stopping
            force_recompute: If True, recompute even if cached

        Returns:
            PageRankResults with scores and metadata
        """
        ...

    def analyze_paths(
        self,
        force_recompute: bool = False,
        k_pivots: int = 100,
        seed: int = 42,
        auto_approximate_threshold: int = 500,
    ) -> PathAnalysisResults:
        """Analyze navigation paths and centrality metrics.

        Args:
            force_recompute: If True, recompute even if cached
            k_pivots: Number of pivot nodes for approximation
            seed: Random seed for deterministic results
            auto_approximate_threshold: Use exact if pages <= this

        Returns:
            PathAnalysisResults with centrality metrics
        """
        ...

    # Formatting
    def format_stats(self) -> str:
        """Format graph statistics as human-readable string.

        Returns:
            Formatted stats string
        """
        ...
