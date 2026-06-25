"""Capture README hero as a pixel screenshot of the running Streamlit app."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


class PlaywrightNotReadyError(RuntimeError):
    """Raised when Playwright or its Chromium browser bundle is unavailable."""


class HeroCaptureError(RuntimeError):
    """Raised when hero screenshot capture fails after prerequisites are met."""


def playwright_chromium_ready() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


def ensure_playwright_chromium(*, auto_install: bool = True) -> None:
    if playwright_chromium_ready():
        return
    if auto_install:
        try:
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
                timeout=600,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise PlaywrightNotReadyError(
                "Playwright Chromium install failed. Run:\n"
                "  pip install -r requirements-dev.txt\n"
                "  python -m playwright install chromium"
            ) from exc
        if playwright_chromium_ready():
            return
    raise PlaywrightNotReadyError(
        "Playwright Chromium is not installed. Run:\n"
        "  pip install -r requirements-dev.txt\n"
        "  python -m playwright install chromium"
    )


def _wait_for_streamlit_ready(proc: subprocess.Popen[str], *, timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.stdout is None:
            break
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            raise RuntimeError("Streamlit process exited before becoming ready")
        if line and (
            "Local URL" in line
            or "Network URL" in line
            or "You can now view" in line
        ):
            return
        if not line:
            time.sleep(0.1)
    raise RuntimeError("Timed out waiting for Streamlit server")


def capture_hero_screenshot(
    app_path: Path,
    out_path: Path,
    *,
    port: int = 8799,
    viewport_width: int = 1440,
    viewport_height: int = 1100,
    auto_install: bool = True,
) -> None:
    """Start streamlit run app.py, click Run Simulation, save full-page PNG."""
    if not playwright_chromium_ready():
        if not auto_install:
            raise PlaywrightNotReadyError(
                "Playwright Chromium is not installed (auto_install=False). Run:\n"
                "  pip install -r requirements-dev.txt\n"
                "  python -m playwright install chromium"
            )
        ensure_playwright_chromium(auto_install=True)
    elif auto_install:
        ensure_playwright_chromium(auto_install=True)

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.headless",
            "true",
            "--server.port",
            str(port),
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=str(app_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_streamlit_ready(proc)
        from playwright.sync_api import sync_playwright

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": viewport_width, "height": viewport_height}
            )
            page.goto(f"http://localhost:{port}", wait_until="networkidle", timeout=90_000)
            page.get_by_role("button", name="Run Simulation").click()
            page.get_by_text("Decoder comparison").first.wait_for(timeout=120_000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(out_path), full_page=True)
            browser.close()
    except PlaywrightNotReadyError:
        raise
    except Exception as exc:
        raise HeroCaptureError(f"Hero screenshot capture failed: {exc}") from exc
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)