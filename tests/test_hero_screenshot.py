"""Tests for optional Playwright hero capture guards."""

from __future__ import annotations

from pathlib import Path

import pytest

from ui.hero_screenshot import PlaywrightNotReadyError, capture_hero_screenshot, ensure_playwright_chromium


def test_capture_skips_streamlit_when_playwright_missing(monkeypatch, capsys):
    monkeypatch.setattr("ui.hero_screenshot.playwright_chromium_ready", lambda: False)

    with pytest.raises(PlaywrightNotReadyError, match="auto_install=False"):
        capture_hero_screenshot(
            Path("app.py"),
            Path("assets/hero.png"),
            auto_install=False,
        )
    print("capture_skipped_without_playwright: True")


def test_ensure_playwright_wraps_install_failure(monkeypatch, capsys):
    import subprocess

    monkeypatch.setattr("ui.hero_screenshot.playwright_chromium_ready", lambda: False)

    def _fail_install(*_args, **_kwargs):
        raise subprocess.CalledProcessError(1, "playwright install")

    monkeypatch.setattr("ui.hero_screenshot.subprocess.run", _fail_install)

    with pytest.raises(PlaywrightNotReadyError, match="install failed"):
        ensure_playwright_chromium(auto_install=True)
    print("install_failure_wrapped: True")