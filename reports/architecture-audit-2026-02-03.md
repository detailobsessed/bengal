# Architecture Audit: Circular Imports and Module Coupling

Date: 2026-02-03
Issue: bengal-cgs

## Scope

Investigate circular imports reported by pre-commit and assess module coupling. Provide recommendations on whether deferred imports are appropriate and identify refactor opportunities.

## Commands Run

```bash
python3 scripts/check_cycles.py --format=detailed
python3 scripts/check_dependencies.py --format=simple
```

## Summary

- Circular imports: 9 cycles, all **deferred-only** (TYPE_CHECKING or lazy imports).
- Layer violations: **none** (0 violations, 750 Python files).
- Coupling hotspots: `analysis.graph.knowledge_graph`, `utils.observability`, `core.resources`.

## Findings by Cycle

### 1) `bengal.utils.observability.logger` ↔ `bengal.utils.observability.rich_console`

**Pattern**
- `logger.py` imports `rich_console.get_console()` inside logging methods for rich formatting.
- `rich_console.py` lazily imports `logger.get_logger()` only in the exception path for `is_live_display_active()`.

**Assessment**
- Deferred-only cycle, but the relationship is real at runtime (logger depends on rich). The reverse dependency is only for debug logging.

**Recommendation**
- Keep `logger -> rich_console` (valid design: rich is output backend).
- Remove `rich_console -> logger` by replacing the exception logging with a minimal fallback (e.g., `warnings.warn`, stdlib `logging`, or `print`).
- This will eliminate the cycle without affecting features.

### 2) `bengal.errors.context` ↔ `bengal.errors.exceptions`

**Pattern**
- `context.py` only imports `exceptions.BengalError` under `TYPE_CHECKING`.
- `exceptions.py` lazily imports `BuildPhase`, `RelatedFile` from `context.py` within methods.

**Assessment**
- Type-checking / lazy-only cycle. Low risk and already aligned with current architecture.

**Recommendation**
- Accept as-is. If desired, move `RelatedFile` and `ErrorDebugPayload` into a small `errors/types.py` (or `protocols`) module to avoid type references to `context.py`.

### 3) `bengal.analysis.graph.knowledge_graph` ↔ `bengal.analysis.graph.analyzer`
### 4) `bengal.analysis.graph.knowledge_graph` ↔ `bengal.analysis.graph.reporter`
### 5) `bengal.analysis.graph.knowledge_graph` ↔ `bengal.analysis.graph.page_rank`
### 6) `bengal.analysis.graph.knowledge_graph` ↔ `bengal.analysis.graph.community_detection`
### 7) `bengal.analysis.graph.knowledge_graph` ↔ `bengal.analysis.links.suggestions`
### 8) `bengal.analysis.graph.knowledge_graph` ↔ `bengal.analysis.performance.path_analysis`

**Pattern**
- `knowledge_graph.py` owns the orchestration and lazily imports analyzer/reporters/calculators.
- The dependent modules only reference `KnowledgeGraph` for type hints (`TYPE_CHECKING`).

**Assessment**
- All cycles are deferred-only and safe. However, they indicate a tight cluster around `KnowledgeGraph` as a hub.

**Recommendation**
- Prefer **protocols** over consolidation. Create a `bengal.protocols.analysis` (or `analysis/graph/protocols.py`) with a minimal `KnowledgeGraphProtocol` interface used by analyzer/reporters.
- This removes type-checking edges and keeps modules independent.
- Consolidation into a single module is not recommended: it would increase file size, reduce separability, and conflict with the design intent of delegated analyzers.

### 9) `bengal.core.resources.image` ↔ `bengal.core.resources.processor`

**Pattern**
- `ImageResource._process()` lazy-imports `ImageProcessor`.
- `ImageProcessor.process()` imports `ImageResource` and `ProcessedImage` to construct results.

**Assessment**
- Deferred-only cycle but architecture is tightly coupled. This is the only cycle that touches core resources and could grow if new processors appear.

**Recommendation**
- Shift the result boundary to a shared type to break the cycle.
- Option A: have `ImageProcessor` return `ProcessedImageData` (already defined in `bengal/core/resources/types.py`), and let `ImageResource._process()` wrap it into `ProcessedImage`.
- Option B: move `ProcessedImage` to `types.py` and make `source` a protocol/Any to avoid importing `ImageResource`.

## Module Coupling Notes

- `scripts/check_dependencies.py` shows **no layer violations**. The current dependency direction is compliant.
- The audit aligns with `plan/rfc-remaining-coupling-fixes.md` (draft) but current cycles are all deferred-only, indicating progress since the RFC draft.
- The remaining cycles are localized and can be addressed by small protocol extractions rather than structural rewrites.

## Proposed Follow-up Work

1. Remove `rich_console -> logger` dependency by using a lightweight fallback logger.
2. Introduce `KnowledgeGraphProtocol` (or similar) to remove TYPE_CHECKING imports to `KnowledgeGraph`.
3. Decouple `ImageProcessor` from `ImageResource` using `ProcessedImageData` or protocol-based results.
