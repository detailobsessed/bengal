# Skipped Tests Audit

Issue: bengal-79x (CLOSED)

## Summary

Audited 120 skip markers. Reduced unconditional skips from 8 to 1.

## Unconditional Skips - REVIEWED

| File | Reason | Action |
|------|--------|--------|
| `test_default_theme_kida.py` | Kida doesn't support `{% do %}` | ✅ **DELETED** - tests unsupported feature |
| `test_protocols.py` | Deprecation paths not implemented | ✅ **DELETED** - incomplete stubs |
| `test_template_chain.py:125` | Template dependency tracking not in provenance | ⏸️ **KEPT** - valid future feature, has RFC |
| `test_cross_features.py` | i18n not fully implemented | ✅ **DELETED** - empty test body |
| `test_cross_features.py` | Versioned docs not fully implemented | ✅ **DELETED** - empty test body |
| `test_incremental_output_formats.py` | PageProxy caching bug | ✅ **CONVERTED to xfail** |
| `test_snapshot_integration.py` | Flaky parallel builds | ✅ **CONVERTED to xfail** |
| `test_incremental_efficiency.py` | Placeholder for regressions | ✅ **DELETED** - empty test body |

## 2. Conditional Skips (`@pytest.mark.skipif`) - VALID

These skip based on environment/dependencies:

| Condition | Files |
|-----------|-------|
| `not _pillow_available()` | test_type_safety.py, test_resource_contracts.py (4 tests) |
| `pytest_benchmark is None` | test_performance.py |
| `os.name == "nt"` (Windows) | test_edge_cases.py, test_resource_cleanup.py |
| `hypothesis not installed` | test_fuzz.py |

## 3. Runtime Skips (`pytest.skip()`) - VALID

These skip when preconditions aren't met:

| Category | Count | Notes |
|----------|-------|-------|
| Site not built | ~20 | test_autodoc_*.py - require `bengal build` first |
| Golden file ops | ~5 | test_directive_parity.py, test_golden_output.py |
| Feature not found | ~15 | CLI/API dirs, RSS feeds, etc. |
| Tool not registered | 2 | test_debug_tool_contract.py |
| Test quality thresholds | 3 | test_test_quality.py - soft thresholds |

## Remaining Valid Skips

- **Conditional skips**: Pillow, pytest-benchmark, Windows - correct behavior
- **Runtime skips**: autodoc tests require `bengal build` first - expected for integration tests
- **Template dependency**: `test_template_chain.py:125` - waiting on RFC implementation
