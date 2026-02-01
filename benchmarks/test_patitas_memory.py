"""
Patitas Parser Memory Usage Benchmarks.

Measures memory consumption during parsing of various document sizes.

Run with:
    python benchmarks/test_patitas_memory.py

Memory characteristics:
    - StringBuilder pattern minimizes intermediate allocations
    - Frozen dataclasses reduce memory overhead
    - Memory usage scales linearly with document size

Related:
    - plan/drafted/rfc-patitas-markdown-parser.md
    - bengal/parsing/backends/patitas/stringbuilder.py
"""

import gc
import tracemalloc
from statistics import mean


def measure_memory(func, *args, iterations=10):
    """Measure peak memory usage of a function.

    Returns (mean_peak_kb, measurements).
    """
    measurements = []

    for _ in range(iterations):
        # Force garbage collection
        gc.collect()

        # Start tracing
        tracemalloc.start()

        try:
            func(*args)
        finally:
            _current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

        measurements.append(peak / 1024)  # Convert to KB

    return mean(measurements), measurements


# Test documents
SMALL_DOC = """
# Heading 1

This is a paragraph with **bold** and *italic* text.

## Heading 2

- List item 1
- List item 2

```python
def hello():
    print("Hello!")
```
"""

MEDIUM_DOC = (
    """
# API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | /users | List users |
| POST | /users | Create user |

```python
def api_call():
    return {"status": "ok"}
```

> Note: This is important.
"""
    * 5
)

LARGE_DOC = MEDIUM_DOC * 10


def main():
    print("=" * 70)
    print("Patitas Parser Memory Usage Benchmarks")
    print("=" * 70)
    print()

    # Setup parser
    from bengal.parsing.backends.patitas import create_markdown

    patitas_md = create_markdown(
        plugins=["table", "strikethrough", "math"],
        highlight=False,
    )

    def patitas_parse(doc):
        return patitas_md(doc)

    # Warm up
    for _ in range(3):
        patitas_parse(SMALL_DOC)

    # Test each document size
    docs = [
        ("Small (~200 chars)", SMALL_DOC),
        ("Medium (~1500 chars)", MEDIUM_DOC),
        ("Large (~15000 chars)", LARGE_DOC),
    ]

    results = []

    for name, doc in docs:
        print(f"{name}:")
        print(f"  Document size: {len(doc):,} chars")

        patitas_mem, _ = measure_memory(patitas_parse, doc)
        mem_per_char = patitas_mem * 1024 / len(doc)  # bytes per char

        print(f"  Memory:   {patitas_mem:,.1f} KB")
        print(f"  Per char: {mem_per_char:.2f} bytes/char")
        print()

        results.append(
            {
                "name": name,
                "doc_size": len(doc),
                "patitas_kb": patitas_mem,
                "bytes_per_char": mem_per_char,
            }
        )

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()

    avg_bytes_per_char = mean(r["bytes_per_char"] for r in results)
    total_mem = sum(r["patitas_kb"] for r in results)

    print(f"Average memory per char: {avg_bytes_per_char:.2f} bytes")
    print(f"Total memory used: {total_mem:,.1f} KB")

    return results


if __name__ == "__main__":
    main()
