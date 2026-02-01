import os

from bengal.errors.traceback import (
    TracebackConfig,
    TracebackStyle,
    apply_file_traceback_to_env,
    map_debug_flag_to_traceback,
    set_effective_style_from_cli,
)


def test_default_style_is_compact(monkeypatch):
    # Clear traceback-related env vars (monkeypatch restores at teardown)
    monkeypatch.delenv("BENGAL_TRACEBACK", raising=False)
    monkeypatch.delenv("BENGAL_TRACEBACK_SHOW_LOCALS", raising=False)
    monkeypatch.delenv("BENGAL_TRACEBACK_MAX_FRAMES", raising=False)
    monkeypatch.delenv("BENGAL_TRACEBACK_SUPPRESS", raising=False)

    cfg = TracebackConfig.from_environment()
    assert cfg.style == TracebackStyle.COMPACT
    assert cfg.show_locals is False
    assert cfg.max_frames == 10


def test_env_sets_full_style(monkeypatch):
    monkeypatch.delenv("BENGAL_TRACEBACK", raising=False)
    monkeypatch.delenv("BENGAL_TRACEBACK_SHOW_LOCALS", raising=False)
    monkeypatch.delenv("BENGAL_TRACEBACK_MAX_FRAMES", raising=False)
    monkeypatch.delenv("BENGAL_TRACEBACK_SUPPRESS", raising=False)

    monkeypatch.setenv("BENGAL_TRACEBACK", "full")
    cfg = TracebackConfig.from_environment()
    assert cfg.style == TracebackStyle.FULL
    assert cfg.show_locals is True
    assert cfg.max_frames >= 20


def test_map_debug_maps_to_full_when_not_overridden(monkeypatch):
    # monkeypatch.delenv records original state and restores at teardown
    monkeypatch.delenv("BENGAL_TRACEBACK", raising=False)
    map_debug_flag_to_traceback(True, None)
    assert os.environ.get("BENGAL_TRACEBACK") == "full"


def test_map_debug_does_not_override_explicit_traceback(monkeypatch):
    monkeypatch.delenv("BENGAL_TRACEBACK", raising=False)
    set_effective_style_from_cli("minimal")
    map_debug_flag_to_traceback(True, "minimal")
    assert os.environ.get("BENGAL_TRACEBACK") == "minimal"


def test_get_renderer_types(monkeypatch):
    monkeypatch.delenv("BENGAL_TRACEBACK", raising=False)

    # Full
    set_effective_style_from_cli("full")
    cfg = TracebackConfig.from_environment()
    from bengal.errors.traceback import FullTracebackRenderer

    assert isinstance(cfg.get_renderer(), FullTracebackRenderer)

    # Compact
    set_effective_style_from_cli("compact")
    cfg = TracebackConfig.from_environment()
    from bengal.errors.traceback import CompactTracebackRenderer

    assert isinstance(cfg.get_renderer(), CompactTracebackRenderer)

    # Minimal
    set_effective_style_from_cli("minimal")
    cfg = TracebackConfig.from_environment()
    from bengal.errors.traceback import MinimalTracebackRenderer

    assert isinstance(cfg.get_renderer(), MinimalTracebackRenderer)

    # Off
    set_effective_style_from_cli("off")
    cfg = TracebackConfig.from_environment()
    from bengal.errors.traceback import OffTracebackRenderer

    assert isinstance(cfg.get_renderer(), OffTracebackRenderer)


def test_apply_file_traceback_to_env_sets_env(monkeypatch):
    # monkeypatch.delenv records original state and restores at teardown
    monkeypatch.delenv("BENGAL_TRACEBACK", raising=False)
    monkeypatch.delenv("BENGAL_TRACEBACK_SHOW_LOCALS", raising=False)
    monkeypatch.delenv("BENGAL_TRACEBACK_MAX_FRAMES", raising=False)
    monkeypatch.delenv("BENGAL_TRACEBACK_SUPPRESS", raising=False)

    site_cfg = {
        "dev": {
            "traceback": {
                "style": "minimal",
                "show_locals": True,
                "max_frames": 7,
                "suppress": ["click", "jinja2"],
            }
        }
    }

    apply_file_traceback_to_env(site_cfg)

    assert os.getenv("BENGAL_TRACEBACK") == "minimal"
    assert os.getenv("BENGAL_TRACEBACK_SHOW_LOCALS") == "1"
    assert os.getenv("BENGAL_TRACEBACK_MAX_FRAMES") == "7"
    assert os.getenv("BENGAL_TRACEBACK_SUPPRESS") == "click,jinja2"
